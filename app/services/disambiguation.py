"""
Disambiguation service for selecting the best conversion candidate.

Uses local, explainable heuristics based on:
- Part of speech match
- Context clues and collocations from dictionary data
- Verbal context (e.g., noun + 하다/되다 matching dictionary entries)
- Explicit evidence thresholds
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class CandidateScore:
    """Scored candidate with explanation."""
    entry_id: int
    written_form: str
    origin_raw: Optional[str]
    replacement: Optional[str]
    replacement_type: Optional[str]
    is_reliable: bool
    part_of_speech: Optional[str]
    homonym_number: Optional[int]
    score: float = 0.0
    reasons: List[str] = field(default_factory=list)


# Minimum score to auto-select a candidate
MIN_AUTO_SELECT_SCORE = 0.5
# Minimum gap between top two candidates to auto-select
MIN_SCORE_GAP = 0.15


class DisambiguationService:
    """Select the best Hanja conversion candidate using local heuristics."""

    def __init__(self, collocations: Optional[Dict[Tuple[str, str], str]] = None):
        # (hangul_word, context_word) -> expected origin_hanja
        self._collocations: Dict[Tuple[str, str], str] = collocations or {}

    def set_collocations(self, collocations: Dict[Tuple[str, str], str]):
        self._collocations = collocations

    def score_candidates(
        self,
        candidates: List[dict],
        token_tag: Optional[str] = None,
        context_forms: Optional[List[str]] = None,
        is_verbal_context: bool = False,
    ) -> List[CandidateScore]:
        """Score and rank candidates for a given token.
        
        Args:
            candidates: List of candidate dicts from database
            token_tag: POS tag from morphological analysis
            context_forms: List of nearby word forms for context
            is_verbal_context: Whether token is followed by verbal suffix (하다/되다)
        
        Returns:
            Sorted list of CandidateScore (highest first)
        """
        if not candidates:
            return []

        scored = []
        for c in candidates:
            cs = CandidateScore(
                entry_id=c.get('entry_id', 0),
                written_form=c.get('written_form', ''),
                origin_raw=c.get('origin_raw'),
                replacement=c.get('replacement'),
                replacement_type=c.get('replacement_type'),
                is_reliable=bool(c.get('is_reliable', 0)),
                part_of_speech=c.get('part_of_speech'),
                homonym_number=c.get('homonym_number'),
            )

            # 1. Reliability of replacement
            if cs.is_reliable and cs.replacement:
                cs.score += 0.3
                cs.reasons.append('reliable_replacement')

            # 2. POS match
            if token_tag and cs.part_of_speech:
                if self._pos_matches(token_tag, cs.part_of_speech):
                    cs.score += 0.2
                    cs.reasons.append('pos_match')
                else:
                    cs.score -= 0.1
                    cs.reasons.append('pos_mismatch')

            # 3. Context collocation match from dictionary
            if context_forms and cs.origin_raw:
                for ctx in context_forms:
                    key = (cs.written_form, ctx)
                    if key in self._collocations:
                        expected_orig = self._collocations[key]
                        if expected_orig and (expected_orig in cs.origin_raw or cs.origin_raw in expected_orig):
                            cs.score += 0.25
                            cs.reasons.append(f'collocation_match({ctx}->{expected_orig})')
                            break

            # 4. A generic verbal context is not semantic evidence. In
            # particular, do not special-case examples such as 발전하다:
            # homonyms must be resolved by local, dictionary-backed context.

            # 5. Vocabulary level (minor tie-breaker only)
            vocab = c.get('vocabulary_level', '')
            if vocab == '초급':
                cs.score += 0.04
                cs.reasons.append('basic_vocab')
            elif vocab == '중급':
                cs.score += 0.02
                cs.reasons.append('intermediate_vocab')

            # 6. Replacement type
            if cs.replacement_type == 'pure_hanja':
                cs.score += 0.05
                cs.reasons.append('pure_hanja_type')

            scored.append(cs)

        # Sort by score descending and merge duplicates with identical replacement and origin_raw
        scored.sort(key=lambda x: x.score, reverse=True)
        return self.merge_identical_candidates(scored)

    def merge_identical_candidates(self, candidates: List[CandidateScore]) -> List[CandidateScore]:
        """Merge candidates that have identical replacement and origin_raw to avoid redundant glyph choices."""
        merged: Dict[Tuple[Optional[str], Optional[str]], CandidateScore] = {}
        for c in candidates:
            key = (c.replacement, c.origin_raw)
            if key not in merged:
                merged[key] = c
            else:
                existing = merged[key]
                if c.part_of_speech and existing.part_of_speech and c.part_of_speech not in existing.part_of_speech:
                    existing.part_of_speech = f"{existing.part_of_speech}/{c.part_of_speech}"
                if c.score > existing.score:
                    existing.score = c.score
                    existing.entry_id = c.entry_id
                    existing.reasons = list(dict.fromkeys(existing.reasons + c.reasons))
        return sorted(merged.values(), key=lambda x: x.score, reverse=True)

    def select_best(
        self,
        scored_candidates: List[CandidateScore],
    ) -> Tuple[Optional[CandidateScore], str]:
        """Select the best candidate if confidence is sufficient.
        
        Returns:
            (selected_candidate, status)
            status is 'converted', 'ambiguous', or 'no_match'
        """
        if not scored_candidates:
            return None, 'no_match'

        top = scored_candidates[0]

        # Single reliable candidate
        if len(scored_candidates) == 1:
            if top.is_reliable and top.replacement and top.score >= MIN_AUTO_SELECT_SCORE:
                return top, 'converted'
            elif top.score >= MIN_AUTO_SELECT_SCORE:
                return top, 'ambiguous'
            else:
                return top, 'ambiguous'

        # Multiple candidates: need sufficient gap
        second = scored_candidates[1]
        gap = top.score - second.score

        if (top.is_reliable and top.replacement and
                top.score >= MIN_AUTO_SELECT_SCORE and gap >= MIN_SCORE_GAP):
            return top, 'converted'
        elif top.score >= MIN_AUTO_SELECT_SCORE:
            # Close scores = ambiguous
            return top, 'ambiguous'
        else:
            return None, 'ambiguous'

    def _pos_matches(self, kiwi_tag: str, dict_pos: str) -> bool:
        pos_map = {
            '명사': ['NNG', 'NNP', 'NNB', 'NR', 'NP'],
            '동사': ['VV', 'VX', 'XSV'],
            '형용사': ['VA', 'VCP', 'VCN', 'XSA'],
            '부사': ['MAG', 'MAJ'],
            '관형사': ['MM'],
            '감탄사': ['IC'],
            '대명사': ['NP'],
            '수사': ['NR'],
            '접사': ['XPN', 'XSN', 'XSV', 'XSA'],
            '의존 명사': ['NNB'],
            '보조 동사': ['VX'],
            '보조 형용사': ['VX'],
            '고유 명사': ['NNP'],
        }
        expected_tags = pos_map.get(dict_pos, [])
        return kiwi_tag in expected_tags or any(kiwi_tag.startswith(t) for t in expected_tags)
