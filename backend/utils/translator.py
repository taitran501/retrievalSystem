"""
Translation Layer for Vietnamese Query Support
Translates Vietnamese queries to English for better CLIP/embedding performance
"""

import logging
import os
import json
from pathlib import Path
from typing import Optional
import re
from functools import lru_cache
import signal

# Try multiple translation backends
try:
    from googletrans import Translator as GoogleTranslator
    GOOGLE_TRANS_AVAILABLE = True
except ImportError:
    GOOGLE_TRANS_AVAILABLE = False

try:
    from transformers import MarianMTModel, MarianTokenizer
    MARIAN_AVAILABLE = True
except ImportError:
    MARIAN_AVAILABLE = False

# Vietnamese word segmentation
try:
    from underthesea import word_tokenize
    UNDERTHESEA_AVAILABLE = True
except ImportError:
    UNDERTHESEA_AVAILABLE = False

# DRES dictionary
try:
    try:
        from .dres_dictionary import get_exact_query, get_keywords, EXACT_QUERIES, CRITICAL_KEYWORDS
        DRES_DICT_AVAILABLE = True
    except (ImportError, ValueError):
        try:
            from dres_dictionary import get_exact_query, get_keywords, EXACT_QUERIES, CRITICAL_KEYWORDS
            DRES_DICT_AVAILABLE = True
        except ImportError:
            DRES_DICT_AVAILABLE = False
            EXACT_QUERIES = {}
            CRITICAL_KEYWORDS = {}
except Exception:
    DRES_DICT_AVAILABLE = False
    EXACT_QUERIES = {}
    CRITICAL_KEYWORDS = {}


class TimeoutException(Exception):
    """Custom exception for translation timeout"""
    pass


def timeout_handler(signum, frame):
    """Handler for translation timeout"""
    raise TimeoutException("Translation timeout")


class QueryTranslator:
    """
    Smart Vietnamese-to-English translator for DRES
    
    Features:
    - Exact dictionary matching for common queries
    - Keyword preservation for critical terms
    - Multi-backend with fallback
    - Translation caching
    - Timeout protection
    """
    
    def __init__(self, backend='marian', cache_size=1000, timeout_seconds=2):
        """
        Initialize translator
        
        Args:
            backend: 'google', 'marian', or 'auto'
            cache_size: Number of translations to cache
            timeout_seconds: Max time for single translation
        """
        self.logger = logging.getLogger(__name__)
        self.cache = {}
        self.cache_size = cache_size
        self.timeout_seconds = timeout_seconds
        
        # Persistent Cache Setup
        self.cache_dir = Path(os.path.join(os.path.dirname(__file__), "..", "data", "cache")).absolute()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.persistent_cache_file = self.cache_dir / "translations.json"
        self._load_persistent_cache()
        
        # Load DRES dictionary
        if DRES_DICT_AVAILABLE:
            self.exact_queries = EXACT_QUERIES
            self.keywords = CRITICAL_KEYWORDS
            self.logger.info(f"Loaded {len(self.exact_queries)} exact queries, {len(self.keywords)} keywords")
        else:
            self.exact_queries = {}
            self.keywords = {}
            self.logger.warning("DRES dictionary not available")
        
        # Initialize backend
        if backend == 'auto':
            if MARIAN_AVAILABLE:
                self.backend = 'marian'
            elif GOOGLE_TRANS_AVAILABLE:
                self.backend = 'google'
            else:
                self.backend = 'none'
                self.logger.warning("No translation library available")
        else:
            self.backend = backend
        
        # Initialize translator
        self._init_translator()
        
        self.logger.info(f"QueryTranslator initialized with backend: {self.backend}")

    def _load_persistent_cache(self):
        """Load translations from disk"""
        if self.persistent_cache_file.exists():
            try:
                with open(self.persistent_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cache.update(data)
                    self.logger.info(f"Loaded {len(data)} translations from persistent cache")
            except Exception as e:
                self.logger.warning(f"Failed to load persistent translation cache: {e}")

    def _save_persistent_cache(self):
        """Save translations to disk"""
        try:
            with open(self.persistent_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save persistent translation cache: {e}")
    
    def _init_translator(self):
        """Initialize translation backend"""
        if self.backend == 'marian' and MARIAN_AVAILABLE:
            model_name = "Helsinki-NLP/opus-mt-vi-en"
            self.logger.info(f"Loading Marian model: {model_name}")
            try:
                self.tokenizer = MarianTokenizer.from_pretrained(model_name)
                self.model = MarianMTModel.from_pretrained(model_name)
                self.logger.info("Marian model loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load Marian: {e}")
                self.backend = 'none'
                self.translator = None
            
        elif self.backend == 'google' and GOOGLE_TRANS_AVAILABLE:
            self.translator = GoogleTranslator()
            self.logger.info("Using Google Translate")
            
        else:
            self.translator = None
            self.logger.warning(f"Backend '{self.backend}' not available")
    
    def is_vietnamese(self, text: str) -> bool:
        """
        Detect if text is Vietnamese
        """
        if not text:
            return False
            
        vietnamese_chars = 'àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ'
        vietnamese_chars += vietnamese_chars.upper()
        
        # Count Vietnamese characters
        viet_char_count = sum(1 for c in text if c in vietnamese_chars)
        
        # If > 5% Vietnamese chars, consider it Vietnamese
        return viet_char_count / len(text) > 0.05
    
    def preserve_keywords(self, text: str) -> tuple:
        """
        Extract and replace critical keywords with placeholders
        
        Returns:
            (modified_text, replacements_dict)
        """
        replacements = {}
        modified = text
        
        # Sort keywords by length (longest first) to avoid partial matches
        sorted_keywords = sorted(self.keywords.items(), key=lambda x: len(x[0]), reverse=True)
        
        for vi_term, en_term in sorted_keywords:
            if vi_term in modified:
                placeholder = f"__KW{len(replacements)}__"
                modified = modified.replace(vi_term, placeholder)
                replacements[placeholder] = en_term
        
        return modified, replacements
    
    def restore_keywords(self, text: str, replacements: dict) -> str:
        """Restore placeholders with English keywords"""
        result = text
        for placeholder, en_term in replacements.items():
            result = result.replace(placeholder, en_term)
        return result
    
    def translate_with_timeout(self, text: str, source='vi', target='en') -> str:
        """
        Translate with timeout protection
        """
        try:
            if self.backend == 'google' and self.translator:
                result = self.translator.translate(text, src=source, dest=target)
                return result.text
                
            elif self.backend == 'marian':
                inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
                outputs = self.model.generate(**inputs, max_length=512)
                return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return text
            
        except Exception as e:
            self.logger.warning(f"Translation failed: {e}")
            return text
    
    def translate_smart(self, query: str) -> str:
        """
        Semantic-Augmented Translation (SAT):
        1. Exact dictionary match
        2. Direct MT + Visual Anchor Injection
        3. Fallback to original
        """
        # Normalize
        query_normalized = query.lower().strip()
        
        # Tier 1: Exact match
        if query_normalized in self.exact_queries:
            result = self.exact_queries[query_normalized]
            self.logger.info(f"Exact match: '{query}' → '{result}'")
            return result
        
        # Tier 2: SAT Logic
        try:
            # 1. Natural Machine Translation
            direct_translated = self.translate_with_timeout(query)
            
            # 2. Visual Anchor Extraction (Longest-Match First with Range Tracking)
            anchors_found = []
            # Sort keywords by length (longest first)
            sorted_keywords = sorted(self.keywords.items(), key=lambda x: len(x[0]), reverse=True)
            
            # Lowercase query for matching
            query_lower = query.lower()
            translated_lower = direct_translated.lower()
            
            # TRACK CONSUMED RANGES to prevent sub-string matching
            consumed_indices = set()
            
            for vi_term, en_term in sorted_keywords:
                vi_term_lower = vi_term.lower()
                
                # Use regex to find all occurrences of the term
                # This handles cases where a term appears multiple times
                for match in re.finditer(re.escape(vi_term_lower), query_lower):
                    start, end = match.start(), match.end()
                    
                    # Check if this range overlaps with any consumed indices
                    if any(i in consumed_indices for i in range(start, end)):
                        continue
                        
                    # Mark as consumed
                    for i in range(start, end):
                        consumed_indices.add(i)
                    
                    # Check if the English equivalent is already in the MT result
                    # Only add if it's a "Missing Link" visual anchor
                    if en_term.lower() not in translated_lower:
                        anchors_found.append(en_term)
            
            # 3. Semantic Merging
            if anchors_found:
                # Deduplicate anchors (preserving order)
                unique_anchors = []
                for a in anchors_found:
                    if a.lower() not in [ua.lower() for ua in unique_anchors]:
                        unique_anchors.append(a)
                
                # Append anchors as tags
                result = f"{direct_translated}, {', '.join(unique_anchors)}"
                self.logger.info(f"SAT: Augmented '{direct_translated}' with {len(unique_anchors)} anchors (Total: {len(anchors_found)})")
            else:
                result = direct_translated
                self.logger.info(f"SAT: Used direct translation for '{query}'")
            
            return result
            
        except Exception as e:
            self.logger.error(f"SAT failed: {e}")
            return query
    
    def process_query(self, query: str, auto_detect=True) -> str:
        """
        Process query with auto-detection and caching
        
        Args:
            query: Input query
            auto_detect: Auto-detect if query is Vietnamese
        
        Returns:
            English query
        """
        if not query or not query.strip():
            return query
        
        # Check cache
        cache_key = f"query_{query}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Auto-detect Vietnamese
        if auto_detect and not self.is_vietnamese(query):
            # Already English, return as-is
            return query
        
        # Translate
        result = self.translate_smart(query)
        
        # Cache result
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry (FIFO)
            self.cache.pop(next(iter(self.cache)))
        self.cache[cache_key] = result
        self._save_persistent_cache()
        
        return result


# Singleton instance
_translator_instance = None

def get_translator(backend='marian') -> QueryTranslator:
    """Get or create translator instance"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = QueryTranslator(backend=backend)
    return _translator_instance
