from langchain_core.prompts.image import ImagePromptTemplate
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, PromptTemplate


def build_standard_chat_prompt_template(kwargs):
    """Build a ChatPromptTemplate from system and human message configs.

    Supports both text-only and multimodal (text + image) prompts.

    Args:
        kwargs: Dictionary with optional 'system' and 'human' keys.
            Each value is a dict with 'template' (required) and optional
            'type' ('text' or 'image') and 'input_variables'.

    Returns:
        A configured ChatPromptTemplate ready for use with an LLM.
    """
    messages = []

    if 'system' in kwargs:
        content = kwargs.get('system')

        # allow list of prompts for multimodal
        if isinstance(content, list):
            prompts = [PromptTemplate(**c) for c in content]
        else:
            prompts = [PromptTemplate(**content)]

        message = SystemMessagePromptTemplate(prompt=prompts)
        messages.append(message)

    if 'human' in kwargs:
        content = kwargs.get('human')

        # allow list of prompts for multimodal
        if isinstance(content, list):
            prompts = []
            for c in content:
                if c.get("type") == "image":
                    prompts.append(ImagePromptTemplate(**c))
                else:
                    prompts.append(PromptTemplate(**c))
        else:
            if content.get("type") == "image":
                prompts = [ImagePromptTemplate(**content)]
            else:
                prompts = [PromptTemplate(**content)]

        message = HumanMessagePromptTemplate(prompt=prompts)
        messages.append(message)

    chat_prompt_template = ChatPromptTemplate.from_messages(messages)

    return chat_prompt_template
