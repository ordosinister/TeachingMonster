"""Central model configuration for DEV and PROD environments.

Provides get_model_config(env) factory that returns LLM model instances.
Instances are cached per event loop to avoid httpx event-loop reuse errors
when asyncio.run() is called multiple times in the same thread.
"""

import asyncio
import os
import threading

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from llama_index.llms.openai import OpenAI

from initialization import credential_init
from src.ollama_connection import llama_index_ollama

credential_init()

_event_loop_cache: dict[tuple, dict] = {}
_cache_lock = threading.Lock()


def get_model_config(env: str) -> dict:
    """Return a dict of LLM model instances for the given environment.

    Caches instances per asyncio event loop so that repeated calls within
    the same asyncio.run() reuse the same objects, while a new asyncio.run()
    (or a call from a sync context) gets fresh instances with clean httpx
    connection pools.
    """
    try:
        loop_key = id(asyncio.get_running_loop())
    except RuntimeError:
        # No running event loop (sync code path)
        loop_key = None

    cache_key = (env, loop_key)

    with _cache_lock:
        if cache_key in _event_loop_cache:
            return _event_loop_cache[cache_key]

        config = _build_config(env)
        _event_loop_cache[cache_key] = config
        return config


def _build_config(env: str) -> dict:
    """Build a fresh model configuration dict."""
    return {
    "DEV":
        {'main': ChatOllama(model='deepseek-v3.1:671b-cloud',
                               base_url='https://ollama.com',
                               name='main', temperature=0),
         'context': llama_index_ollama(model='deepseek-v3.1:671b-cloud', temperature=0, request_timeout=240),
         'sub': ChatOllama(model='gpt-oss:120b-cloud',
                           base_url='https://ollama.com',
                           name='sub', temperature=0),
         'master': ChatOllama(model='deepseek-v3.1:671b-cloud',
                           base_url='https://ollama.com',
                           name='master', temperature=0, reasoning=True),
         'image_caption': ChatOllama(model='qwen3.5:397b-cloud',
                           base_url='https://ollama.com',
                           name='image_caption', temperature=0, reasoning=True),
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
