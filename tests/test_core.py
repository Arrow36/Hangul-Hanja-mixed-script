"""Portable contract tests using a tiny dictionary; no downloaded data required."""
import asyncio
import json
import os
import sqlite3
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import aiosqlite
from fastapi.testclient import TestClient
from app.database import validate_database
from app.schema import create_schema
from app.locales import LANGUAGE_PATHS, resolve_language_path
from app.main import app
from app.services.dictionary import DictionaryService


class TestCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).parent / f'fixture-{uuid.uuid4().hex}.db'
        with sqlite3.connect(cls.path) as db:
            create_schema(db)
            entries = [(1,'경제','經濟'),(2,'발전','發展'),(3,'발전','發電'),(4,'경제 발전','經濟發展'),(5,'서비스','service'),(6,'위하다','爲하다')]
            for eid, word, origin in entries:
                db.execute('INSERT INTO entries(id,target_code,written_form,origin_raw,part_of_speech,raw_json) VALUES(?,?,?,?,?,?)',
                           (eid,eid,word,origin,'동사' if eid == 6 else '명사',json.dumps({'word':word})))
                if eid != 5:
                    db.execute('INSERT INTO conversion_candidates(entry_id,written_form,origin_raw,replacement,replacement_type,is_reliable) VALUES(?,?,?,?,?,1)',
                               (eid,word,origin,'爲' if eid == 6 else origin,'mixed' if eid == 6 else 'pure_hanja'))
            for i in range(1,11):
                db.execute('INSERT INTO senses(id,entry_id,sense_number,definition) VALUES(?,1,?,?)',(i,str(i),f'definition {i}'))
                db.execute('INSERT INTO equivalents(sense_id,language,lemma) VALUES(?,?,?)',(i,'영어','economy'))
                db.execute('INSERT INTO sense_examples(sense_id,group_index,order_index,example_type,example) VALUES(?,0,0,?,?)',(i,'문장','경제'))
            db.execute("INSERT INTO import_metadata(source_filename,sha256,import_timestamp,data_version,total_entries,total_senses,total_examples,origin_entries) VALUES('fixture.zip','test','2026-09-23','fixture',6,10,10,5)")
        db.close()
        cls.environment = patch.dict(os.environ, {'HANJA_DB_PATH':str(cls.path.resolve())})
        cls.environment.start()
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None,None,None)
        cls.environment.stop()
        cls.path.unlink(missing_ok=True)

    def convert(self,text):
        response=self.client.post('/api/convert',json={'text':text,'request_id':'test'})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def test_language_negotiation(self):
        for language, path in [('ko-KR','kr'),('en-US','en'),('ja-JP','ja'),('ar','ar'),('zh-TW','zh')]:
            response=self.client.get('/',headers={'Accept-Language':language},follow_redirects=False)
            self.assertEqual(response.status_code,307)
            self.assertEqual(response.headers['location'],'/'+path)
            self.assertIn('no-store',response.headers['cache-control'])
        self.assertEqual(resolve_language_path(None,'ko;q=0,en;q=0.8,fr;q=0.9'),'fr')
        self.assertEqual(resolve_language_path(None,'ko;q=bad,de'),'zh')
        self.assertEqual(resolve_language_path('en','ko-KR'),'en')

    def test_all_language_routes_and_assets(self):
        for path in LANGUAGE_PATHS:
            for suffix in ['', '/']:
                self.assertEqual(self.client.get('/'+path+suffix).status_code,200)
        self.assertEqual(self.client.get('/ko',follow_redirects=False).headers['location'],'/kr')
        self.assertEqual(self.client.get('/unsupported').status_code,404)
        for asset in ['app.js','languages.js','requests.js','styles.css']:
            self.assertEqual(self.client.get('/static/'+asset).status_code,200)

    def test_query_string_preserved_on_redirect(self):
        r=self.client.get('/?source=share',headers={'Accept-Language':'ko'},follow_redirects=False)
        self.assertEqual(r.headers['location'],'/kr?source=share')

    def test_candidate_contract(self):
        segment=next(s for s in self.convert('경제')['segments'] if s['original']=='경제')
        self.assertEqual(segment['display_text'],'經濟')
        self.assertTrue(segment['candidates'][0]['is_reliable'])
        self.assertEqual(segment['candidates'][0]['replacement_type'],'pure_hanja')

    def test_lossless_offsets_and_whitespace(self):
        for text in ['', ' \n\t', '경제 🎉\n\n발전.', '\t경제\u00a0발전  ']:
            result=self.convert(text)
            self.assertEqual(result['text_length'],len(text))
            self.assertEqual(''.join(s['original'] for s in result['segments']),text)
            end=0
            for segment in result['segments']:
                self.assertEqual(segment['start'],end)
                self.assertEqual(segment['original'],text[segment['start']:segment['end']])
                end=segment['end']
            self.assertEqual(end,len(text))

    def test_context_does_not_cross_sentence_or_paragraph(self):
        for text in ['발전. 경제.', '발전\n경제', '발전!경제', '발전。경제']:
            segment=next(s for s in self.convert(text)['segments'] if s['original']=='발전')
            self.assertEqual(segment['status'],'ambiguous')
            self.assertEqual(segment['display_text'],'발전')
        segment=next(s for s in self.convert('경제 발전')['segments'] if s['original']=='발전')
        self.assertEqual(segment['display_text'],'發展')

    def test_length_limits(self):
        self.assertEqual(self.client.post('/api/convert',json={'text':'가'*20001}).status_code,422)
        self.assertEqual(self.client.get('/api/debug/tokenize',params={'text':'a'*20001}).status_code,422)

    def test_lazy_raw_and_details(self):
        entry=self.client.get('/api/entries/1').json()
        self.assertIsNone(entry['raw_json'])
        self.assertEqual(len(entry['senses']),10)
        self.assertEqual(entry['senses'][0]['examples'][0]['group_index'],0)
        raw=self.client.get('/api/entries/1/raw').json()
        self.assertEqual(raw,{'word':'경제'})
        self.assertEqual(self.client.get('/api/entries/1?include_raw=true').json()['raw_json'],raw)
        self.assertEqual(self.client.get('/api/entries/999/raw').status_code,404)

    def test_bounded_detail_query_count(self):
        async def check():
            queries=[]
            async with aiosqlite.connect(self.path) as db:
                db.row_factory=aiosqlite.Row
                await db.set_trace_callback(queries.append)
                entry=await DictionaryService(str(self.path)).get_entry_detail(1,db)
                self.assertEqual(len(entry['senses']),10)
            self.assertLessEqual(len(queries),10)
            self.assertFalse(any('raw_json' in q for q in queries))
        asyncio.run(check())

    def test_candidate_selection_is_lightweight(self):
        async def check():
            svc=DictionaryService(str(self.path))
            with patch.object(svc,'get_entry_detail',side_effect=AssertionError('unneeded detail query')):
                info=await svc.get_entry_candidate_info(1)
            self.assertEqual(info['entry']['written_form'],'경제')
        asyncio.run(check())

    def test_startup_rejects_missing_and_empty_database(self):
        missing=self.path.with_name('missing-'+uuid.uuid4().hex+'.db')
        with self.assertRaisesRegex(RuntimeError,'import_dictionary'):
            validate_database(missing)
        self.assertFalse(missing.exists())
        empty=self.path.with_name('empty-'+uuid.uuid4().hex+'.db')
        try:
            with sqlite3.connect(empty) as db: create_schema(db)
            db.close()
            with self.assertRaisesRegex(RuntimeError,'empty'): validate_database(empty)
        finally: empty.unlink(missing_ok=True)

    def test_lru_cache_replaces_old_entries(self):
        svc=DictionaryService(str(self.path)); svc._max_cache=2
        svc._cache_candidates('a',[]); svc._cache_candidates('b',[])
        asyncio.run(svc.lookup_candidates('a'))
        svc._cache_candidates('c',[])
        self.assertEqual(list(svc._candidate_cache),['a','c'])

if __name__=='__main__': unittest.main()
