"""Pipeline builder for slide content generation."""
from textwrap import dedent

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable

from src.logic import build_standard_chat_prompt_template
from poc.slide_content.models import LessonBlueprint
from poc.slide_content.prompts import SYSTEM_PROMPT


def create_slide_content_pipeline(model) -> Runnable:
    """Build the slide-content generation pipeline."""
    output_parser = PydanticOutputParser(pydantic_object=LessonBlueprint)
    format_instructions = output_parser.get_format_instructions()

    input_ = {
        "system": {
            "template": SYSTEM_PROMPT,
            "partial_variables": {"format_instructions": format_instructions},
        },
        "human": {
            "template": dedent("""
                <INPUT>: {input}
            """),
        },
    }

    pipeline = build_standard_chat_prompt_template(input_) | model | output_parser
    return pipeline