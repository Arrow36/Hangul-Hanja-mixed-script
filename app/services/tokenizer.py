"""
Tokenizer service for Korean text morphological analysis.
This module provides a clean abstraction layer around the kiwipiepy analyzer,
so that the converter logic does not depend directly on kiwipiepy types.
"""
import sys
if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from dataclasses import dataclass
from typing import List, Optional
import re

@dataclass
class MorphToken:
    """A morphological token abstraction, independent of any specific analyzer."""
    form: str          # The surface form / lemma of the token
    tag: str           # POS tag (normalized to a common scheme)
    start: int         # Character offset in original text
    length: int        # Character length in original text
    original: str      # Exact original text slice from input
    is_hangul: bool    # Whether the form is primarily Hangul
    is_noun: bool      # Whether this is a noun-type token
    is_verb_stem: bool # Whether this is a verb/adj stem
    is_suffix: bool    # Whether this is a suffix (XSV, XSA, XSN)
    is_particle: bool  # Whether this is a particle/ending
    is_punct: bool     # Whether this is punctuation

@dataclass
class WordGroup:
    """A group of morphological tokens forming a whitespace-delimited unit."""
    start: int
    end: int
    original: str
    tokens: List[MorphToken]
    
    @property
    def has_content(self) -> bool:
        return len(self.tokens) > 0
    
    @property
    def primary_noun(self) -> Optional[MorphToken]:
        for t in self.tokens:
            if t.is_noun:
                return t
        return None
    
    @property  
    def primary_verb(self) -> Optional[MorphToken]:
        for t in self.tokens:
            if t.is_verb_stem:
                return t
        return None
    
    @property
    def content_form(self) -> Optional[str]:
        """The form of the primary content morpheme."""
        n = self.primary_noun
        if n:
            return n.form
        v = self.primary_verb
        if v:
            return v.form
        return None

class TokenizerService:
    """Korean morphological analyzer wrapper."""
    
    def __init__(self):
        self._kiwi = None
        self._available = False
        self._init_error = None
        self._try_init()
    
    def _try_init(self):
        try:
            from kiwipiepy import Kiwi
            self._kiwi = Kiwi()
            self._available = True
        except ImportError as e:
            self._init_error = str(e)
            self._available = False
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    @property
    def init_error(self) -> Optional[str]:
        return self._init_error
    
    def tokenize(self, text: str) -> List[MorphToken]:
        if not self._available:
            raise RuntimeError(f"Tokenizer not available: {self._init_error}")
        
        tokens = self._kiwi.tokenize(text)
        result = []
        for t in tokens:
            # Extract the ORIGINAL text from the input
            original = text[t.start:t.start + t.len]
            
            tag = t.tag
            is_hangul = bool(re.match(r'^[가-힣]+$', t.form))
            
            # Noun tags: NNG (common), NNP (proper), NNB (bound), NR (numeral), NP (pronoun)
            is_noun = tag.startswith('NN') or tag == 'NR' or tag == 'NP'
            # Verb/adj stems
            is_verb_stem = tag in ('VV', 'VA', 'VX', 'VCP', 'VCN')
            # Suffixes
            is_suffix = tag.startswith('XS')  # XSV, XSA, XSN
            # Particles and endings
            is_particle = tag.startswith('J') or tag.startswith('E') or tag == 'EP'
            # Punctuation
            is_punct = tag.startswith('S')  # SF, SP, SS, SE, SO, SW
            
            result.append(MorphToken(
                form=t.form,
                tag=tag,
                start=t.start,
                length=t.len,
                original=original,
                is_hangul=is_hangul,
                is_noun=is_noun,
                is_verb_stem=is_verb_stem,
                is_suffix=is_suffix,
                is_particle=is_particle,
                is_punct=is_punct,
            ))
        
        return result
    
    def build_word_groups(self, text: str, tokens: List[MorphToken]) -> List[WordGroup]:
        """Group adjacent tokens into word groups that correspond to whitespace-separated units.
        This helps align morphological analysis with original text structure.
        
        A word group contains:
        - The original text span (preserving spaces, punctuation)
        - The constituent morphological tokens
        - The primary content token (first noun or verb stem)
        """
        if not tokens:
            return []
        
        groups = []
        current_tokens = []
        group_start = 0
        
        # Track gaps between tokens to detect word boundaries
        for i, token in enumerate(tokens):
            if current_tokens:
                prev = current_tokens[-1]
                prev_end = prev.start + prev.length
                gap = text[prev_end:token.start]
                
                # If there's a space in the gap, start a new group
                if ' ' in gap or '\n' in gap or '\t' in gap:
                    # Close current group
                    group_end = prev_end
                    groups.append(WordGroup(
                        start=group_start,
                        end=group_end,
                        original=text[group_start:group_end],
                        tokens=current_tokens[:]
                    ))
                    
                    # Add whitespace as its own group if any
                    ws_text = gap
                    if ws_text:
                        groups.append(WordGroup(
                            start=prev_end,
                            end=token.start,
                            original=ws_text,
                            tokens=[]
                        ))
                    
                    current_tokens = [token]
                    group_start = token.start
                else:
                    current_tokens.append(token)
            else:
                # Handle leading whitespace
                if token.start > group_start:
                    leading = text[group_start:token.start]
                    if leading.strip() == '':
                        groups.append(WordGroup(
                            start=group_start,
                            end=token.start,
                            original=leading,
                            tokens=[]
                        ))
                        group_start = token.start
                current_tokens = [token]
                group_start = token.start
        
        # Close last group
        if current_tokens:
            last = current_tokens[-1]
            group_end = last.start + last.length
            groups.append(WordGroup(
                start=group_start,
                end=group_end,
                original=text[group_start:group_end],
                tokens=current_tokens[:]
            ))
        
        # Handle trailing text
        if groups:
            last_end = groups[-1].end
            if last_end < len(text):
                groups.append(WordGroup(
                    start=last_end,
                    end=len(text),
                    original=text[last_end:],
                    tokens=[]
                ))
        elif text:
            groups.append(WordGroup(
                start=0,
                end=len(text),
                original=text,
                tokens=[]
            ))
        
        return groups
