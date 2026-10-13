import json
import os
import sqlite3
import uuid
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit
from .domain import assess, comments, parse_time
from .providers import DemoProvider

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get('APP_DB', str(ROOT / '.local' / 'app.sqlite3')))
MAX_BODY = 64000

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS posts (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    return db

def valid_link(value, kind='post'):
    if not value and kind == 'profile': return ''
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.hostname not in ('linkedin.com', 'www.linkedin.com') or parsed.username or parsed.password or parsed.port:
        raise ValueError('Nur HTTPS-Links zu linkedin.com sind erlaubt.')
    prefixes = ('/posts/', '/feed/update/', '/pulse/') if kind == 'post' else ('/in/',)
    if not parsed.path.startswith(prefixes):
        raise ValueError('Bitte einen Beitragslink beziehungsweise einen persönlichen /in/-Profillink verwenden.')
    return value

def validate_post(data):
    def field(name, limit, required=True):
        value = data.get(name, '')
        if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
            raise ValueError(f'Ungültiges Feld: {name}')
        return value.strip()
    post = dict(id=str(uuid.uuid4()), source='manual', url=valid_link(field('url', 2000)),
                profile_url=valid_link(field('profile_url', 2000, False), 'profile'),
                author=field('author', 200), text=field('text', 15000), published_at=field('published_at', 100),
                author_type=field('author_type', 30))
    if post['author_type'] not in ('person', 'company', 'unknown'):
        raise ValueError('Ungültige Autorenart.')
    parse_time(post['published_at'])
    return post

def all_posts():
    with connect() as db:
        manual = [json.loads(row[0]) for row in db.execute('SELECT data FROM posts')]
        reviews = {row[0]:json.loads(row[1]) for row in db.execute('SELECT id,data FROM reviews')}
    result = []
    for post in DemoProvider().fetch() + manual:
        review = reviews.get(post['id'], {})
        result.append({**post, 'assessment': assess(post), 'comments': comments(post, review.get('variant', 0)), 'review': review})
    return sorted(result, key=lambda p:p['assessment']['score'], reverse=True)

class Handler(BaseHTTPRequestHandler):
    def respond(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/posts': return self.respond(all_posts())
        if path == '/api/health': return self.respond({'status':'ok', 'provider':'demo + manual'})
        files = {'/':'index.html', '/app.js':'app.js', '/style.css':'style.css'}
        if path not in files: return self.respond({'error':'Nicht gefunden'}, 404)
        body = (ROOT / 'static' / files[path]).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', {'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[path])
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            # Local development server: reject browser requests from other origins.
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host',''):
                return self.respond({'error':'Fremder Ursprung abgelehnt'},403)
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > MAX_BODY: raise ValueError('Ungültige Anfragegröße.')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict): raise ValueError('JSON-Objekt erwartet.')
            path = urlsplit(self.path).path
            if path == '/api/posts':
                post = validate_post(data)
                with connect() as db:
                    db.execute('INSERT INTO posts VALUES (?,?)', (post['id'], json.dumps(post)))
                return self.respond({'id':post['id']},201)
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[:2] == ['api','posts'] and parts[3] in ('review','regenerate'):
                post = next((p for p in all_posts() if p['id'] == parts[2]), None)
                if not post: return self.respond({'error':'Beitrag nicht gefunden'},404)
                review = post['review'].copy()
                if parts[3] == 'regenerate':
                    review['variant'] = review.get('variant',0)+1
                    review.pop('draft',None)
                    review.pop('selected',None)
                else:
                    if 'unsuitable' in data:
                        if not isinstance(data['unsuitable'], bool): raise ValueError('Ungültiger Status.')
                        review['unsuitable'] = data['unsuitable']
                    if 'selected' in data:
                        if data['selected'] not in ('A','B','C'): raise ValueError('Ungültige Option.')
                        review['selected'] = data['selected']
                    if 'draft' in data:
                        if not isinstance(data['draft'],str) or len(data['draft']) > 5000: raise ValueError('Kommentar zu lang.')
                        review['draft'] = data['draft']
                with connect() as db:
                    db.execute('INSERT OR REPLACE INTO reviews VALUES (?,?)',(post['id'],json.dumps(review)))
                return self.respond({'ok':True})
            return self.respond({'error':'Nicht gefunden'},404)
        except (ValueError, TypeError, OverflowError) as exc:
            self.respond({'error':str(exc)},400)

if __name__ == '__main__':
    connect().close()
    host = os.environ.get('HOST','127.0.0.1')
    port = int(os.environ.get('PORT','8000'))
    print(f'heise academy Recherche: http://{host}:{port}',flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
