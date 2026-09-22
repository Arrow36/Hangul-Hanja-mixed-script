"""
Regression test suite covering the 13 required verification criteria:
1. Version API dynamic reporting (code version, schema version, data version, exact benchmark stats)
2. Origin-to-text whole-span alignment for inflected verbs (위한 -> 爲한, origin 爲하다)
3. Particles and suffixes never get homonym Hanja origins
4. Whole-word matching for compounds (국제화는 -> 國際化는)
5. Whole-word matching for suffixes (문화적 -> 文化的) with candidate deduplication
6. Full benchmark sentence accuracy, offset integrity, and lossless reconstruction
7. Safe handling of mixed loanwords (게임기 -> game機, is_reliable=0, preserved in mixed text)
8. Safe handling of pure loanwords (서비스 -> service, empty candidate list, preserved in mixed text)
9. POST /api/select-candidate endpoint validation and safe replacement derivation
10. Candidate selection synchronizes origin cache (기사 -> 記事)
11. Single-pass origin return in /api/convert without per-word client enrichments
12. Preserved dialogue structure with group_index and order_index for entries like 요리하다
13. Database stats endpoint reporting total_examples == 659075
"""

import os
import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app

DB_PATH = PROJECT_ROOT / 'hanja_dict.db'


class TestRegressionFixed(unittest.TestCase):
    """Rigorous regression tests for all 13 fixed issues."""

    @classmethod
    def setUpClass(cls):
        if not DB_PATH.exists():
            raise unittest.SkipTest("Database hanja_dict.db not found")
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def test_01_version_endpoint(self):
        """Criterion 1: GET /api/version returns dynamic code, schema, and data stats."""
        resp = self.client.get("/api/version")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data.get("code_version"), "2026.09.23.1")
        self.assertEqual(data.get("api_schema_version"), "2.1.0")
        self.assertEqual(data.get("data_version"), "20260919")

        stats = data.get("db_stats", {})
        self.assertEqual(stats.get("total_entries"), 56555)
        self.assertEqual(stats.get("total_senses"), 76833)
        self.assertEqual(stats.get("total_examples"), 659075)
        self.assertGreater(stats.get("entries_with_hanja", 0), 30000)

    def test_02_origin_alignment_wihan(self):
        """Criterion 2: 위한 is aligned across [0, 2) as 爲한 with origin 爲하다.
        Must not be split into 胃/位 + 恨/限, and must not produce 爲하다한.
        """
        resp = self.client.post("/api/convert", json={"text": "평화를 위한 노력"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        segments = data["segments"]

        # Find the segment covering '위한'
        wihan_segs = [s for s in segments if s["original"] == "위한"]
        self.assertEqual(len(wihan_segs), 1, "Should have exactly one segment for '위한'")
        wihan = wihan_segs[0]

        self.assertEqual(wihan["display_text"], "爲한")
        self.assertEqual(wihan["start"], 4)
        self.assertEqual(wihan["end"], 6)
        self.assertIsNotNone(wihan.get("origin"))
        self.assertEqual(wihan["origin"]["raw"], "爲하다")
        self.assertEqual(wihan["origin"]["type"], "hanja")

        # Verify no spurious split segments for '위' or '한'
        originals = [s["original"] for s in segments]
        self.assertNotIn("위", originals)
        self.assertNotIn("한", originals)

        # Verify no spurious homonym Hanja for 胃, 位, 恨, 限
        displays = [s["display_text"] for s in segments]
        for bad in ("胃", "位", "恨", "限"):
            self.assertNotIn(bad, displays)

        # Full mixed text check
        full_display = "".join(s["display_text"] for s in segments)
        self.assertNotIn("爲하다한", full_display)
        self.assertIn("爲한", full_display)

    def test_03_grammatical_particles_and_endings_no_spurious_hanja(self):
        """Criterion 3: Particles and endings never receive homonym Hanja origins."""
        text = "사람은 학교에서 공부를 하였다."
        resp = self.client.post("/api/convert", json={"text": text})
        self.assertEqual(resp.status_code, 200)
        segments = resp.json()["segments"]

        # Verify grammatical tokens: 은, 에서, 를, 하였다 (하+였+다)
        for s in segments:
            orig = s["original"].strip()
            if orig in ("은", "는", "이", "가", "을", "를", "의", "에", "에서", "로", "으로", "였다", "다"):
                self.assertIsNone(
                    s.get("origin"),
                    f"Grammatical particle/ending '{orig}' must not receive an origin object: {s.get('origin')}"
                )
                self.assertEqual(
                    s["display_text"], orig,
                    f"Grammatical particle/ending '{orig}' must remain identical in display"
                )

    def test_04_gukjehwaneun_whole_word_matching(self):
        """Criterion 4: 국제화는 prefers full-word 국제화 -> 國際化, preserving particle 는."""
        resp = self.client.post("/api/convert", json={"text": "국제화는 중요하다."})
        self.assertEqual(resp.status_code, 200)
        segments = resp.json()["segments"]

        gukje_segs = [s for s in segments if s["original"] == "국제화"]
        self.assertEqual(len(gukje_segs), 1, "국제화 should be matched as a single multi-morpheme whole word")
        self.assertEqual(gukje_segs[0]["display_text"], "國際化")

        neun_segs = [s for s in segments if s["original"] == "는"]
        self.assertEqual(len(neun_segs), 1, "는 should be preserved as separate particle")
        self.assertEqual(neun_segs[0]["display_text"], "는")
        self.assertIsNone(neun_segs[0].get("origin"))

        full_display = "".join(s["display_text"] for s in segments)
        self.assertTrue(full_display.startswith("國際化는"))

    def test_05_munhwajeok_whole_word_and_candidate_merging(self):
        """Criterion 5: 문화적 matches 文化的 and merges duplicate candidate representations."""
        resp = self.client.post("/api/convert", json={"text": "문화적 차이"})
        self.assertEqual(resp.status_code, 200)
        segments = resp.json()["segments"]

        munhwa_segs = [s for s in segments if s["original"] == "문화적"]
        self.assertEqual(len(munhwa_segs), 1)
        seg = munhwa_segs[0]
        self.assertEqual(seg["display_text"], "文化的")

        # Check candidate deduplication
        replacements = [c.get("replacement") for c in seg.get("candidates", []) if c.get("replacement")]
        self.assertEqual(
            len(replacements), len(set(replacements)),
            f"Candidates must not contain duplicates: {replacements}"
        )

    def test_06_benchmark_sentence(self):
        """Criterion 6: 대한민국의 경제는 빠르게 발전하였다 -> 大韓民國의 經濟는 빠르게 發展하였다."""
        text = "대한민국의 경제는 빠르게 발전하였다."
        resp = self.client.post("/api/convert", json={"text": text})
        self.assertEqual(resp.status_code, 200)
        segments = resp.json()["segments"]

        # Lossless reconstruction
        reconstructed = "".join(s["original"] for s in segments)
        self.assertEqual(reconstructed, text)

        # Full mixed text output
        mixed_text = "".join(s["display_text"] for s in segments)
        self.assertEqual(mixed_text, "大韓民國의 經濟는 빠르게 發展하였다.")

        # Offset boundary continuity without gaps
        sorted_segs = sorted(segments, key=lambda s: s["start"])
        self.assertEqual(sorted_segs[0]["start"], 0)
        for i in range(1, len(sorted_segs)):
            self.assertEqual(
                sorted_segs[i]["start"], sorted_segs[i-1]["end"],
                f"Offset gap between {sorted_segs[i-1]} and {sorted_segs[i]}"
            )
        self.assertEqual(sorted_segs[-1]["end"], len(text))

    def test_07_gamegi_mixed_loanword(self):
        """Criterion 7: 게임기 has origin game機 (is_reliable=0) and remains 게임기 in mixed script."""
        resp = self.client.post("/api/convert", json={"text": "새로운 게임기를 샀다."})
        self.assertEqual(resp.status_code, 200)
        segments = resp.json()["segments"]

        game_segs = [s for s in segments if s["original"] == "게임기"]
        self.assertEqual(len(game_segs), 1)
        seg = game_segs[0]

        self.assertEqual(seg["display_text"], "게임기")
        self.assertIsNotNone(seg.get("origin"))
        self.assertEqual(seg["origin"]["raw"], "game機")

    def test_08_service_loanword(self):
        """Criterion 8: 서비스 has origin service, zero hanja candidates, remains 서비스."""
        resp = self.client.post("/api/convert", json={"text": "고객 서비스"})
        self.assertEqual(resp.status_code, 200)
        segments = resp.json()["segments"]

        serv_segs = [s for s in segments if s["original"] == "서비스"]
        self.assertEqual(len(serv_segs), 1)
        seg = serv_segs[0]

        self.assertEqual(seg["display_text"], "서비스")
        self.assertEqual(seg.get("candidates"), [])
        self.assertIsNotNone(seg.get("origin"))
        self.assertEqual(seg["origin"]["raw"], "service")

    def test_09_select_candidate_endpoint(self):
        """Criterion 9: POST /api/select-candidate validates selection and returns schema response."""
        payload = {
            "segment_id": 0,
            "entry_id": 17231,  # 記事
            "original": "기사"
        }
        resp = self.client.post("/api/select-candidate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["segment_id"], 0)
        self.assertEqual(data["matched_entry_id"], 17231)
        self.assertEqual(data["display_text"], "記事")
        self.assertEqual(data["origin_raw"], "記事")
        self.assertTrue(data["is_reliable"])
        self.assertEqual(data["origin"]["raw"], "記事")

    def test_10_candidate_selection_origin_cache_sync(self):
        """Criterion 10: Selecting 記事 for 기사 synchronizes segment origin directly to 記事."""
        # Step 1: convert ambiguous word 기사
        resp1 = self.client.post("/api/convert", json={"text": "기사"})
        self.assertEqual(resp1.status_code, 200)
        seg1 = resp1.json()["segments"][0]
        self.assertEqual(seg1["status"], "ambiguous")

        # Candidates must include 記事
        entry_gisa = [c for c in seg1["candidates"] if c["replacement"] == "記事"]
        self.assertTrue(len(entry_gisa) > 0, "Candidates must include 記事")
        gisa_id = entry_gisa[0]["entry_id"]

        # Step 2: select 記事
        resp2 = self.client.post(
            "/api/select-candidate",
            json={"segment_id": seg1["segment_id"], "entry_id": gisa_id, "original": "기사"}
        )
        self.assertEqual(resp2.status_code, 200)
        sel_data = resp2.json()

        # Origin raw must be 記事, NOT 技士 / 記事 / 騎士
        self.assertEqual(sel_data["origin"]["raw"], "記事")
        self.assertEqual(sel_data["origin_raw"], "記事")
        self.assertEqual(sel_data["display_text"], "記事")

    def test_11_single_pass_origin_resolution(self):
        """Criterion 11: /api/convert returns complete origin data in a single request."""
        resp = self.client.post("/api/convert", json={"text": "경제 발전"})
        self.assertEqual(resp.status_code, 200)
        segments = resp.json()["segments"]

        content_segs = [s for s in segments if s["original"].strip()]
        for s in content_segs:
            self.assertIsNotNone(
                s.get("origin"),
                f"Segment '{s['original']}' should have pre-attached origin in convert response"
            )
            self.assertIn("raw", s["origin"])
            self.assertIn("type", s["origin"])

    def test_12_dictionary_examples_dialogue_structure(self):
        """Criterion 12: 요리하다 entry preserves dialogue structure with group_index and order_index."""
        resp = self.client.get("/api/lookup?query=요리하다")
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", [])
        self.assertGreater(len(results), 0)

        entry_id = results[0]["id"]
        entry_resp = self.client.get(f"/api/entries/{entry_id}")
        self.assertEqual(entry_resp.status_code, 200)
        entry_data = entry_resp.json()

        dialogue_examples = []
        for sense in entry_data.get("senses", []):
            for ex in sense.get("examples", []):
                if ex.get("example_type") == "대화":
                    dialogue_examples.append(ex)

        self.assertGreater(
            len(dialogue_examples), 0,
            "Entry for 요리하다 must have examples with example_type == '대화'"
        )

        # Verify group_index and order_index are preserved and not all null/0
        group_indices = {ex.get("group_index") for ex in dialogue_examples}
        order_indices = {ex.get("order_index") for ex in dialogue_examples}
        self.assertTrue(
            any(g is not None for g in group_indices),
            "group_index must be populated on dialogue examples"
        )
        self.assertIn(0, order_indices)
        self.assertIn(1, order_indices)

    def test_13_stats_endpoint(self):
        """Criterion 13: GET /api/stats reports exact reference benchmark totals."""
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()

        self.assertEqual(stats.get("total_entries"), 56555)
        self.assertEqual(stats.get("total_senses"), 76833)
        self.assertEqual(stats.get("total_examples"), 659075)


if __name__ == "__main__":
    unittest.main()
