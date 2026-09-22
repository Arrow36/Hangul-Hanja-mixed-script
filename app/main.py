"""
FastAPI application for Korean-Hanja mixed script converter and dictionary reader.
"""

import os
import re
import time
import json
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, get_db_path
from app.schemas import (
    MAX_TEXT_LENGTH, ConvertRequest, ConvertResponse, ConvertSegment, SegmentCandidate,
    EntryDetail, EntryBrief, LookupResponse, StatsResponse,
    SelectCandidateRequest, SelectCandidateResponse, VersionResponse,
    SenseDetail, EquivalentInfo, SenseExampleInfo, SenseRelationInfo,
    MultimediaInfo, WordFormInfo, RelatedFormInfo,
)
from app.services.tokenizer import TokenizerService
from app.services.dictionary import DictionaryService
from app.services.converter import ConverterService
from app.services.disambiguation import DisambiguationService
from app.locales import resolve_language_path, LANGUAGE_PATHS

CODE_VERSION = "2026.09.23.1"


# --- App state ---
tokenizer: TokenizerService = None
dictionary: DictionaryService = None
converter: ConverterService = None
disambiguation: DisambiguationService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global tokenizer, dictionary, converter, disambiguation

    # Initialize database
    await init_db()

    # Initialize services
    tokenizer = TokenizerService()
    if not tokenizer.is_available:
        print(f"WARNING: Tokenizer not available: {tokenizer.init_error}")
        print("Conversion will not work properly without a morphological analyzer.")

    db_path = str(get_db_path())
    dictionary = DictionaryService(db_path)
    collocations = await dictionary.load_collocations()
    disambiguation = DisambiguationService(collocations)
    converter = ConverterService(tokenizer, disambiguation)

    print(f"Database: {db_path}")
    print(f"Tokenizer available: {tokenizer.is_available}")
    print(f"Loaded {len(collocations)} collocations from dictionary")

    yield

    # Cleanup
    dictionary.invalidate_cache()


app = FastAPI(
    title="Korean-Hanja Mixed Script Converter",
    description="Convert Korean text to Hanja-mixed script with dictionary lookup",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Routes ---

@app.get("/", include_in_schema=False)
async def index(request: Request):
    path = resolve_language_path(request.cookies.get("ui-language"), request.headers.get("accept-language", ""))
    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(f"/{path}{query}", status_code=307,
                            headers={"Vary": "Accept-Language, Cookie", "Cache-Control": "private, no-store"})


@app.get("/{language_path}", response_class=HTMLResponse, include_in_schema=False)
@app.get("/{language_path}/", response_class=HTMLResponse, include_in_schema=False)
async def localized_index(language_path: str):
    if language_path == "ko":
        return RedirectResponse("/kr", status_code=308)
    if language_path not in LANGUAGE_PATHS:
        raise HTTPException(status_code=404, detail="Language not supported")
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html",
                        headers={"Cache-Control": "no-cache"})


@app.post("/api/convert", response_model=ConvertResponse)
async def convert_text(req: ConvertRequest):
    """Convert Korean text to Hanja-mixed script."""
    if not converter:
        raise HTTPException(status_code=503, detail="Service not initialized")

    started = time.perf_counter()
    if not req.text:
        return ConvertResponse(
            request_id=req.request_id or "default",
            segments=[],
            text_length=0,
            processing_time_ms=0.0,
        )

    # Lookup function using dictionary service
    async def lookup_fn(forms):
        return await dictionary.batch_lookup_candidates(forms)

    segments, elapsed = await converter.convert(req.text, lookup_fn)

    # Etymology is independent from conversion. It includes Hanja origins,
    # loanwords, and native Korean words without turning them into candidates.
    excluded_reasons = {
        'non_content_token', 'whitespace_or_empty', 'particle',
        'stem_suffix', 'inter_token_gap', 'trailing_text'
    }
    origin_forms = list({
        seg.original for seg in segments
        if seg.original.strip() and seg.origin is None and seg.selection_reason not in excluded_reasons
    })
    origins_map = await dictionary.batch_lookup_origins(origin_forms) if origin_forms else {}
    for seg in segments:
        if seg.origin is not None:
            continue
        if seg.selection_reason in excluded_reasons:
            continue
        entries = origins_map.get(seg.original, [])
        if not entries:
            continue
        raw_values = list(dict.fromkeys(e.get('origin_raw') for e in entries if e.get('origin_raw')))
        if raw_values:
            raw = ' / '.join(raw_values)
            if re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]', raw):
                origin_type, language = 'hanja', 'Hanja'
            else:
                origin_type = 'loanword'
                language = 'English' if re.search(r'[A-Za-z]', raw) else None
        else:
            raw, origin_type, language = '고유어', 'native', 'Korean'
        seg.origin = {'type': origin_type, 'language': language, 'raw': raw, 'entry_id': entries[0]['entry_id']}

    # Convert to response model
    response_segments = []
    for seg in segments:
        candidates = []
        for c in seg.candidates:
            candidates.append(SegmentCandidate(
                entry_id=c.get('entry_id', 0),
                written_form=c.get('written_form', ''),
                origin_raw=c.get('origin_raw'),
                replacement=c.get('replacement'),
                replacement_type=c.get('replacement_type'),
                is_reliable=bool(c.get('is_reliable', False)),
                part_of_speech=c.get('part_of_speech'),
                homonym_number=c.get('homonym_number'),
                score=c.get('score', 0.0),
                selection_reason=c.get('selection_reason'),
            ))

        response_segments.append(ConvertSegment(
            segment_id=seg.segment_id,
            start=seg.start,
            end=seg.end,
            original=seg.original,
            display_text=seg.display_text,
            status=seg.status,
            matched_entry_id=seg.matched_entry_id,
            matched_sense_id=seg.matched_sense_id,
            origin_raw=seg.origin_raw,
            candidates=candidates,
            selection_reason=seg.selection_reason,
            origin=seg.origin,
        ))

    return ConvertResponse(
        request_id=req.request_id or "default",
        segments=response_segments,
        text_length=len(req.text),
        processing_time_ms=round((time.perf_counter() - started) * 1000, 2),
    )


@app.get("/api/lookup", response_model=LookupResponse)
async def lookup_entries(
    query: str = Query(..., min_length=1, max_length=200),
    search_type: str = Query('written_form', pattern='^(written_form|origin|entry_id)$'),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Search dictionary entries."""
    if not dictionary:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results, total = await dictionary.search_entries(
        query, search_type, page, page_size
    )

    briefs = []
    for r in results:
        preview = r.get('definition_preview', '') or ''
        if len(preview) > 100:
            preview = preview[:100] + '...'
        briefs.append(EntryBrief(
            id=r['id'],
            written_form=r['written_form'],
            homonym_number=r.get('homonym_number'),
            part_of_speech=r.get('part_of_speech'),
            origin_raw=r.get('origin_raw'),
            vocabulary_level=r.get('vocabulary_level'),
            definition_preview=preview,
        ))

    return LookupResponse(
        query=query,
        total=total,
        page=page,
        page_size=page_size,
        results=briefs,
    )


@app.get("/api/entries/{entry_id}", response_model=EntryDetail)
async def get_entry(entry_id: int, include_raw: bool = Query(False)):
    """Get full entry details."""
    if not dictionary:
        raise HTTPException(status_code=503, detail="Service not initialized")

    entry = await dictionary.get_entry_detail(entry_id, include_raw=include_raw)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Build senses
    senses = []
    for s in entry.get('senses', []):
        equivalents = [
            EquivalentInfo(
                language=eq.get('language', ''),
                lemma=eq.get('lemma'),
                definition=eq.get('definition'),
            )
            for eq in s.get('equivalents', [])
        ]
        examples = [
            SenseExampleInfo(
                example_type=ex.get('example_type'),
                example=ex.get('example', ''),
                group_index=ex.get('group_index'),
                order_index=ex.get('order_index'),
            )
            for ex in s.get('examples', [])
        ]
        relations = [
            SenseRelationInfo(
                target_entry_id=rel.get('target_entry_id'),
                target_lemma=rel.get('target_lemma'),
                target_homonym_number=rel.get('target_homonym_number'),
                relation_type=rel.get('relation_type'),
            )
            for rel in s.get('relations', [])
        ]
        multimedia = [
            MultimediaInfo(
                label=mm.get('label'),
                media_type=mm.get('media_type'),
                url=mm.get('url'),
            )
            for mm in s.get('multimedia', [])
        ]
        senses.append(SenseDetail(
            sense_number=s.get('sense_number'),
            definition=s.get('definition'),
            annotation=s.get('annotation'),
            syntactic_annotation=s.get('syntactic_annotation'),
            syntactic_pattern=s.get('syntactic_pattern'),
            equivalents=equivalents,
            examples=examples,
            relations=relations,
            multimedia=multimedia,
        ))

    # Word forms
    word_forms = []
    for wf in entry.get('word_forms', []):
        sub_forms = wf.get('sub_forms', [])
        word_forms.append(WordFormInfo(
            form_type=wf.get('form_type'),
            written_form=wf.get('written_form'),
            pronunciation=wf.get('pronunciation'),
            sound_url=wf.get('sound_url'),
            sub_forms=sub_forms,
        ))

    # Related forms
    related_forms = [
        RelatedFormInfo(
            target_entry_id=rf.get('target_entry_id'),
            relation_type=rf.get('relation_type'),
            written_form=rf.get('written_form'),
        )
        for rf in entry.get('related_forms', [])
    ]

    raw_json = None
    if include_raw and entry.get('raw_json_parsed'):
        raw_json = entry['raw_json_parsed']

    return EntryDetail(
        id=entry['id'],
        written_form=entry['written_form'],
        variant=entry.get('variant'),
        homonym_number=entry.get('homonym_number'),
        lexical_unit=entry.get('lexical_unit'),
        part_of_speech=entry.get('part_of_speech'),
        origin_raw=entry.get('origin_raw'),
        vocabulary_level=entry.get('vocabulary_level'),
        annotation=entry.get('annotation'),
        semantic_category=entry.get('semantic_category'),
        subject_category=entry.get('subject_category'),
        senses=senses,
        word_forms=word_forms,
        related_forms=related_forms,
        raw_json=raw_json,
    )


@app.get("/api/entries/{entry_id}/raw")
async def get_entry_raw(entry_id: int):
    if not dictionary:
        raise HTTPException(status_code=503, detail="Service not initialized")
    raw = await dictionary.get_entry_raw(entry_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return raw


@app.get("/api/version", response_model=VersionResponse)
async def get_version():
    """Return backend code version, API schema version, data version, and DB statistics."""
    stats = await dictionary.get_stats() if dictionary else {}
    import_info = stats.get('import_info') or {}
    data_ver = import_info.get('data_version')
    return VersionResponse(
        code_version=CODE_VERSION,
        api_schema_version="2.1.0",
        data_version=data_ver,
        db_stats={
            "total_entries": stats.get("total_entries", 0),
            "total_senses": stats.get("total_senses", 0),
            "total_examples": stats.get("total_examples", 0),
            "entries_with_hanja": stats.get("entries_with_hanja_origin", 0),
        }
    )


@app.post("/api/select-candidate", response_model=SelectCandidateResponse)
async def select_candidate(req: SelectCandidateRequest):
    """Validate user's candidate selection for a segment and return safe replacement + origin."""
    if not dictionary:
        raise HTTPException(status_code=503, detail="Service not initialized")

    info = await dictionary.get_entry_candidate_info(req.entry_id)
    if not info or not info.get('entry'):
        raise HTTPException(status_code=404, detail="Entry not found")

    entry = info['entry']
    cand = info.get('candidate')
    
    is_reliable = bool(cand and cand.get('is_reliable'))
    origin_raw = entry.get('origin_raw')
    
    orig = req.original or entry['written_form']
    if is_reliable and cand and cand.get('replacement'):
        cand_rep = cand['replacement']
        wf = entry['written_form']
        if wf.endswith('하다') and orig != wf and orig.startswith(wf[:-2]):
            root_len = len(cand_rep)
            display_text = cand_rep + orig[root_len:]
        else:
            display_text = cand_rep
    else:
        display_text = orig

    origin_dict = dictionary.build_origin_dict(entry)

    return SelectCandidateResponse(
        status="ok",
        segment_id=req.segment_id,
        matched_entry_id=req.entry_id,
        display_text=display_text,
        origin_raw=origin_raw,
        origin=origin_dict,
        is_reliable=is_reliable,
        selection_reason="user_selected",
    )


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get database statistics."""
    if not dictionary:
        raise HTTPException(status_code=503, detail="Service not initialized")

    stats = await dictionary.get_stats()
    return StatsResponse(**stats)


@app.get("/api/debug/tokenize")
async def debug_tokenize(text: str = Query(..., max_length=MAX_TEXT_LENGTH)):
    """Debug endpoint: show tokenization results."""
    if not tokenizer or not tokenizer.is_available:
        raise HTTPException(status_code=503, detail="Tokenizer not available")

    tokens = await tokenizer.tokenize_async(text)
    groups = tokenizer.build_word_groups(text, tokens)

    return {
        "text": text,
        "tokens": [
            {
                "form": t.form,
                "tag": t.tag,
                "start": t.start,
                "length": t.length,
                "original": t.original,
                "is_hangul": t.is_hangul,
                "is_noun": t.is_noun,
                "is_verb_stem": t.is_verb_stem,
                "is_suffix": t.is_suffix,
                "is_particle": t.is_particle,
                "is_punct": t.is_punct,
            }
            for t in tokens
        ],
        "groups": [
            {
                "start": g.start,
                "end": g.end,
                "original": g.original,
                "has_content": g.has_content,
                "content_form": g.content_form,
                "token_count": len(g.tokens),
            }
            for g in groups
        ],
    }
