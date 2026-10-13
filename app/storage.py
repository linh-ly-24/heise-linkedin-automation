"""Additive SQLite schema. Personal data is removed only on explicit confirmation."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from .config import settings
from .transport import ProviderError


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = path

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA busy_timeout=10000')
        db.execute('CREATE TABLE IF NOT EXISTS posts (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS candidates (id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, data TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS generations (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS api_calls (id TEXT PRIMARY KEY, day TEXT NOT NULL, kind TEXT NOT NULL, post_id TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS leases (id TEXT PRIMARY KEY, expires TEXT NOT NULL)')
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def read(self, table):
        if table not in ('posts', 'reviews', 'candidates', 'generations'):
            raise ValueError('Unknown table')
        db = self.connect()
        try:
            return {row[0]: json.loads(row[1]) for row in db.execute(f'SELECT id,data FROM {table}')}
        finally:
            db.close()

    def usage(self):
        db = self.connect()
        try:
            day = now_iso()[:10]
            counts = dict(db.execute('SELECT kind,COUNT(*) FROM api_calls WHERE day=? GROUP BY kind', (day,)))
            unique = db.execute("SELECT COUNT(DISTINCT post_id) FROM api_calls WHERE day=? AND kind='ai'", (day,)).fetchone()[0]
            return {'ai_calls': counts.get('ai', 0), 'search_calls': counts.get('search', 0), 'posts_processed': unique, 'day_utc': day}
        finally:
            db.close()

    @contextmanager
    def reserve(self, kind, post_id=None):
        config = settings()
        resource = kind + ':' + (post_id or 'search')
        with self.transaction() as db:
            now, day = now_iso(), now_iso()[:10]
            db.execute('DELETE FROM leases WHERE expires<=?', (now,))
            if db.execute('SELECT 1 FROM leases WHERE id=?', (resource,)).fetchone():
                raise ProviderError('Für diese Aktion läuft bereits eine Anfrage. Bitte warten.', 409)
            count = db.execute('SELECT COUNT(*) FROM api_calls WHERE day=? AND kind=?', (day, kind)).fetchone()[0]
            if count >= config['max_ai_calls' if kind == 'ai' else 'max_search_calls']:
                raise ProviderError('Konfiguriertes tägliches API-Limit erreicht. Keine weitere Anbieteranfrage.', 429)
            if kind == 'ai':
                old = db.execute("SELECT 1 FROM api_calls WHERE day=? AND kind='ai' AND post_id=?", (day, post_id)).fetchone()
                total = db.execute("SELECT COUNT(DISTINCT post_id) FROM api_calls WHERE day=? AND kind='ai'", (day,)).fetchone()[0]
                if not old and total >= config['max_posts']:
                    raise ProviderError('Tägliches Limit unterschiedlicher Beiträge erreicht.', 429)
            expires = (datetime.now(timezone.utc) + timedelta(seconds=config['timeout'] + 60)).isoformat()
            db.execute('INSERT INTO leases VALUES (?,?)', (resource, expires))
            db.execute('INSERT INTO api_calls VALUES (?,?,?,?)', (str(uuid.uuid4()), day, kind, post_id))
        try:
            yield
        finally:
            with self.transaction() as db:
                db.execute('DELETE FROM leases WHERE id=?', (resource,))

    def expired(self):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=settings()['retention_days'])).isoformat()
        posts = [id for id, p in self.read('posts').items() if p.get('created_at') and p['created_at'] < cutoff]
        candidates = [id for id, p in self.read('candidates').items() if p.get('discovered_at') and p['discovered_at'] < cutoff]
        legacy = sum(not p.get('created_at') for p in self.read('posts').values())
        return {'post_ids': posts, 'candidate_ids': candidates, 'legacy_without_date': legacy}

    def purge(self):
        expired = self.expired()
        with self.transaction() as db:
            for id in expired['post_ids']:
                for table in ('posts', 'reviews', 'generations'):
                    db.execute(f'DELETE FROM {table} WHERE id=?', (id,))
            for id in expired['candidate_ids']:
                db.execute('DELETE FROM candidates WHERE id=?', (id,))
        return {'posts_removed': len(expired['post_ids']), 'candidates_removed': len(expired['candidate_ids'])}
