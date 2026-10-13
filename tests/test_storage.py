import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from app.storage import Store
from app.transport import ProviderError
from app.config import settings

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'usage.sqlite')
        self.env=patch.dict(os.environ,{'MAX_AI_CALLS_PER_DAY':'10','MAX_SEARCH_CALLS_PER_DAY':'5','MAX_POSTS_PROCESSED_PER_DAY':'10','PROVIDER_TIMEOUT_SECONDS':'10'})
        self.env.start()
    def tearDown(self):
        self.env.stop();self.tmp.cleanup()
    def test_concurrent_reservation_blocks_duplicate(self):
        errors=[]
        def concurrent():
            try:
                with self.store.reserve('ai','same'):pass
            except ProviderError as e:errors.append(e.status)
        with self.store.reserve('ai','same'):
            thread=threading.Thread(target=concurrent);thread.start();thread.join()
        self.assertEqual(errors,[409])
        self.assertEqual(self.store.usage()['ai_calls'],1)
        with self.store.reserve('ai','same'):pass
        self.assertEqual(self.store.usage()['ai_calls'],2)
        self.assertEqual(self.store.usage()['posts_processed'],1)
    def test_atomic_daily_cap_across_threads(self):
        os.environ['MAX_AI_CALLS_PER_DAY']='1'
        barrier=threading.Barrier(3);outcomes=[]
        def attempt(id):
            barrier.wait()
            try:
                with self.store.reserve('ai',id):outcomes.append('ok')
            except ProviderError as e:outcomes.append(e.status)
        threads=[threading.Thread(target=attempt,args=(str(i),)) for i in range(2)]
        for t in threads:t.start()
        barrier.wait()
        for t in threads:t.join()
        self.assertCountEqual(outcomes,['ok',429])
        self.assertEqual(self.store.usage()['ai_calls'],1)
    def test_failed_calls_count_and_release_lock(self):
        with self.assertRaises(ProviderError):
            with self.store.reserve('search'):raise ProviderError('Provider unavailable')
        with self.store.reserve('search'):pass
        self.assertEqual(self.store.usage()['search_calls'],2)
    def test_zero_limit_and_expired_lease(self):
        os.environ['MAX_AI_CALLS_PER_DAY']='0'
        with self.assertRaises(ProviderError):
            with self.store.reserve('ai','a'):pass
        self.assertEqual(self.store.usage()['ai_calls'],0)
        with self.store.transaction() as db:db.execute('INSERT INTO leases VALUES (?,?)',('search:search','2000-01-01T00:00:00+00:00'))
        with self.store.reserve('search'):pass
    def test_invalid_configuration(self):
        for name,value in [('MAX_AI_CALLS_PER_DAY','-1'),('MAX_SEARCH_RESULTS','21'),('DATA_RETENTION_DAYS','0'),('PROVIDER_TIMEOUT_SECONDS','abc')]:
            with patch.dict(os.environ,{name:value}),self.assertRaises(ValueError):settings()
