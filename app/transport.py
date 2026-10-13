"""Small verified-TLS HTTP client with fixed destinations and safe error messages."""
import json
import socket
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError


class ProviderError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward credentials to another destination.


def request_json(url, headers, payload=None, timeout=25):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    request = Request(url, data=data, headers={**headers, 'Accept': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ProviderError('Anbieterantwort ist zu groß.')
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ProviderError('Ungültige Anbieterantwort: JSON-Objekt erwartet.')
            return result
    except HTTPError as exc:
        # Provider bodies may contain submitted post content or credentials: never log them.
        if exc.code in (401, 403):
            raise ProviderError('Anbieter hat den Zugriff abgelehnt. Schlüssel, Rechte und Netzwerkfreigabe prüfen.', 503) from None
        if exc.code == 429:
            raise ProviderError('Ratenlimit oder API-Guthaben erreicht. Später erneut versuchen; Abrechnung prüfen.', 429) from None
        raise ProviderError(f'Anbieteranfrage fehlgeschlagen (HTTP {exc.code}). Es wurde kein Ersatztext erzeugt.') from None
    except (TimeoutError, socket.timeout):
        raise ProviderError('Zeitüberschreitung beim Anbieter. Später ausdrücklich erneut versuchen.', 504) from None
    except URLError:
        raise ProviderError('Anbieter nicht erreichbar. Netzwerk, DNS und TLS prüfen.', 503) from None
    except (UnicodeDecodeError, ValueError):
        raise ProviderError('Anbieter lieferte kein gültiges JSON.') from None
