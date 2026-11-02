from textwrap import dedent

from langchain_core.output_parsers import PydanticOutputParser

from src.logic import build_standard_chat_prompt_template
from src.logic.writers.image.visual_style import SYSTEM_PROMPT
from src.logic.writers.image.visual_style.parser import VisualStyleOutput


def create_visual_style_pipeline(model):

    output_parser = PydanticOutputParser(pydantic_object=VisualStyleOutput)
    format_instructions = output_parser.get_format_instructions()

    input_ = {
        "system": {"template": SYSTEM_PROMPT,
                   "partial_variables": {"format_instructions": format_instructions}},
        "human": {
            "template": dedent("""
                                <COURSE REQUIREMENT>:
                                {course_requirement}
                                
                                <STUDENT PERSONA>:
                                {student_persona}
                                
                                <PRESENTATION CONTENT>:
                                {content}
                        """),
        }
    }

    chat_prompt_template = build_standard_chat_prompt_template(input_)

    pipeline = chat_prompt_template | model | output_parser

    return pipeline