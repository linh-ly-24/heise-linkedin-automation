from urllib.parse import urlsplit, urlunsplit, unquote


def valid_link(value, kind='post'):
    if not value and kind == 'profile':
        return ''
    if not isinstance(value, str) or len(value) > 2000 or any(ord(c) <= 32 for c in value):
        raise ValueError('Ungültiger LinkedIn-Link.')
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.hostname not in ('linkedin.com', 'www.linkedin.com')
            or parsed.username or parsed.password or parsed.port):
        raise ValueError('Nur HTTPS-Links zu linkedin.com sind erlaubt.')
    prefixes = ('/posts/', '/feed/update/', '/pulse/') if kind == 'post' else ('/in/',)
    if not parsed.path.startswith(prefixes) or not any(parsed.path[len(prefix):] for prefix in prefixes if parsed.path.startswith(prefix)):
        raise ValueError('Bitte einen Beitragslink beziehungsweise einen persönlichen /in/-Profillink verwenden.')
    decoded = unquote(parsed.path)
    if any(ord(c) <= 32 for c in decoded) or '\\' in decoded or '/..' in decoded:
        raise ValueError('Ungültiger LinkedIn-Pfad.')
    return value


def canonical_url(value):
    parsed = urlsplit(valid_link(value))
    return urlunsplit(('https', 'www.linkedin.com', parsed.path.rstrip('/'), '', ''))
