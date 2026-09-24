"""A fixed public-fact task; arbitrary chat content cannot enter this cache path."""
import time

PROMPTS = ('In one short sentence, what is the capital of France?',
           'Name the capital city of France in one short sentence.')


def run(app, provider, model, variant=0, cache_factory=None, enabled=False):
    from app.core import Problem, provider_options
    from redisvl.extensions.cache.llm import LangCacheSemanticCache
    option = next((o for o in provider_options(app.store.c) if o['id'] == provider), None)
    if not app.provider and (not option or not option['available'] or model not in option['models']):
        raise Problem('model_unavailable', 'Choose a configured provider and model.', 422)
    if variant not in (0, 1):
        raise Problem('invalid_example', 'Choose an approved example.', 422)
    if not enabled:
        answer = app.private_answer([dict(role='USER', text=PROMPTS[variant])], provider, model)
        return dict(status='bypassed', text=answer['text'], cache_ms=0,
                    generation_ms=answer['generation_ms'], provider=provider, model=model)
    c = app.store.c
    if not all(c.get(k) for k in ('LANGCACHE_BASE_URL','LANGCACHE_CACHE_ID','LANGCACHE_API_KEY')):
        return {'status': 'not_configured', 'text': 'Configure LangCache to run this fixed public-fact example.'}
    attributes = dict(task='france-capital', prompt_version='1', provider=provider,
                      model=model, settings='answer-v1-max700')
    started = time.monotonic()
    try:
        cache = (cache_factory or LangCacheSemanticCache)(server_url=c['LANGCACHE_BASE_URL'],
            cache_id=c['LANGCACHE_CACHE_ID'], api_key=c['LANGCACHE_API_KEY'], ttl=3600)
        hits = cache.check(prompt=PROMPTS[variant], attributes=attributes, distance_threshold=0.05)
        # Check returned metadata too; do not trust a misconfigured service filter.
        hit = next((h for h in hits if h.get('metadata') == attributes and h.get('response')), None)
        cache_ms = round((time.monotonic()-started)*1000)
        if hit:
            return dict(status='hit', text=hit['response'], cache_ms=cache_ms,
                        generation_ms=0, provider=provider, model=model, attributes=attributes)
        answer = app.private_answer([dict(role='USER', text=PROMPTS[variant])], provider, model)
        cache.store(prompt=PROMPTS[variant], response=answer['text'], metadata=attributes, ttl=3600)
        return dict(status='miss', text=answer['text'], cache_ms=cache_ms,
                    generation_ms=answer['generation_ms'], provider=provider, model=model,
                    attributes=attributes)
    except Exception:
        raise Problem('cache_example_failed', 'The LangCache example failed. Check service configuration and retry.', 502)
