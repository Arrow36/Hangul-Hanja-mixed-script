from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any

class ConvertRequest(BaseModel):
    text: str = Field(..., description="The text to convert")
    request_id: Optional[str] = Field(None, description="Client-generated unique ID for this request to prevent stale responses")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "학교에 갑니다.",
                "request_id": "req-12345"
            }
        }
    )


class SegmentCandidate(BaseModel):
    entry_id: int = Field(..., description="The dictionary entry ID for this candidate")
    written_form: str = Field(..., description="The Hangul written form")
    origin_raw: Optional[str] = Field(None, description="The original language form (e.g., Hanja, English)")
    replacement: Optional[str] = Field(None, description="The text to use as replacement if selected (e.g., Hanja mixed script)")
    replacement_type: Optional[str] = Field(None, description="How the replacement was derived")
    is_reliable: bool = Field(False, description="Whether the replacement passed conservative conversion validation")
    part_of_speech: Optional[str] = Field(None, description="Part of speech of the word")
    homonym_number: Optional[int] = Field(None, description="Homonym number to distinguish identical written forms")
    score: float = Field(0.0, description="Confidence score for this candidate")
    selection_reason: Optional[str] = Field(None, description="Reason this candidate was selected/scored")

class SegmentOrigin(BaseModel):
    type: str
    language: Optional[str] = None
    raw: str
    entry_id: Optional[int] = None

class ConvertSegment(BaseModel):
    segment_id: int = Field(..., description="Unique ID for this segment within the conversion result")
    start: int = Field(..., description="Start character offset in the original text")
    end: int = Field(..., description="End character offset (exclusive) in the original text")
    original: str = Field(..., description="Exact original text from the input")
    display_text: str = Field(..., description="What to show in the UI - either the replacement or original text")
    status: str = Field(..., description="Status of the conversion: 'converted', 'ambiguous', 'no_match', 'kept'")
    matched_entry_id: Optional[int] = Field(None, description="The dictionary entry ID that was matched and selected")
    matched_sense_id: Optional[int] = Field(None, description="The sense ID of the matched entry, if applicable")
    origin_raw: Optional[str] = Field(None, description="The raw origin text for the matched entry")
    candidates: List[SegmentCandidate] = Field(default_factory=list, description="List of possible candidates for this segment")
    selection_reason: Optional[str] = Field(None, description="Why the current match was selected (or not)")
    origin: Optional[SegmentOrigin] = None

class ConvertResponse(BaseModel):
    request_id: str = Field(..., description="The request_id provided in the ConvertRequest")
    segments: List[ConvertSegment] = Field(..., description="List of segments comprising the full converted text")
    text_length: int = Field(..., description="Length of the original input text")
    processing_time_ms: float = Field(..., description="Time taken to process the conversion in milliseconds")


class EntryBrief(BaseModel):
    id: int = Field(..., description="Dictionary entry ID")
    written_form: str = Field(..., description="The Hangul written form")
    homonym_number: Optional[int] = Field(None, description="Homonym number")
    part_of_speech: Optional[str] = Field(None, description="Part of speech")
    origin_raw: Optional[str] = Field(None, description="Raw origin (Hanja/etc.)")
    vocabulary_level: Optional[str] = Field(None, description="Vocabulary level indicator")
    definition_preview: Optional[str] = Field(None, description="First 100 characters of the first sense definition")


class EquivalentInfo(BaseModel):
    language: str = Field(..., description="Language of the equivalent word")
    lemma: Optional[str] = Field(None, description="The equivalent word lemma")
    definition: Optional[str] = Field(None, description="Definition in the target language")

class SenseExampleInfo(BaseModel):
    example_type: Optional[str] = Field(None, description="Type of example")
    example: str = Field(..., description="The example text")
    group_index: int = Field(0, description="Group index for preserving dialogue/example grouping")
    order_index: int = Field(0, description="Order index within the group")

class SenseRelationInfo(BaseModel):
    target_entry_id: Optional[str] = Field(None, description="Related dictionary entry ID")
    target_lemma: Optional[str] = Field(None, description="Lemma of the related word")
    target_homonym_number: Optional[str] = Field(None, description="Homonym number of the related word")
    relation_type: Optional[str] = Field(None, description="Type of relationship (e.g., synonym, antonym)")

class MultimediaInfo(BaseModel):
    label: Optional[str] = Field(None, description="Description or label of the media")
    media_type: Optional[str] = Field(None, description="Type of media (image, audio, video)")
    url: Optional[str] = Field(None, description="URL to the media asset")

class SenseDetail(BaseModel):
    sense_number: Optional[str] = Field(None, description="Number denoting the sense sequence")
    definition: Optional[str] = Field(None, description="Definition of this sense")
    annotation: Optional[str] = Field(None, description="Usage annotation")
    syntactic_annotation: Optional[str] = Field(None, description="Syntactic usage annotation")
    syntactic_pattern: Optional[str] = Field(None, description="Syntactic pattern example")
    equivalents: List[EquivalentInfo] = Field(default_factory=list, description="Equivalent words in other languages")
    examples: List[SenseExampleInfo] = Field(default_factory=list, description="Example sentences/phrases")
    relations: List[SenseRelationInfo] = Field(default_factory=list, description="Related senses/words")
    multimedia: List[MultimediaInfo] = Field(default_factory=list, description="Multimedia assets for this sense")


class WordFormInfo(BaseModel):
    form_type: Optional[str] = Field(None, description="Type of word form (e.g., past, present)")
    written_form: Optional[str] = Field(None, description="How the form is written")
    pronunciation: Optional[str] = Field(None, description="How the form is pronounced")
    sound_url: Optional[str] = Field(None, description="URL to pronunciation audio")
    sub_forms: List[Dict[str, Any]] = Field(default_factory=list, description="Additional nested form representations")

class RelatedFormInfo(BaseModel):
    target_entry_id: Optional[str] = Field(None, description="Entry ID of the related form")
    relation_type: Optional[str] = Field(None, description="Type of relationship")
    written_form: Optional[str] = Field(None, description="Written form of the related entry")


class EntryDetail(BaseModel):
    id: int = Field(..., description="Dictionary entry ID")
    written_form: str = Field(..., description="The written form of the entry")
    variant: Optional[str] = Field(None, description="Variant forms")
    homonym_number: Optional[int] = Field(None, description="Homonym number")
    lexical_unit: Optional[str] = Field(None, description="Lexical unit category (e.g., word, idiom)")
    part_of_speech: Optional[str] = Field(None, description="Part of speech")
    origin_raw: Optional[str] = Field(None, description="Raw origin form (e.g., Hanja characters)")
    vocabulary_level: Optional[str] = Field(None, description="Vocabulary level indicator")
    annotation: Optional[str] = Field(None, description="General annotation")
    semantic_category: Optional[str] = Field(None, description="Semantic classification")
    subject_category: Optional[str] = Field(None, description="Subject domain classification")
    senses: List[SenseDetail] = Field(default_factory=list, description="Detailed senses/definitions")
    word_forms: List[WordFormInfo] = Field(default_factory=list, description="Inflectional or structural forms")
    related_forms: List[RelatedFormInfo] = Field(default_factory=list, description="Related morphological forms")
    raw_json: Optional[Dict[str, Any]] = Field(None, description="The original raw dictionary JSON, if requested")


class LookupRequest(BaseModel):
    query: str = Field(..., description="The search query")
    search_type: str = Field('written_form', description="Type of search: 'written_form', 'origin', 'entry_id'")
    page: int = Field(1, description="Page number for pagination", ge=1)
    page_size: int = Field(20, description="Results per page", ge=1, le=100)

class LookupResponse(BaseModel):
    query: str = Field(..., description="The search query that was executed")
    total: int = Field(..., description="Total number of matched results")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Results per page")
    results: List[EntryBrief] = Field(..., description="List of matched entry briefs")


class StatsResponse(BaseModel):
    total_entries: int = Field(..., description="Total number of dictionary entries")
    total_senses: int = Field(..., description="Total number of senses")
    total_examples: Optional[int] = Field(None, description="Total number of example values")
    entries_with_origin: int = Field(..., description="Number of entries that have an origin defined")
    entries_with_hanja_origin: Optional[int] = Field(None, description="Number of entries whose origin contains Hanja/CJK characters")
    unique_hangul_forms_with_origin: int = Field(..., description="Number of unique Hangul words that have a Hanja/origin form")
    import_info: Optional[Dict[str, Any]] = Field(None, description="Information about the last dictionary data import")


class SelectCandidateRequest(BaseModel):
    segment_id: int = Field(..., description="The segment ID being updated")
    entry_id: int = Field(..., description="The newly selected dictionary entry ID for the segment")
    original: Optional[str] = Field(None, description="The original surface text of the segment")


class SelectCandidateResponse(BaseModel):
    status: str = Field("ok")
    segment_id: int
    matched_entry_id: int
    display_text: str
    origin_raw: Optional[str] = None
    origin: Optional[SegmentOrigin] = None
    is_reliable: bool = False
    selection_reason: str = "user_selected"


class VersionResponse(BaseModel):
    code_version: str = Field(..., description="Code version identifier")
    api_schema_version: str = Field(..., description="API schema version")
    data_version: Optional[str] = Field(None, description="Dictionary data version")
    db_stats: Dict[str, Any] = Field(default_factory=dict, description="Database summary statistics")
