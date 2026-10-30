from typing import Literal

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate
)

from model_orchestration import get_model_config


def create_pipeline(env: Literal["DEV", "PROD"], system_prompt: str):

    MODEL_NAME = "image_caption"

    system_prompt = PromptTemplate(
        template=system_prompt,
        input_variables=[],
    )

    system_message = SystemMessagePromptTemplate(prompt=system_prompt)

    chat_prompt_template = ChatPromptTemplate.from_messages(
        [system_message,
         MessagesPlaceholder(variable_name="messages")])

    model = get_model_config(env)[MODEL_NAME]

    pipeline = chat_prompt_template | model | StrOutputParser()

    return pipeline