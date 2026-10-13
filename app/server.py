import hashlib
import json
import os
import uuid
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs
from .domain import assess, parse_time
from .providers import DemoProvider, SEARCH_TERMS, search_provider
from .generators import DemoCommentGenerator, OpenAICommentGenerator
from .config import settings
from .links import valid_link, canonical_url
from .storage import Store, now_iso
from .transport import ProviderError

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get('APP_DB', str(ROOT / '.local' / 'app.sqlite3')))
MAX_BODY = 64000


def store():
    return Store(DB)


def connect():
    return store().connect()


def validate_post(data):
    def field(name, limit, required=True):
        value = data.get(name, '')
        if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
            raise ValueError(f'Ungültiges Feld: {name}')
        return value.strip()
    published = field('published_at', 100, False)
    if published:
        parse_time(published)
    post = dict(id=str(uuid.uuid4()), source='manual', url=canonical_url(field('url', 2000)),
                profile_url=valid_link(field('profile_url', 2000, False), 'profile'),
                author=field('author', 200, False), text=field('text', 15000, False),
                published_at=published or None, author_type=field('author_type', 30),
                verified=False, created_at=now_iso(), publication_evidence=field('publication_evidence', 1000, False))
    if post['author_type'] not in ('person', 'company', 'unknown'):
        raise ValueError('Ungültige Autorenart.')
    return post


def digest(post):
    return hashlib.sha256(json.dumps({k: post.get(k) for k in ('text', 'published_at', 'author_type', 'verified')}, sort_keys=True).encode()).hexdigest()


def all_posts(include_demo=False):
    db = store()
    reviews, generations = db.read('reviews'), db.read('generations')
    source_posts = list(db.read('posts').values())
    if include_demo:
        source_posts = DemoProvider().fetch()
    result = []
    for raw in source_posts:
        post = {**raw, 'verified': raw.get('verified', False)}
        review = reviews.get(post['id'], {})
        if post['source'] == 'demo':
            generation = DemoCommentGenerator().generate(post, review.get('variant', 0))
        else:
            generation = generations.get(post['id'], {})
            if generation.get('post_hash') != digest(post):
                generation = {}
        result.append({**post, 'assessment': assess(post), 'comments': generation.get('comments', []),
            'generation': generation, 'review': review, 'status': 'demo' if post['source'] == 'demo' else ('verified' if post['verified'] else 'unverified')})
    return sorted(result, key=lambda p: p['assessment']['score'], reverse=True)


def find_post(id):
    return next((p for p in all_posts(id.startswith('demo-')) if p['id'] == id), None)


def status():
    config = settings()
    expired = store().expired()
    return {'model': config['model'], 'ai_ready': config['ai_key_present'] and config['ai_authorized'],
        'ai_key_present': config['ai_key_present'], 'ai_authorized': config['ai_authorized'],
        'search_provider': config['search_provider'], 'search_ready': config['search_provider'] == 'brave' and config['search_key_present'] and config['search_authorized'],
        'search_key_present': config['search_key_present'], 'search_authorized': config['search_authorized'],
        'limits': {k:config[k] for k in ('max_ai_calls', 'max_search_calls', 'max_results', 'max_posts', 'retention_days')},
        'usage': store().usage(), 'topics': list(SEARCH_TERMS),
        'retention': {'expired_posts': len(expired['post_ids']), 'expired_candidates': len(expired['candidate_ids']), 'legacy_without_date': expired['legacy_without_date']}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # No request bodies, credentials, user text, or query strings in logs.
        return

    def respond(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            parsed = urlsplit(self.path)
            if parsed.path == '/api/posts':
                return self.respond(all_posts(parse_qs(parsed.query).get('mode') == ['demo']))
            if parsed.path == '/api/candidates':
                return self.respond(sorted(store().read('candidates').values(), key=lambda p:p['discovered_at'], reverse=True))
            if parsed.path == '/api/status':
                return self.respond(status())
            if parsed.path == '/api/health':
                return self.respond({'status': 'ok', 'provider': 'manual + explicit demo; optional brave/openai'})
            files = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}
            if parsed.path not in files:
                return self.respond({'error': 'Nicht gefunden'}, 404)
            body = (ROOT / 'static' / files[parsed.path]).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', {'/': 'text/html; charset=utf-8', '/app.js': 'text/javascript; charset=utf-8', '/style.css': 'text/css; charset=utf-8'}[parsed.path])
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)
        except ValueError as exc:
            self.respond({'error': str(exc)}, 400)

    def do_POST(self):
        try:
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                return self.respond({'error': 'Fremder Ursprung abgelehnt'}, 403)
            # Reject cross-site simple requests; fetch uses application/json.
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.respond({'error': 'Content-Type application/json erforderlich'}, 415)
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > MAX_BODY:
                raise ValueError('Ungültige Anfragegröße.')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('JSON-Objekt erwartet.')
            path = urlsplit(self.path).path
            if path == '/api/posts':
                if data.get('import_authorized') is not True:
                    raise ProviderError('Bitte die Berechtigung zur lokalen Verarbeitung bestätigen.', 403)
                post = validate_post(data)
                with store().transaction() as db:
                    for row in db.execute('SELECT data FROM posts'):
                        if canonical_url(json.loads(row[0])['url']) == post['url']:
                            raise ProviderError('Dieser Beitragslink wurde bereits importiert. Bestehenden Beitrag prüfen.', 409)
                    db.execute('INSERT INTO posts VALUES (?,?)', (post['id'], json.dumps(post)))
                return self.respond({'id': post['id']}, 201)
            if path == '/api/search':
                if data.get('authorized') is not True:
                    raise ProviderError('Suchauftrag und zulässige Verwendung der Suchergebnisse bestätigen.', 403)
                topic = data.get('topic')
                if not isinstance(topic, str) or topic not in SEARCH_TERMS:
                    raise ValueError('Unbekanntes Suchthema.')
                config = settings()
                if not config['search_key_present'] or not config['search_authorized']:
                    # Preflight does not spend the call budget.
                    raise ProviderError('Suche nicht eingerichtet. SEARCH_PROVIDER=brave, BRAVE_SEARCH_API_KEY und SEARCH_USE_AUTHORIZED=true serverseitig konfigurieren. Alternativ manuell recherchieren.', 503)
                provider = search_provider()
                with store().reserve('search'):
                    candidates = provider.search(topic)
                    added = 0
                    with store().transaction() as db:
                        existing = {canonical_url(json.loads(row[0])['url']) for row in db.execute('SELECT data FROM posts')}
                        for candidate in candidates:
                            if candidate['url'] in existing:
                                continue
                            cur = db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?)', (candidate['id'], candidate['url'], json.dumps(candidate)))
                            added += cur.rowcount
                    return self.respond({'added': added, 'found': len(candidates), 'note': 'Suchtreffer sind unverifizierte Kandidaten. Keine LinkedIn-Seite wurde abgerufen.'})
            if path == '/api/retention/purge':
                if data.get('confirm') is not True:
                    raise ValueError('Löschung muss ausdrücklich bestätigt werden.')
                return self.respond(store().purge())
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[:2] == ['api', 'candidates'] and parts[3] == 'verify':
                candidate = store().read('candidates').get(parts[2])
                if not candidate:
                    return self.respond({'error': 'Kandidat nicht gefunden'}, 404)
                return self.verify(parts[2], data, candidate)
            if len(parts) != 4 or parts[:2] != ['api', 'posts']:
                return self.respond({'error': 'Nicht gefunden'}, 404)
            post = find_post(parts[2])
            if not post:
                return self.respond({'error': 'Beitrag nicht gefunden'}, 404)
            if parts[3] == 'verify':
                return self.verify(post['id'], data)
            if parts[3] in ('generate', 'regenerate'):
                return self.generate(post, data, parts[3] == 'regenerate')
            if parts[3] == 'review':
                return self.review(post, data)
            return self.respond({'error': 'Nicht gefunden'}, 404)
        except ProviderError as exc:
            self.respond({'error': str(exc)}, exc.status)
        except (ValueError, TypeError, OverflowError, UnicodeDecodeError) as exc:
            self.respond({'error': str(exc)}, 400)
        except Exception:
            # Do not expose a traceback containing provider payloads or credentials.
            self.respond({'error': 'Interner Fehler. Keine Anbieter- oder Zugangsdaten werden angezeigt.'}, 500)

    def verify(self, id, data, candidate=None):
        if id.startswith('demo-'):
            raise ValueError('Fiktive Beispiele können nicht als echte Beiträge verifiziert werden.')
        if any(data.get(k) is not True for k in ('original_checked', 'author_checked', 'time_checked', 'import_authorized')):
            raise ValueError('Originaltext, Autorenart, tatsächliche Zeit und Verarbeitungsberechtigung müssen bestätigt werden.')
        post = validate_post(data)
        if not post['text'] or not post['author'] or not post['published_at'] or not post['publication_evidence']:
            raise ValueError('Für die Verifikation fehlen Originaltext, Autor, Veröffentlichungszeit oder Zeitbeleg.')
        post['id'] = id
        post.update(verified=True, verified_at=now_iso(), verification_method='human')
        with store().transaction() as db:
            existing = db.execute('SELECT data FROM posts WHERE id=?', (id,)).fetchone()
            if existing:
                before = json.loads(existing[0])
                if post['url'] != canonical_url(before['url']):
                    raise ValueError('Der ursprüngliche Beitragslink darf bei der Verifikation nicht geändert werden.')
                if before.get('verified'):
                    raise ProviderError('Bereits verifiziert. Bestehende Daten werden nicht überschrieben.', 409)
                post['created_at'] = before.get('created_at')  # Preserve undated legacy data.
            if candidate:
                if post['url'] != candidate['url']:
                    raise ValueError('Der ursprüngliche Kandidatenlink darf nicht geändert werden.')
                post['source'] = candidate['source']
                post['discovered_at'] = candidate['discovered_at']
            for row in db.execute('SELECT id,data FROM posts'):
                if row[0] != id and canonical_url(json.loads(row[1])['url']) == post['url']:
                    raise ProviderError('Dieser Link wurde bereits importiert. Bestehenden Beitrag prüfen.', 409)
            db.execute('INSERT OR REPLACE INTO posts VALUES (?,?)', (id, json.dumps(post)))
            if candidate:
                # Keep search evidence and snippet; mark candidate promoted rather than deleting it.
                candidate['status'] = 'verified'
                db.execute('UPDATE candidates SET data=? WHERE id=?', (json.dumps(candidate), id))
        return self.respond({'id': id, 'assessment': assess(post)})

    def generate(self, post, data, regenerate=False):
        if post['source'] == 'demo':
            review = post['review'].copy()
            if regenerate:
                review['variant'] = review.get('variant', 0) + 1
                review.pop('draft', None)
                review.pop('selected', None)
                review['reviewed'] = False
                with store().transaction() as db:
                    db.execute('INSERT OR REPLACE INTO reviews VALUES (?,?)', (post['id'], json.dumps(review)))
            return self.respond(DemoCommentGenerator().generate(post, review.get('variant', 0)))
        assessment = assess(post)
        if not post.get('verified') or not assessment['eligible'] or not assessment['enough_context'] or post['review'].get('unsuitable'):
            raise ValueError('Nur menschlich verifizierte, geeignete Beiträge mit genügend Inhalt können KI-Kommentare erhalten.')
        if data.get('authorized') is not True:
            raise ProviderError('Übermittlung des Originaltexts an OpenAI muss ausdrücklich bestätigt werden.', 403)
        if post['generation'] and not regenerate:
            return self.respond({**post['generation'], 'cached': True})
        config = settings()
        if not config['ai_key_present'] or not config['ai_authorized']:
            raise ProviderError('KI nicht eingerichtet. OPENAI_API_KEY und OPENAI_PROCESSING_AUTHORIZED=true im Server konfigurieren. ChatGPT-Abonnements enthalten nicht automatisch API-Zugang.', 503)
        with store().reserve('ai', post['id']):
            generated = OpenAICommentGenerator().generate(post)
            generated.update(created_at=now_iso(), post_hash=digest(post), review_required=True)
            with store().transaction() as db:
                # Never erase a human-edited draft on regeneration.
                db.execute('INSERT OR REPLACE INTO generations VALUES (?,?)', (post['id'], json.dumps(generated)))
                row = db.execute('SELECT data FROM reviews WHERE id=?', (post['id'],)).fetchone()
                review = json.loads(row[0]) if row else {}
                review['reviewed'] = False
                db.execute('INSERT OR REPLACE INTO reviews VALUES (?,?)', (post['id'], json.dumps(review)))
        return self.respond({**generated, 'cached': False})

    def review(self, post, data):
        with store().transaction() as db:
            row = db.execute('SELECT data FROM reviews WHERE id=?', (post['id'],)).fetchone()
            review = json.loads(row[0]) if row else {}
            for key in ('unsuitable', 'reviewed'):
                if key in data:
                    if not isinstance(data[key], bool):
                        raise ValueError('Ungültiger Status.')
                    review[key] = data[key]
            if 'selected' in data:
                if data['selected'] not in ('A', 'B', 'C'):
                    raise ValueError('Ungültige Option.')
                if data['selected'] != review.get('selected'):
                    review['reviewed'] = False
                review['selected'] = data['selected']
            if 'draft' in data:
                if not isinstance(data['draft'], str) or len(data['draft']) > 5000:
                    raise ValueError('Kommentar zu lang.')
                if data['draft'] != review.get('draft') or data.get('selected', review.get('selected')) != review.get('selected'):
                    review['reviewed'] = False
                review['draft'] = data['draft']
            if review.get('unsuitable'):
                review['reviewed'] = False
            if data.get('reviewed') is True:
                if not post['assessment']['eligible'] or not post['comments'] or not review.get('draft', '').strip() or review.get('unsuitable'):
                    raise ValueError('Nur ein geeigneter Beitrag mit gespeichertem Entwurf kann als geprüft markiert werden.')
                review['reviewed'] = True
                review['reviewed_at'] = now_iso()
            db.execute('INSERT OR REPLACE INTO reviews VALUES (?,?)', (post['id'], json.dumps(review)))
        return self.respond({'ok': True, 'review': review})


if __name__ == '__main__':
    settings()  # Fail early on invalid limits, without printing credentials.
    connect().close()
    host, port = os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '8000'))
    http = ThreadingHTTPServer((host, port), Handler)
    print(f'heise academy Recherche: http://{host}:{port}', flush=True)
    http.serve_forever()
