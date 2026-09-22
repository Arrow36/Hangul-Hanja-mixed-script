"""
End-to-end API testing script covering live HTTP endpoints against port 8000.
"""

import os
import sys
import unittest
import httpx

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = os.environ.get('HANJA_BASE_URL', 'http://127.0.0.1:8000')


def is_server_running():
    try:
        r = httpx.get(f"{BASE_URL}/api/version", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


class TestE2EApi(unittest.TestCase):
    """End-to-end tests against the live server."""

    @classmethod
    def setUpClass(cls):
        if not is_server_running():
            raise unittest.SkipTest(f"Server is not running on {BASE_URL}")
        cls.client = httpx.Client(base_url=BASE_URL, timeout=10.0, follow_redirects=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'client'):
            cls.client.close()

    def test_01_index_html(self):
        """Test 1: Serve main HTML page."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn('<title>汉谚混写·국한문혼용체</title>', html)
        self.assertIn('/static/app.js', html)

    def test_02_version(self):
        """Test 2: Dynamic /api/version."""
        resp = self.client.get("/api/version")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["code_version"], "2026.09.23.1")
        self.assertEqual(data["api_schema_version"], "2.1.0")
        self.assertEqual(data["data_version"], "20260919")
        self.assertEqual(data["db_stats"]["total_examples"], 659075)

    def test_03_stats(self):
        """Test 3: Database /api/stats."""
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()
        self.assertEqual(stats['total_entries'], 56555)
        self.assertEqual(stats['total_senses'], 76833)
        self.assertEqual(stats['total_examples'], 659075)
        self.assertEqual(stats['entries_with_origin'], 36151)
        self.assertEqual(stats['entries_with_hanja_origin'], 34150)

    def test_04_convert_cases(self):
        """Test 4: Key conversion cases."""
        test_cases = [
            ("대한민국의 경제는 빠르게 발전하였다.", "大韓民國의 經濟는 빠르게 發展하였다."),
            ("한국의", "韓國의"),
            ("경제 발전", "經濟 發展"),
            ("위하여", "爲하여"),
            ("발전", "발전"),  # ambiguous without context
            ("기사", "기사"),  # ambiguous with 4 candidates
            ("게임기", "게임기"),  # loanword mixed, safe preservation
        ]

        for inp, expected in test_cases:
            resp = self.client.post('/api/convert', json={'text': inp})
            self.assertEqual(resp.status_code, 200)
            res = resp.json()
            text_out = ''.join(s['display_text'] for s in res['segments'])
            orig_out = ''.join(s['original'] for s in res['segments'])
            self.assertEqual(orig_out, inp)
            if inp in ("대한민국의 경제는 빠르게 발전하였다.", "한국의", "경제 발전", "위하여"):
                self.assertEqual(text_out, expected)

    def test_05_candidate_options(self):
        """Test 5: Candidates for 기사 (4) and 발전 (2)."""
        res_kisa = self.client.post('/api/convert', json={'text': '기사'}).json()
        kisa_seg = res_kisa['segments'][0]
        self.assertEqual(len(kisa_seg['candidates']), 4)
        kisa_origins = {c['origin_raw'] for c in kisa_seg['candidates']}
        self.assertIn('技士', kisa_origins)
        self.assertIn('記事', kisa_origins)
        self.assertIn('棋士/碁士', kisa_origins)
        self.assertIn('騎士', kisa_origins)

        res_bal = self.client.post('/api/convert', json={'text': '발전'}).json()
        bal_seg = res_bal['segments'][0]
        self.assertEqual(len(bal_seg['candidates']), 2)
        bal_origins = {c['origin_raw'] for c in bal_seg['candidates']}
        self.assertIn('發展', bal_origins)
        self.assertIn('發電', bal_origins)

    def test_06_lookup_and_entries(self):
        """Test 6: /api/lookup and /api/entries/{id}."""
        lookup_res = self.client.get('/api/lookup?query=경제&search_type=written_form&page=1&page_size=10').json()
        self.assertGreater(lookup_res['total'], 0)
        first_id = lookup_res['results'][0]['id']

        entry_detail = self.client.get(f"/api/entries/{first_id}").json()
        self.assertEqual(entry_detail['id'], first_id)
        self.assertEqual(entry_detail['written_form'], '경제')
        self.assertEqual(entry_detail['origin_raw'], '經濟')
        self.assertGreater(len(entry_detail['senses']), 0)

    def test_07_select_candidate(self):
        """Test 7: /api/select-candidate endpoint."""
        sel_res = self.client.post('/api/select-candidate', json={'segment_id': 0, 'entry_id': 17231, 'original': '기사'}).json()
        self.assertEqual(sel_res['status'], 'ok')
        self.assertEqual(sel_res['display_text'], '記事')
        self.assertEqual(sel_res['origin']['raw'], '記事')


if __name__ == '__main__':
    unittest.main()
