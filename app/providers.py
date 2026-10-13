"""Provider boundary: implement fetch() for a separately authorized data source."""
from datetime import datetime, timezone, timedelta
from typing import Protocol

class PostProvider(Protocol):
    def fetch(self) -> list[dict]: ...

class DemoProvider:
    def fetch(self):
        now = datetime.now(timezone.utc)
        samples = [
            ('demo-ai', 'Beispielperson · Lea', 'KI', 2, 'Bei unserem KI-Prototyp waren plausible Antworten das größte Problem. Ich habe gelernt, dass ein kleiner Satz überprüfbarer Testfälle mehr hilft als ein längerer Prompt. Welche Erfahrungen habt ihr mit der Bewertung von LLM-Ausgaben gemacht?'),
            ('demo-security', 'Beispielperson · Jonas', 'Cybersecurity', 5, 'Nach einer internen Phishing-Übung diskutieren wir gerade, wie IT-Sicherheit im Alltag besser verstanden wird. Meine Beobachtung: Der Meldeweg ist oft unklar. Wie gestaltet ihr Übungen, ohne Mitarbeitende bloßzustellen?'),
            ('demo-cloud', 'Beispielperson · Mira', 'Cloud & DevOps', 9, 'Beim Kubernetes-Deployment hat uns nicht der Rollout, sondern die Wiederherstellung beschäftigt. Unsere Herausforderung war die Abstimmung zwischen Anwendung und Infrastruktur. Welche Erfahrungen habt ihr mit regelmäßigen Recovery-Übungen unter Linux?'),
            ('demo-teams', 'Beispielperson · Ben', 'Microsoft 365', 12, 'Wir nutzen Microsoft 365 und Teams für die Zusammenarbeit. Das Problem liegt für uns weniger im Produkt als in uneinheitlichen Ablagen und Zuständigkeiten. Welche Regeln haben euch geholfen, ohne den Alltag unnötig kompliziert zu machen?'),
        ]
        return [dict(id=id, author=name, author_type='person', text=text, published_at=(now-timedelta(hours=age)).isoformat(), url='', profile_url='', source='demo') for id,name,topic,age,text in samples]


# Search discovers URLs only. No code fetches LinkedIn pages.
import os
import uuid
from urllib.parse import urlencode
from .config import settings
from .links import canonical_url
from .transport import request_json, ProviderError

SEARCH_TERMS = {
    'KI': '"künstliche Intelligenz" OR "generative KI" OR LLM',
    'Cybersecurity': 'Cybersecurity OR "IT-Sicherheit" OR Phishing',
    'Softwareentwicklung': 'Softwareentwicklung OR Softwarearchitektur OR Testing',
    'Cloud & DevOps': 'Cloud OR DevOps OR Kubernetes',
    'Linux & Open Source': 'Linux OR "Open Source"',
    'Microsoft 365': '"Microsoft 365" OR SharePoint OR Teams',
    'Weiterbildung': '"IT-Weiterbildung" OR "digitale Transformation" OR IT-Kompetenzen',
}


class SearchProvider(Protocol):
    def search(self, topic: str) -> list[dict]: ...


class BraveSearchProvider:
    def search(self, topic):
        config = settings()
        key = os.environ.get('BRAVE_SEARCH_API_KEY')
        if not key:
            raise ProviderError('BRAVE_SEARCH_API_KEY fehlt. Manuelle Recherche und Import bleiben verfügbar.', 503)
        if not config['search_authorized']:
            raise ProviderError('Suchanbieter-Nutzung nicht freigegeben. Vertrag einschließlich Speicherung prüfen; SEARCH_USE_AUTHORIZED=true setzen.', 403)
        if topic not in SEARCH_TERMS:
            raise ValueError('Unbekanntes Suchthema.')
        # No freshness claim: index dates are not original publication dates.
        query = 'site:linkedin.com/posts/ (' + SEARCH_TERMS[topic] + ')'
        url = 'https://api.search.brave.com/res/v1/web/search?' + urlencode({'q': query, 'count': config['max_results'], 'search_lang': 'de'})
        response = request_json(url, {'X-Subscription-Token': key}, timeout=config['timeout'])
        web = response.get('web', {})
        if not isinstance(web, dict) or not isinstance(web.get('results', []), list):
            raise ProviderError('Ungültige Suchantwort.')
        candidates, seen = [], set()
        for item in web.get('results', [])[:config['max_results']]:
            if not isinstance(item, dict):
                continue
            try:
                source_url = item.get('url', '')
                url = canonical_url(source_url)
            except (ValueError, TypeError):
                continue
            if url in seen:
                continue
            title, snippet = item.get('title', ''), item.get('description', '')
            if not isinstance(title, str) or not isinstance(snippet, str):
                continue
            seen.add(url)
            candidates.append({'id': str(uuid.uuid4()), 'url': url, 'source_url': source_url,
                'title': title[:300], 'snippet': snippet[:1500], 'source': 'brave', 'topic': topic,
                'discovered_at': datetime.now(timezone.utc).isoformat(),
                'published_at': None, 'author_type': 'unknown', 'status': 'candidate'})
        return candidates


def search_provider():
    if settings()['search_provider'] != 'brave':
        raise ProviderError('Keine unterstützte Suchquelle eingerichtet. SEARCH_PROVIDER=brave konfigurieren oder manuell recherchieren.', 503)
    return BraveSearchProvider()
