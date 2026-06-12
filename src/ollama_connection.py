from llama_index.llms.ollama import Ollama

from initialization import credential_init

def llama_index_ollama(model: str, temperature: float, request_timeout=60):

    """Create a llama_index Ollama LLM instance.

    Args:
        model: Ollama model name (e.g., 'deepseek-v3.1:671b-cloud').
        temperature: Sampling temperature for generation.
        request_timeout: Timeout in seconds for each request.

    Returns:
        Configured llama_index Ollama LLM instance.
    """
    """
    llm = llama_index_ollama(model='gpt_oss:120b-cloud')
    """
    credential_init()

    base_url = "https://ollama.com"

    llm = Ollama(model=model, request_timeout=request_timeout, 
                 base_url=base_url, temperature=temperature)

    return llm