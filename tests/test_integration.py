"""
Integration tests for the Korean-Hanja converter.
Tests against the actual imported dictionary database.
"""

import sys
import os
import json
import asyncio
import sqlite3
import unittest
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = str(PROJECT_ROOT / 'hanja_dict.db')


def db_exists():
    return os.path.exists(DB_PATH)


class TestDatabaseImport(unittest.TestCase):
    """Test that the dictionary was imported correctly."""

    @classmethod
    def setUpClass(cls):
        if not db_exists():
            raise unittest.SkipTest("Database not found. Run import first.")
        cls.conn = sqlite3.connect(DB_PATH)
        cls.conn.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_entry_count(self):
        """Test 1: Total entry count matches reference."""
        count = self.conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        self.assertEqual(count, 56555, f"Expected ~56555 entries, got {count}")

    def test_02_sense_count(self):
        """Test 2: Total sense count matches reference."""
        count = self.conn.execute("SELECT COUNT(*) FROM senses").fetchone()[0]
        self.assertEqual(count, 76833, f"Expected ~76833 senses, got {count}")

    def test_03_origin_entries(self):
        """Test 3: Entries with hanja origin."""
        count = self.conn.execute(
            "SELECT COUNT(*) FROM conversion_candidates"
        ).fetchone()[0]
        self.assertGreater(count, 30000)

    def test_04_kisa_four_entries(self):
        """Test 8: 기사 has four entries with correct origins."""
        rows = self.conn.execute(
            "SELECT id, homonym_number, origin_raw, part_of_speech "
            "FROM entries WHERE written_form = '기사' "
            "ORDER BY homonym_number"
        ).fetchall()
        self.assertEqual(len(rows), 4, f"Expected 4 기사 entries, got {len(rows)}")

        origins = {r['origin_raw'] for r in rows}
        self.assertIn('技士', origins)
        self.assertIn('記事', origins)
        self.assertIn('棋士/碁士', origins)
        self.assertIn('騎士', origins)

    def test_05_senses_not_lost(self):
        """Test 3: Multi-sense entries preserved."""
        # 가 (entry 27733) should have at least 2 senses
        senses = self.conn.execute(
            "SELECT COUNT(*) FROM senses WHERE entry_id = 27733"
        ).fetchone()[0]
        self.assertGreaterEqual(senses, 2)

    def test_06_equivalents_preserved(self):
        """Test 3: Multilingual equivalents preserved."""
        # Check that equivalents exist for first sense of entry 27733
        sense_id = self.conn.execute(
            "SELECT id FROM senses WHERE entry_id = 27733 ORDER BY sense_number LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(sense_id)

        equiv_count = self.conn.execute(
            "SELECT COUNT(*) FROM equivalents WHERE sense_id = ?",
            (sense_id[0],)
        ).fetchone()[0]
        self.assertGreater(equiv_count, 0)

    def test_07_examples_preserved(self):
        """Test 3: Sense examples preserved."""
        # Entry 27733 sense 1 has examples
        sense_id = self.conn.execute(
            "SELECT id FROM senses WHERE entry_id = 27733 ORDER BY sense_number LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(sense_id)

        example_count = self.conn.execute(
            "SELECT COUNT(*) FROM sense_examples WHERE sense_id = ?",
            (sense_id[0],)
        ).fetchone()[0]
        self.assertGreater(example_count, 0)

    def test_08_raw_json_preserved(self):
        """Test 2: Raw JSON preserved for entries."""
        raw = self.conn.execute(
            "SELECT raw_json FROM entries WHERE id = 27733"
        ).fetchone()
        self.assertIsNotNone(raw)
        self.assertIsNotNone(raw[0])

        parsed = json.loads(raw[0])
        self.assertIn('Lemma', parsed)
        self.assertIn('Sense', parsed)

    def test_09_word_forms_preserved(self):
        """Test 2: Word forms (pronunciation, conjugation) preserved."""
        count = self.conn.execute(
            "SELECT COUNT(*) FROM word_forms WHERE entry_id = 27733"
        ).fetchone()[0]
        self.assertGreater(count, 0)

    def test_10_reimport_no_duplicates(self):
        """Test 4: Verify reimport would not create duplicates.
        We test by checking entry IDs are unique."""
        dup_count = self.conn.execute(
            "SELECT COUNT(*) FROM (SELECT id FROM entries GROUP BY id HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        self.assertEqual(dup_count, 0, "Found duplicate entry IDs")

    def test_11_conversion_candidates_korean_lookup(self):
        """Test 5: 한국 -> 韓國 candidate exists."""
        rows = self.conn.execute(
            "SELECT * FROM conversion_candidates WHERE written_form = '한국'"
        ).fetchall()
        self.assertGreater(len(rows), 0)
        origins = [r['origin_raw'] for r in rows]
        self.assertTrue(any('韓國' in o for o in origins if o))

    def test_12_baljeon_candidates(self):
        """Test 7: 발전 has both 發展 and 發電 candidates."""
        rows = self.conn.execute(
            "SELECT origin_raw FROM conversion_candidates WHERE written_form = '발전'"
        ).fetchall()
        origins = [r[0] for r in rows]
        self.assertIn('發展', origins)
        self.assertIn('發電', origins)

    def test_13_native_word_no_candidate(self):
        """Test 9: 빠르다 (native word) should not have conversion candidate."""
        rows = self.conn.execute(
            "SELECT * FROM conversion_candidates WHERE written_form = '빠르다'"
        ).fetchall()
        self.assertEqual(len(rows), 0)

    def test_14_foreign_word_no_latin_replacement(self):
        """Test 10: 게임기 should not have Latin letters in reliable replacement."""
        rows = self.conn.execute(
            "SELECT replacement, is_reliable FROM conversion_candidates "
            "WHERE written_form = '게임기'"
        ).fetchall()
        for r in rows:
            if r['is_reliable']:
                # Should not contain Latin letters
                self.assertFalse(
                    any(c.isascii() and c.isalpha() for c in (r['replacement'] or '')),
                    f"Reliable replacement contains Latin: {r['replacement']}"
                )

    def test_15_related_forms_preserved(self):
        """Related forms preserved."""
        count = self.conn.execute(
            "SELECT COUNT(*) FROM related_forms"
        ).fetchone()[0]
        self.assertGreater(count, 0)

    def test_16_sense_relations_preserved(self):
        """Sense relations preserved."""
        count = self.conn.execute(
            "SELECT COUNT(*) FROM sense_relations"
        ).fetchone()[0]
        self.assertGreater(count, 0)


class TestTokenizer(unittest.TestCase):
    """Test the tokenizer service."""

    @classmethod
    def setUpClass(cls):
        from app.services.tokenizer import TokenizerService
        cls.tokenizer = TokenizerService()
        if not cls.tokenizer.is_available:
            raise unittest.SkipTest("Tokenizer not available")

    def test_basic_tokenization(self):
        """Test basic Korean tokenization."""
        tokens = self.tokenizer.tokenize('대한민국의 경제는 빠르게 발전하였다.')
        forms = [t.form for t in tokens]
        self.assertIn('대한민국', forms)
        self.assertIn('경제', forms)
        self.assertIn('발전', forms)

    def test_offset_preservation(self):
        """Test 14: Character offsets are correct."""
        text = '경제 발전은 중요하다.'
        tokens = self.tokenizer.tokenize(text)
        for t in tokens:
            self.assertEqual(
                text[t.start:t.start + t.length],
                t.original,
                f"Offset mismatch for token {t.form}"
            )

    def test_emoji_preservation(self):
        """Test 14: Non-BMP characters don't break offsets."""
        text = '경제 🎉 발전'
        tokens = self.tokenizer.tokenize(text)
        for t in tokens:
            self.assertEqual(
                text[t.start:t.start + t.length],
                t.original,
                f"Offset mismatch for token {t.form} at {t.start}"
            )

    def test_word_groups(self):
        """Test word group building."""
        text = '경제 발전은 중요하다.'
        tokens = self.tokenizer.tokenize(text)
        groups = self.tokenizer.build_word_groups(text, tokens)
        # Should have groups for each whitespace-separated unit
        originals = [g.original for g in groups if g.has_content]
        self.assertTrue(any('경제' in o for o in originals))

    def test_whitespace_preserved(self):
        """Test 14: Whitespace preserved in groups."""
        text = '경제  발전'  # double space
        tokens = self.tokenizer.tokenize(text)
        groups = self.tokenizer.build_word_groups(text, tokens)
        # Reconstruct should match original
        reconstructed = ''.join(g.original for g in groups)
        self.assertEqual(reconstructed, text)


class TestConverter(unittest.TestCase):
    """Test the conversion engine."""

    @classmethod
    def setUpClass(cls):
        if not db_exists():
            raise unittest.SkipTest("Database not found")

        from app.services.tokenizer import TokenizerService
        from app.services.converter import ConverterService
        from app.services.disambiguation import DisambiguationService
        from app.services.dictionary import DictionaryService

        cls.tokenizer = TokenizerService()
        if not cls.tokenizer.is_available:
            raise unittest.SkipTest("Tokenizer not available")

        cls.dictionary = DictionaryService(DB_PATH)
        cls.disambiguation = DisambiguationService()
        cls.converter = ConverterService(cls.tokenizer, cls.disambiguation)

    def _convert(self, text):
        """Helper to run async conversion."""
        async def _do():
            async def lookup_fn(forms):
                return await self.dictionary.batch_lookup_candidates(forms)
            return await self.converter.convert(text, lookup_fn)
        return asyncio.run(_do())

    def _get_display(self, text):
        """Get combined display text."""
        segments, _ = self._convert(text)
        return ''.join(s.display_text for s in segments)

    def _get_segments(self, text):
        segments, _ = self._convert(text)
        return segments

    def test_05_hanguk_conversion(self):
        """Test 5: 한국의 -> 韓國의"""
        display = self._get_display('한국의')
        self.assertIn('韓國', display)
        self.assertIn('의', display)

    def test_06_gyeongje_baljeon(self):
        """Test 6: 경제 발전 -> 經濟 發展 (when context clear)."""
        segments = self._get_segments('경제 발전')
        converted = {s.original: s.display_text for s in segments if s.status == 'converted'}
        # 경제 should convert
        self.assertIn('경제', converted)
        self.assertEqual(converted['경제'], '經濟')

    def test_07_baljeon_candidates(self):
        """Test 7: 발전 has both 發展 and 發電 as candidates."""
        segments = self._get_segments('발전')
        baljeon = [s for s in segments if s.original == '발전'][0]
        origins = [c.get('origin_raw') for c in baljeon.candidates]
        self.assertIn('發展', origins)
        self.assertIn('發電', origins)

    def test_09_native_word_not_converted(self):
        """Test 9: 빠르게 (native word) not converted."""
        segments = self._get_segments('빠르게 달리다')
        self.assertEqual(''.join(s.display_text for s in segments), '빠르게 달리다')

    def test_12_uncertain_kept(self):
        """Test 12: Ambiguous words kept as hangul."""
        segments = self._get_segments('발전')
        baljeon = [s for s in segments if s.original == '발전'][0]
        # With no context, 발전 might be ambiguous between 發展 and 發電
        self.assertEqual(baljeon.status, 'ambiguous')
        self.assertEqual(baljeon.display_text, '발전')

    def test_13_conjugation_preserved(self):
        """Test 13: 발전하였다 preserves verb ending."""
        display = self._get_display('발전하였다')
        # Should contain 하였다 ending (not replaced)
        self.assertIn('하였다', display)

    def test_14_spacing_preserved(self):
        """Test 14: Spaces and newlines preserved."""
        text = '경제  발전\n중요하다.'
        display = self._get_display(text)
        self.assertIn('  ', display)  # double space
        self.assertIn('\n', display)  # newline

    def test_14_punctuation_preserved(self):
        """Test 14: Punctuation and emoji preserved."""
        text = '경제! 발전? 🎉'
        display = self._get_display(text)
        self.assertIn('!', display)
        self.assertIn('?', display)
        self.assertIn('🎉', display)

    def test_14_english_preserved(self):
        """Test 14: English text preserved."""
        text = 'Hello 경제 World'
        display = self._get_display(text)
        self.assertIn('Hello', display)
        self.assertIn('World', display)

    def test_segment_offsets_cover_text(self):
        """Segments cover entire original text without gaps."""
        text = '대한민국의 경제는 빠르게 발전하였다.'
        segments = self._get_segments(text)
        # Verify no gaps
        sorted_segs = sorted(segments, key=lambda s: s.start)
        self.assertEqual(sorted_segs[0].start, 0)
        for i in range(1, len(sorted_segs)):
            self.assertEqual(
                sorted_segs[i].start, sorted_segs[i-1].end,
                f"Gap between segments {i-1} and {i}"
            )
        self.assertEqual(sorted_segs[-1].end, len(text))

    def test_original_text_reconstructed(self):
        """Original text can be perfectly reconstructed from segments."""
        text = '대한민국의 경제는 빠르게 발전하였다.'
        segments = self._get_segments(text)
        reconstructed = ''.join(s.original for s in sorted(segments, key=lambda s: s.start))
        self.assertEqual(reconstructed, text)


class TestDictionaryService(unittest.TestCase):
    """Test dictionary lookup service."""

    @classmethod
    def setUpClass(cls):
        if not db_exists():
            raise unittest.SkipTest("Database not found")

        from app.services.dictionary import DictionaryService
        cls.dict_svc = DictionaryService(DB_PATH)

    def _run(self, coro):
        return asyncio.run(coro)

    def test_lookup_written_form(self):
        """Look up entry by written form."""
        results = self._run(self.dict_svc.lookup_by_written_form('경제'))
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['written_form'], '경제')

    def test_entry_detail(self):
        """Get full entry detail."""
        results = self._run(self.dict_svc.lookup_by_written_form('경제'))
        self.assertGreater(len(results), 0)

        entry = self._run(self.dict_svc.get_entry_detail(results[0]['id']))
        self.assertIsNotNone(entry)
        self.assertIn('senses', entry)
        self.assertGreater(len(entry['senses']), 0)

    def test_search_entries(self):
        """Search entries with pagination."""
        results, total = self._run(self.dict_svc.search_entries('경제'))
        self.assertGreater(total, 0)
        self.assertGreater(len(results), 0)

    def test_search_by_origin(self):
        """Search entries by origin."""
        results, total = self._run(
            self.dict_svc.search_entries('經濟', search_type='origin')
        )
        self.assertGreater(total, 0)

    def test_search_by_entry_id(self):
        """Search by entry ID."""
        results, total = self._run(
            self.dict_svc.search_entries('27733', search_type='entry_id')
        )
        self.assertEqual(total, 1)

    def test_stats(self):
        """Get database stats."""
        stats = self._run(self.dict_svc.get_stats())
        self.assertGreater(stats['total_entries'], 50000)
        self.assertGreater(stats['total_senses'], 70000)


if __name__ == '__main__':
    unittest.main(verbosity=2)
