"""Central model configuration for DEV and PROD environments.

Provides get_model_config(env) factory that returns LLM model instances.
Instances are cached per event loop to avoid httpx event-loop reuse errors
when asyncio.run() is called multiple times in the same thread.
"""

import asyncio
import os
import threading
import weakref

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from llama_index.llms.openai import OpenAI

from initialization import credential_init
from src.ollama_connection import llama_index_ollama

credential_init()

_event_loop_cache: dict[tuple, dict] = {}
_loop_refs: dict[int, "weakref.ReferenceType"] = {}
_cache_lock = threading.Lock()


def get_model_config(env: str) -> dict:
    """Return a dict of LLM model instances for the given environment.

    Caches instances per asyncio event loop so that repeated calls within
    the same asyncio.run() reuse the same objects, while a new asyncio.run()
    (or a call from a sync context) gets fresh instances with clean httpx
    connection pools.

    Uses weakref to verify loop identity, preventing stale cache hits when
    Python reuses id() values across destroyed and newly created loops.
    """
    try:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
    except RuntimeError:
        # No running event loop (sync code path)
        loop = None
        loop_id = None

    cache_key = (env, loop_id)

    with _cache_lock:
        if cache_key in _event_loop_cache:
            # Verify the cached loop is still the same object (id may be reused)
            if loop_id is None:
                return _event_loop_cache[cache_key]
            if loop_id in _loop_refs and _loop_refs[loop_id]() is loop:
                return _event_loop_cache[cache_key]
            # Stale entry: id was reused for a different loop
            del _event_loop_cache[cache_key]
            if loop_id in _loop_refs:
                del _loop_refs[loop_id]

        config = _build_config(env)
        _event_loop_cache[cache_key] = config
        if loop is not None:
            _loop_refs[loop_id] = weakref.ref(loop)
        return config


def _build_config(env: str) -> dict:
    """Build a fresh model configuration dict."""
    return {
    "DEV":
        {'main': ChatOllama(model='deepseek-v3.1:671b-cloud',
                               name='main', temperature=0),
         'context': llama_index_ollama(model='deepseek-v3.1:671b-cloud', temperature=0, request_timeout=240),
         'sub': ChatOllama(model='gpt-oss:120b-cloud',
                           name='sub', temperature=0),
         'master': ChatOllama(model='deepseek-v3.1:671b-cloud',
                           name='master', temperature=0, reasoning=True),
         'image_caption': ChatOllama(model='kimi-k2.6:cloud',
                           name='image_caption', temperature=0),
         'image_quality': 'medium'
         },
    "PROD":
        {'main':ChatOpenAI(model_name="gpt-5-mini",
                                openai_api_key=os.environ['OPENAI_API_KEY'],
                                temperature=0,
                                name='main'),
         'sub': ChatOllama(model='gpt-oss:120b-cloud',
                               base_url='https://ollama.com',
                               name='sub'),
         'context': llama_index_ollama(model='deepseek-v3.1:671b-cloud', temperature=0, request_timeout=240),

         'master':ChatOpenAI(model_name="gpt-5.4-nano-2026-03-17",
                             openai_api_key=os.environ['OPENAI_API_KEY'],
                             temperature=0,
                             name='master'),
         'image_caption': ChatOpenAI(model_name="gpt-4.1-mini-2025-04-14",
                             openai_api_key=os.environ['OPENAI_API_KEY'],
                             temperature=0,
                             name='image_caption'),
         'image_quality': 'medium'
         }

    }[env]


if __name__ == "__main__":
    cfg = get_model_config("DEV")
    print(cfg['main'].invoke("Hello"))
