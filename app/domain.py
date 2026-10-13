"""Deterministic, inspectable selection rules; no external network operations."""
import re
from datetime import datetime, timezone

TOPICS = {
    'KI': ['ki', 'ai', 'llm', 'generative', 'künstliche intelligenz', 'prompt'],
    'Cybersecurity': ['security', 'sicherheit', 'phishing', 'cyber', 'passkey'],
    'Softwareentwicklung': ['software', 'code', 'architektur', 'python', 'entwicklung', 'testing'],
    'Cloud & DevOps': ['cloud', 'devops', 'linux', 'kubernetes', 'deployment'],
    'Linux & Open Source': ['linux', 'open source', 'opensource'],
    'Microsoft 365': ['microsoft 365', 'teams', 'sharepoint', 'zusammenarbeit'],
    'Weiterbildung': ['weiterbildung', 'lernen', 'kompetenzen', 'transformation', 'lernen'],
}

def parse_time(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Veröffentlichungszeit braucht eine Zeitzone.')
    return dt.astimezone(timezone.utc)


def matches(text, word):
    return bool(re.search(r'(?<!\w)' + re.escape(word) + r'(?!\w)', text, re.I))


def advertising_signals(text):
    """Only direct selling language; quotations/critique deserve review, not exclusion."""
    patterns = [r'jetzt\s+(kaufen|buchen|anmelden|sichern)',
                r'\b\d+\s*%\s*(sparen|rabatt)',
                r'\b(rabattcode|promocode|sonderangebot|discount)\b',
                r'(mein|unser)\w*\s+(kurs|produkt|angebot|dienstleistung)\w*']
    hits = []
    for pattern in patterns:
        for hit in re.finditer(pattern, text.lower()):
            context = text.lower()[max(0, hit.start()-90):min(len(text),hit.end()+90)]
            # A discussion about promotional language is not itself a sales pitch.
            if re.search(r'\b(kein\w*|nicht|kritisi\w*|werbeversprechen|werbesprache)\b', context):
                continue
            if pattern.startswith('(mein|unser)') and not re.search(r'\b(buchen|kaufen|anmelden|sichern|bestellen|angebot|preis|plätze|plaetze)\b', context):
                continue
            hits.append(hit.group())
    return hits


def assess(post, now=None):
    now = now or datetime.now(timezone.utc)
    text = post['text'].strip()
    lower = text.lower()
    warnings, reasons = [], []
    try:
        age = (now - parse_time(post.get('published_at') or '')).total_seconds() / 3600
        if age < 0:
            reasons.append('Veröffentlichungszeit liegt in der Zukunft.')
        elif age > 24:
            reasons.append('Älter als 24 Stunden.')
    except (ValueError, TypeError):
        age = 1000
        reasons.append('Veröffentlichungszeit fehlt oder ist ungültig.')
    if post.get('verified') is False and post.get('source') != 'demo':
        reasons.append('Originaltext, Autorenart und Veröffentlichungszeit müssen menschlich verifiziert werden.')
    if post.get('author_type') != 'person':
        reasons.append('Kein bestätigtes persönliches Profil.')
    # Mentioning a brand alone is deliberately not an advertising signal.
    sales = advertising_signals(lower)
    advertising = bool(sales)
    if advertising:
        reasons.append('Deutliche Verkaufssignale erkannt; menschliche Prüfung möglich.')
    topics = [topic for topic, terms in TOPICS.items() if any(matches(lower, t) for t in terms)]
    if not topics:
        reasons.append('Kein passender Themenbezug erkannt.')
    enough = len(text.split()) >= 18 and len(text) >= 110
    if not advertising and any(w in lower for w in ['kurs', 'produkt', 'dienstleistung', 'rabatt']):
        warnings.append('Produkt- oder Angebotsbezug: Absicht im Kontext prüfen; kein automatischer Ausschluss.')
    if not enough:
        warnings.append('Zu wenig Inhalt für fundierte Kommentare.')
    discussion = min(20, (6 if '?' in text else 0) + sum(4 for w in ['erfahrung', 'gelernt', 'herausforderung', 'problem', 'diskussion', 'beobachtung'] if w in lower))
    quality = min(15, len(text.split()) // 8 + (3 if enough else 0))
    components = {'relevance': 40 if topics else 0, 'recency': round(max(0, 25 * (1 - max(0, age) / 24))), 'discussion': discussion, 'quality': quality}
    warnings.append('Regelbasierte Einschätzung; Inhalt und Angaben vor Verwendung prüfen.')
    if post.get('source') == 'manual' and not post.get('verified'):
        warnings.append('Autor und Veröffentlichungszeit sind manuelle Angaben, nicht durch LinkedIn verifiziert.')
    return {'eligible': not reasons, 'reasons': reasons, 'warnings': warnings, 'topics': topics,
            'score': sum(components.values()), 'components': components, 'enough_context': enough,
            'relevance_reason': 'Bezug zu ' + ', '.join(topics) if topics else 'Keine thematischen Schlüsselbegriffe gefunden.'}


PERSPECTIVES = {
 'KI': ('Ausgaben anhand konkreter Testfälle zu prüfen, macht Grenzen eines KI-Workflows besser sichtbar.', 'Welche Kriterien nutzt du, um brauchbare Ergebnisse von plausibel klingenden Fehlern zu unterscheiden?', 'Für KI-Kompetenz ist neben dem Werkzeug auch die kritische Prüfung der Ergebnisse eine wichtige Lernaufgabe.'),
 'Cybersecurity': ('Neben technischen Maßnahmen lohnt es sich, die Abläufe für Meldung und Reaktion mitzudenken.', 'An welcher Stelle ist die Umsetzung im Alltag am schwierigsten?', 'Sicherheitskompetenz lässt sich gut an konkreten Alltagssituationen und gemeinsam besprochenen Entscheidungen üben.'),
 'Softwareentwicklung': ('Eine kleine, überprüfbare Änderung mit klaren Tests kann helfen, die fachlichen Abwägungen sichtbar zu machen.', 'Welche Abwägung hat eure Entscheidung am stärksten beeinflusst?', 'Für Entwicklungskompetenz ist es hilfreich, auch die Gründe hinter einer technischen Entscheidung gemeinsam zu reflektieren.'),
 'Cloud & DevOps': ('Neben dem Normalbetrieb lohnt es sich, Wiederherstellung und Fehlerfälle ausdrücklich durchzuspielen.', 'Welche Erkenntnis aus dem Betrieb würdest du beim nächsten Durchlauf früher berücksichtigen?', 'Praxisnahe Lernaufgaben zu Betrieb und Fehleranalyse können helfen, technische Zusammenhänge besser zu verstehen.'),
 'Linux & Open Source': ('Eine reproduzierbare Beschreibung der Umgebung kann helfen, Beobachtungen und Lösungsansätze gemeinsam zu prüfen.', 'Welche Randbedingungen waren für deinen Lösungsweg entscheidend?', 'Eine kleine praktische Aufgabe mit anschließender Reflexion kann den Transfer von Linux- und Open-Source-Wissen unterstützen.'),
 'Microsoft 365': ('Klare Absprachen über Ablage, Zuständigkeiten und Kommunikation können die Werkzeugwahl sinnvoll ergänzen.', 'Welche Vereinbarung hat die Zusammenarbeit bei euch konkret erleichtert?', 'Digitale Zusammenarbeit braucht neben Bedienwissen auch gemeinsam entwickelte Arbeitsroutinen.'),
 'Weiterbildung': ('Ein konkretes Anwendungsproblem und ein überprüfbares Lernziel können helfen, den nächsten Lernschritt zu bestimmen.', 'Woran würdest du erkennen, dass sich das Gelernte im Arbeitsalltag bewährt?', 'Für den Transfer von IT-Wissen lohnt es sich, Lernzeit und praktische Anwendung zusammen zu planen.'),
}


def comments(post, variant=0):
    assessment = assess(post)
    if not assessment['eligible'] or not assessment['enough_context']:
        return []
    topic = assessment['topics'][variant % len(assessment['topics'])]
    a, b, c = PERSPECTIVES[topic]
    # Quote actual source words to ground every draft without inventing experience.
    sentences = re.split(r'(?<=[.!?])\s+', post['text'])
    anchor = next((s for s in sentences if any(matches(s, term) for term in TOPICS[topic])), post['text'])
    words = anchor.split()
    excerpt = ' '.join(words[:min(12, len(words))]).strip('"„“') + (' …' if len(words) > 12 else '')
    if variant % 3 == 2:
        a = 'Ein hilfreicher Ausgangspunkt könnte eine gemeinsame Definition von Erfolg und Grenzen sein. ' + a
        b = 'Was wäre bei diesem Thema ein kleiner, überprüfbarer nächster Schritt?'
        c = 'Eine mögliche Lernaufgabe wäre, den beschriebenen Fall gemeinsam zu analysieren und Alternativen zu vergleichen.'
    elif variant % 3 == 1:
        a = 'Eine mögliche nächste Prüfung: ' + a[0].lower() + a[1:]
        b = 'Für die Diskussion wäre interessant: ' + b[0].lower() + b[1:]
        c = 'Aus Lernperspektive: ' + c[0].lower() + c[1:]
    return [
        {'key': 'A', 'label': 'Fachlicher Mehrwert', 'text': f'Zu „{excerpt}“: {a}'},
        {'key': 'B', 'label': 'Persönlich & dialogorientiert', 'text': f'Du sprichst „{excerpt}“ an. {b}'},
        {'key': 'C', 'label': 'Perspektive der heise academy', 'text': f'Dein Punkt „{excerpt}“ bietet einen Lernanlass. {c}'},
    ]
