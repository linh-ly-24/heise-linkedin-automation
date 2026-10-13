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
