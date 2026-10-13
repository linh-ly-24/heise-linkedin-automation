import unittest
from datetime import datetime, timedelta, timezone
from app.domain import assess, comments
from app.server import validate_post

NOW = datetime.now(timezone.utc)
TEXT = 'Beim Software-Testing habe ich gelernt, dass die Architektur unsere Fehleranalyse erschwert. Eine Herausforderung ist die Abstimmung zwischen Teams. Welche Erfahrungen habt ihr damit gemacht und wie prüft ihr die Entscheidungen?'
def post(**kw):
    p=dict(id='test',author='Test',author_type='person',source='manual',published_at=(NOW-timedelta(hours=1)).isoformat(),text=TEXT,url='https://www.linkedin.com/posts/test',profile_url='')
    p.update(kw)
    return p

class SelectionTests(unittest.TestCase):
    def test_time_boundary(self):
        for age,expected in [(0,True),(24,True),(24.001,False),(-1,False)]:
            with self.subTest(age=age):
                self.assertEqual(assess(post(published_at=(NOW-timedelta(hours=age)).isoformat()),NOW)['eligible'],expected)
    def test_timezone(self):
        same=(NOW-timedelta(hours=1)).astimezone(timezone(timedelta(hours=2)))
        self.assertTrue(assess(post(published_at=same.isoformat()),NOW)['eligible'])
        self.assertFalse(assess(post(published_at='2026-01-01T12:00:00'),NOW)['eligible'])
    def test_author_type(self):
        for kind in ['company','unknown','',None]:
            self.assertFalse(assess(post(author_type=kind),NOW)['eligible'])
        self.assertTrue(assess(post(),NOW)['eligible'])
    def test_advertising(self):
        for text in ['Jetzt buchen: unser Kurs für Softwareentwicklung', 'KI mit 20% Rabatt', 'Jetzt kaufen: Security-Lösung']:
            self.assertFalse(assess(post(text=text),NOW)['eligible'])
    def test_discussing_ads_or_learning_is_not_a_pitch(self):
        for text in ['Ich kritisiere Werbeversprechen wie jetzt kaufen bei KI-Produkten. '+TEXT,
                     'Unser Kurs zu Software-Architektur hat Fragen offen gelassen. '+TEXT,
                     'Wir wollen keine Rabattcodes für KI-Produkte. '+TEXT]:
            self.assertTrue(assess(post(text=text),NOW)['eligible'])
    def test_product_mention_is_not_advertising(self):
        self.assertTrue(assess(post(text='Wir nutzen Microsoft 365 und Teams. '+TEXT),NOW)['eligible'])
    def test_irrelevant_and_score(self):
        self.assertFalse(assess(post(text='Wie schmeckt euer Frühstück?'),NOW)['eligible'])
        a=assess(post(),NOW)
        self.assertGreaterEqual(a['score'],0)
        self.assertLessEqual(a['score'],100)
        self.assertEqual(a['score'],sum(a['components'].values()))
    def test_exact_three_different_comments(self):
        options=comments(post())
        self.assertEqual([o['key'] for o in options],['A','B','C'])
        self.assertEqual(len({o['text'] for o in options}),3)
        for option in options:
            self.assertIn('Software-Testing',option['text'])
            self.assertNotIn('Toller Beitrag',option['text'])
        self.assertNotEqual(options,comments(post(),1))
    def test_insufficient_or_excluded_has_no_comments(self):
        self.assertEqual(comments(post(text='KI?')),[])
        self.assertEqual(comments(post(author_type='company')),[])
        self.assertEqual(comments(post(published_at=(NOW-timedelta(days=2)).isoformat())),[])
    def test_import_validation(self):
        self.assertEqual(validate_post(post())['source'],'manual')
        for url in ['http://linkedin.com/posts/a','https://linkedin.com.evil.test/posts/a','javascript:alert(1)','https://www.linkedin.com/company/a','https://user:pass@linkedin.com/posts/a']:
            with self.assertRaises(ValueError):validate_post(post(url=url))
        with self.assertRaises(ValueError):validate_post(post(profile_url='https://linkedin.com/company/test'))

if __name__ == '__main__':unittest.main()
