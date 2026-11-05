from typing import Literal

from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.output_parsers import StrOutputParser

from extractors.word import SYSTEM_PROMPT
from model_orchestration import get_model_config


def create_pipeline(env: Literal["DEV", "PROD"]):

    MODEL_NAME = "image_caption"

    model = get_model_config(env)[MODEL_NAME]

    system_prompt = PromptTemplate(
        template=SYSTEM_PROMPT,
        input_variables=[]
    )

    system_message = SystemMessagePromptTemplate(prompt=system_prompt)

    chat_prompt_template = ChatPromptTemplate.from_messages(
        [system_message, MessagesPlaceholder(variable_name="messages")])

    pipeline = chat_prompt_template | model | StrOutputParser()

    return pipeline