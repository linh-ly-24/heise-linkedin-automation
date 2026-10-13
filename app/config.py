"""Server-only configuration. Never serialize keys or the process environment."""
import os


def flag(name):
    return os.environ.get(name, '').lower() in ('1', 'true', 'yes')


def integer(name, default, minimum=0, maximum=1000):
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        raise ValueError(f'{name} muss eine ganze Zahl sein.') from None
    if not minimum <= value <= maximum:
        raise ValueError(f'{name} muss zwischen {minimum} und {maximum} liegen.')
    return value


def settings():
    return {
        'model': os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'),
        'ai_key_present': bool(os.environ.get('OPENAI_API_KEY')),
        'ai_authorized': flag('OPENAI_PROCESSING_AUTHORIZED'),
        'search_provider': os.environ.get('SEARCH_PROVIDER', 'none'),
        'search_key_present': bool(os.environ.get('BRAVE_SEARCH_API_KEY')),
        'search_authorized': flag('SEARCH_USE_AUTHORIZED'),
        'timeout': integer('PROVIDER_TIMEOUT_SECONDS', 25, 1, 120),
        'max_ai_calls': integer('MAX_AI_CALLS_PER_DAY', 10),
        'max_search_calls': integer('MAX_SEARCH_CALLS_PER_DAY', 5),
        'max_results': integer('MAX_SEARCH_RESULTS', 10, 1, 20),
        'max_posts': integer('MAX_POSTS_PROCESSED_PER_DAY', 10),
        'retention_days': integer('DATA_RETENTION_DAYS', 30, 1, 365),
    }
