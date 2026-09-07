"""
Converter service: transforms Korean text into Hanja-mixed script.

Core principles:
1. All conversions are based on [start, end) character offsets in the original text
2. Morphological analysis is used for segmentation and alignment, NOT for reconstructing text
3. Unreplaced portions preserve the exact original text (spaces, newlines, punct, emoji)
4. Only convert when there's reliable dictionary evidence
5. Never do global syllable-by-syllable replacement
"""

import time
import re
import unicodedata
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field

from app.services.tokenizer import TokenizerService, MorphToken, WordGroup
from app.services.disambiguation import DisambiguationService, CandidateScore


@dataclass
class ConversionSegment:
    """A segment of the conversion result, mapped to original text."""
    segment_id: int
    start: int          # char offset in original text
    end: int            # char offset exclusive
    original: str       # exact original text
    display_text: str   # converted text or original
    status: str         # converted, ambiguous, no_match, kept
    matched_entry_id: Optional[int] = None
    matched_sense_id: Optional[int] = None
    origin_raw: Optional[str] = None
    candidates: List[dict] = field(default_factory=list)
    selection_reason: Optional[str] = None
    origin: Optional[dict] = None


class ConverterService:
    """Convert Korean text to Hanja-mixed script using dictionary lookups."""

    def __init__(self, tokenizer: TokenizerService, disambiguation: DisambiguationService):
        self.tokenizer = tokenizer
        self.disambiguation = disambiguation

    async def convert(
        self,
        text: str,
        lookup_fn,  # async callable: (List[str]) -> Dict[str, List[dict]]
    ) -> Tuple[List[ConversionSegment], float]:
        start_time = time.perf_counter()

        if not text:
            return [], 0.0

        if not self.tokenizer.is_available:
            seg = ConversionSegment(
                segment_id=0,
                start=0,
                end=len(text),
                original=text,
                display_text=text,
                status='kept',
                selection_reason='tokenizer_unavailable',
            )
            elapsed = (time.perf_counter() - start_time) * 1000
            return [seg], elapsed

        # Step 1: Tokenize
        tokens = self.tokenizer.tokenize(text)

        # Step 2: Build word groups (whitespace-delimited units)
        groups = self.tokenizer.build_word_groups(text, tokens)

        # Step 3: Collect forms to look up
        forms_to_lookup = set()
        sentence_context_forms = []

        for group in groups:
            if not group.has_content:
                continue
            for token in group.tokens:
                if token.is_hangul and (token.is_noun or token.is_verb_stem):
                    forms_to_lookup.add(token.form)
                    sentence_context_forms.append(token.form)

                # For verb stems ending in 하 (e.g. 위하 in 위하여/위한), look up with -다
                if token.is_verb_stem and token.is_hangul:
                    forms_to_lookup.add(token.form + '다')
                    if token.form.endswith('하'):
                        forms_to_lookup.add(token.form[:-1])  # e.g. 위

                # For noun stems followed by verbalizer 하, look up noun + 하다
                if token.is_noun and token.is_hangul:
                    forms_to_lookup.add(token.form + '하다')
                    forms_to_lookup.add(token.form + '되다')

            # Intra-word compound candidate forms (e.g. 문화적, 국제화)
            if len(group.tokens) > 1:
                for start_t in range(len(group.tokens)):
                    for end_t in range(start_t + 2, len(group.tokens) + 1):
                        sub = group.tokens[start_t:end_t]
                        if any(t.is_particle for t in sub):
                            continue
                        span_orig = text[sub[0].start : sub[-1].start + sub[-1].length]
                        forms_to_lookup.add(span_orig)
                        span_form = "".join(t.form for t in sub)
                        forms_to_lookup.add(span_form)

        # Multi-word compound check (e.g. 경제 발전)
        content_words = [g.content_form for g in groups if g.has_content and g.content_form]
        for i in range(len(content_words) - 1):
            w1 = content_words[i]
            w2 = content_words[i + 1]
            if w1 and w2:
                forms_to_lookup.add(f"{w1} {w2}")

        # Step 4: Batch lookup candidates from dictionary
        if forms_to_lookup:
            candidates_map = await lookup_fn(list(forms_to_lookup))
        else:
            candidates_map = {}

        # Step 5: Process segments
        segments = []
        segment_id = 0

        for group_idx, group in enumerate(groups):
            if not group.has_content:
                seg = ConversionSegment(
                    segment_id=segment_id,
                    start=group.start,
                    end=group.end,
                    original=group.original,
                    display_text=group.original,
                    status='kept',
                    selection_reason='whitespace_or_empty',
                )
                segments.append(seg)
                segment_id += 1
                continue

            group_segments = self._process_word_group(
                text, group, candidates_map, segment_id, sentence_context_forms
            )
            segments.extend(group_segments)
            segment_id += len(group_segments)

        # Step 6: Fill gaps
        segments = self._fill_gaps(text, segments, segment_id)

        elapsed = (time.perf_counter() - start_time) * 1000
        return segments, elapsed

    def _process_word_group(
        self,
        text: str,
        group: WordGroup,
        candidates_map: Dict[str, List[dict]],
        start_id: int,
        sentence_context: List[str],
    ) -> List[ConversionSegment]:
        segments = []
        seg_id = start_id
        processed_end = group.start

        num_tokens = len(group.tokens)
        i = 0

        while i < num_tokens:
            token = group.tokens[i]

            # Handle inter-token gaps
            if token.start > processed_end:
                gap_text = text[processed_end:token.start]
                segments.append(ConversionSegment(
                    segment_id=seg_id,
                    start=processed_end,
                    end=token.start,
                    original=gap_text,
                    display_text=gap_text,
                    status='kept',
                    selection_reason='inter_token_gap',
                ))
                seg_id += 1
                processed_end = token.start

            # Skip tokens already covered by previous multi-token span
            if (token.start + token.length) <= processed_end:
                i += 1
                continue

            # -------------------------------------------------------------
            # PRIORITY 1: Multi-token compound / whole-word matching
            # (e.g., 문화(NNG) + 적(XSN) -> 문화적; 국제(NNG) + 화(XSN) -> 국제화)
            # -------------------------------------------------------------
            compound_matched = False
            for j in range(num_tokens, i + 1, -1):
                sub_tokens = group.tokens[i:j]
                # Boundary check: do not cross into particles (J*)
                if any(t.is_particle for t in sub_tokens):
                    continue

                span_start = sub_tokens[0].start
                span_end = sub_tokens[-1].start + sub_tokens[-1].length
                span_text = text[span_start:span_end]
                span_form = "".join(t.form for t in sub_tokens)

                cands = candidates_map.get(span_text) or candidates_map.get(span_form)
                if not cands:
                    continue

                scored = self.disambiguation.score_candidates(
                    cands,
                    token_tag=sub_tokens[0].tag,
                    context_forms=[f for f in sentence_context if f not in (span_text, span_form)],
                )
                selected, status = self.disambiguation.select_best(scored)

                if selected and selected.replacement and selected.is_reliable and status == 'converted':
                    cand_list = [
                        {
                            'entry_id': sc.entry_id,
                            'written_form': sc.written_form,
                            'origin_raw': sc.origin_raw,
                            'replacement': sc.replacement,
                            'replacement_type': sc.replacement_type,
                            'is_reliable': sc.is_reliable,
                            'part_of_speech': sc.part_of_speech,
                            'homonym_number': sc.homonym_number,
                            'score': round(sc.score, 4),
                            'selection_reason': ', '.join(sc.reasons) if sc.reasons else None,
                        }
                        for sc in scored
                    ]
                    has_hanja = bool(re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]', selected.origin_raw or ''))
                    origin_obj = {
                        'type': 'hanja' if has_hanja else 'loanword',
                        'language': 'Hanja' if has_hanja else ('English' if re.search(r'[A-Za-z]', selected.origin_raw or '') else None),
                        'raw': selected.origin_raw or selected.replacement,
                        'entry_id': selected.entry_id
                    }
                    segments.append(ConversionSegment(
                        segment_id=seg_id,
                        start=span_start,
                        end=span_end,
                        original=span_text,
                        display_text=selected.replacement,
                        status='converted',
                        matched_entry_id=selected.entry_id,
                        origin_raw=selected.origin_raw,
                        candidates=cand_list,
                        selection_reason='whole_word_match',
                        origin=origin_obj,
                    ))
                    seg_id += 1
                    processed_end = span_end
                    i = j
                    compound_matched = True
                    break

            if compound_matched:
                continue

            # -------------------------------------------------------------
            # PRIORITY 2: Single token processing
            # -------------------------------------------------------------
            token_start = max(token.start, processed_end)
            token_end = max(token.start + token.length, processed_end)
            original_text = text[token_start:token_end]

            context_forms = [f for f in sentence_context if f != token.form]
            is_verbal_context = False
            if i + 1 < num_tokens:
                next_t = group.tokens[i + 1]
                if next_t.is_suffix and next_t.form in ('하', '되', '시키'):
                    is_verbal_context = True

            candidates = []
            if token.is_hangul and (token.is_noun or token.is_verb_stem):
                candidates = candidates_map.get(token.form, [])

                # Verb stem with -다 lookup (e.g. 위하 -> 위하다)
                if token.is_verb_stem and not candidates:
                    hada_candidates = candidates_map.get(token.form + '다', [])
                    if hada_candidates:
                        candidates = hada_candidates

                # If followed by verbalizer suffix (e.g. 발전 + 하 -> 발전하다)
                if is_verbal_context:
                    hada_cands = candidates_map.get(token.form + '하다', [])
                    if hada_cands and not candidates:
                        candidates = hada_cands

                if candidates:
                    scored = self.disambiguation.score_candidates(
                        candidates,
                        token_tag=token.tag,
                        context_forms=context_forms,
                        is_verbal_context=is_verbal_context,
                    )
                    selected, status = self.disambiguation.select_best(scored)

                    cand_list = [
                        {
                            'entry_id': sc.entry_id,
                            'written_form': sc.written_form,
                            'origin_raw': sc.origin_raw,
                            'replacement': sc.replacement,
                            'replacement_type': sc.replacement_type,
                            'is_reliable': sc.is_reliable,
                            'part_of_speech': sc.part_of_speech,
                            'homonym_number': sc.homonym_number,
                            'score': round(sc.score, 4),
                            'selection_reason': ', '.join(sc.reasons) if sc.reasons else None,
                        }
                        for sc in scored
                    ]

                    # Build origin object
                    origin_obj = None
                    if selected and selected.origin_raw:
                        has_hanja = bool(re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]', selected.origin_raw))
                        origin_obj = {
                            'type': 'hanja' if has_hanja else 'loanword',
                            'language': 'Hanja' if has_hanja else ('English' if re.search(r'[A-Za-z]', selected.origin_raw) else None),
                            'raw': selected.origin_raw,
                            'entry_id': selected.entry_id
                        }

                    if selected and selected.replacement and selected.is_reliable and status == 'converted':
                        # Special handling for verb stem inflections like 위한 / 위하여
                        if token.is_verb_stem and token.form.endswith('하') and len(selected.replacement) < len(token.original):
                            root_len = len(selected.replacement)
                            disp_text = selected.replacement + original_text[root_len:]
                            
                            segments.append(ConversionSegment(
                                segment_id=seg_id,
                                start=token_start,
                                end=token_end,
                                original=original_text,
                                display_text=disp_text,
                                status='converted',
                                matched_entry_id=selected.entry_id,
                                origin_raw=selected.origin_raw,
                                candidates=cand_list,
                                selection_reason=', '.join(selected.reasons),
                                origin=origin_obj,
                            ))
                            seg_id += 1
                            processed_end = token_end
                            i += 1
                            # Skip overlapping inflection tokens (e.g. ᆫ in 위한)
                            while i < num_tokens and (group.tokens[i].start + group.tokens[i].length) <= processed_end:
                                i += 1
                            continue

                        display = self._build_display_text(token, selected)
                        seg = ConversionSegment(
                            segment_id=seg_id,
                            start=token_start,
                            end=token_end,
                            original=original_text,
                            display_text=display,
                            status='converted',
                            matched_entry_id=selected.entry_id,
                            origin_raw=selected.origin_raw,
                            candidates=cand_list,
                            selection_reason=', '.join(selected.reasons),
                            origin=origin_obj,
                        )
                    else:
                        seg = ConversionSegment(
                            segment_id=seg_id,
                            start=token_start,
                            end=token_end,
                            original=original_text,
                            display_text=original_text,
                            status=status if candidates else 'no_match',
                            matched_entry_id=selected.entry_id if selected else None,
                            origin_raw=selected.origin_raw if selected else None,
                            candidates=cand_list,
                            selection_reason='insufficient_evidence',
                            origin=origin_obj,
                        )
                else:
                    seg = ConversionSegment(
                        segment_id=seg_id,
                        start=token_start,
                        end=token_end,
                        original=original_text,
                        display_text=original_text,
                        status='no_match',
                    )
            else:
                reason = 'particle' if token.is_particle else ('stem_suffix' if token.is_suffix else 'non_content_token')
                seg = ConversionSegment(
                    segment_id=seg_id,
                    start=token_start,
                    end=token_end,
                    original=original_text,
                    display_text=original_text,
                    status='kept',
                    selection_reason=reason,
                    origin=None,
                )

            segments.append(seg)
            seg_id += 1
            processed_end = token_end
            i += 1

        if processed_end < group.end:
            trailing = text[processed_end:group.end]
            segments.append(ConversionSegment(
                segment_id=seg_id,
                start=processed_end,
                end=group.end,
                original=trailing,
                display_text=trailing,
                status='kept',
                selection_reason='trailing_text',
            ))
            seg_id += 1

        return segments

    def _build_display_text(
        self,
        token: MorphToken,
        selected: CandidateScore,
    ) -> str:
        replacement = selected.replacement
        if not replacement:
            return token.original

        rtype = selected.replacement_type

        if rtype == 'pure_hanja':
            return replacement

        elif rtype == 'mixed':
            hanja_part = _extract_hanja_prefix(replacement)
            if hanja_part and len(hanja_part) == len(token.form):
                return hanja_part
            return replacement

        elif rtype == 'slash_variants':
            parts = replacement.split('/')
            if parts:
                first = parts[0].strip()
                if _is_all_hanja(first) and len(first) == len(token.form):
                    return first
            return token.original

        return token.original

    def _fill_gaps(
        self,
        text: str,
        segments: List[ConversionSegment],
        next_id: int,
    ) -> List[ConversionSegment]:
        if not text:
            return segments

        segments.sort(key=lambda s: s.start)
        filled = []
        pos = 0

        for seg in segments:
            if seg.start > pos:
                gap_text = text[pos:seg.start]
                filled.append(ConversionSegment(
                    segment_id=next_id,
                    start=pos,
                    end=seg.start,
                    original=gap_text,
                    display_text=gap_text,
                    status='kept',
                    selection_reason='gap_fill',
                ))
                next_id += 1
            filled.append(seg)
            pos = max(pos, seg.end)

        if pos < len(text):
            trailing = text[pos:]
            filled.append(ConversionSegment(
                segment_id=next_id,
                start=pos,
                end=len(text),
                original=trailing,
                display_text=trailing,
                status='kept',
                selection_reason='trailing_fill',
            ))

        for i, seg in enumerate(filled):
            seg.segment_id = i

        return filled

    def apply_user_selection(
        self,
        segments: List[ConversionSegment],
        segment_id: int,
        entry_id: int,
    ) -> List[ConversionSegment]:
        """Apply a user's candidate selection to a specific segment.
        Only affects the targeted segment, not other occurrences.
        """
        for seg in segments:
            if seg.segment_id == segment_id:
                for c in seg.candidates:
                    if c['entry_id'] == entry_id:
                        if c.get('replacement'):
                            seg.display_text = c['replacement']
                            seg.status = 'converted'
                        seg.matched_entry_id = entry_id
                        seg.origin_raw = c.get('origin_raw')
                        seg.selection_reason = 'user_selected'
                        break
                break
        return segments


def _is_hangul(s: str) -> bool:
    return bool(re.match(r'^[\uac00-\ud7a3]+$', s))


def _is_all_hanja(s: str) -> bool:
    return bool(re.match(r'^[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+$', s))


def _extract_hanja_prefix(s: str) -> str:
    result = []
    cjk_re = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
    for ch in s:
        if cjk_re.match(ch):
            result.append(ch)
        else:
            break
    return ''.join(result)
