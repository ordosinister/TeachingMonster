from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate, SystemMessagePromptTemplate
from langchain_core.runnables import Runnable

from src.sop.audio import SYSTEM_PROMPT
import logging

from src.sop.audio.structured_output import TTSScripts

logger = logging.getLogger(__name__)


def create_pipeline(model) -> Runnable:

    output_parser = PydanticOutputParser(pydantic_object=TTSScripts)
    format_instructions = output_parser.get_format_instructions()

    system_prompt = PromptTemplate(
        template=SYSTEM_PROMPT,
        input_variables=[],
        partial_variables={'format_instructions': format_instructions}
    )

    system_message = SystemMessagePromptTemplate(prompt=system_prompt)

    chat_prompt_template = ChatPromptTemplate.from_messages(
        [system_message,
         ("human", "<PERSONA>: {persona}"),
         MessagesPlaceholder(variable_name="messages")])

    pipeline = chat_prompt_template | model | output_parser
    logger.info("TTS pipeline created")

    return pipeline