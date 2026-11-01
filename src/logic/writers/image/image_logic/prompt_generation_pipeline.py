from textwrap import dedent

from langchain_core.output_parsers import PydanticOutputParser

from src.logic import build_standard_chat_prompt_template
from src.logic.writers.image.image_logic import SYSTEM_PROMPT
from src.logic.writers.image.image_logic.parser import Output


def create_image_prompt_pipeline(model):

    output_parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = output_parser.get_format_instructions()

    input_ = {"system": {"template": SYSTEM_PROMPT,
                         "partial_variables": {"format_instructions": format_instructions}},
              "human": {
                  "template": dedent("""
                  <Context>: {context}
                
                  <Slide Content>: {slide_content}
                  
                  <Speaker Note>: {speaker_notes}

                  <PERSONA>: {student_persona}
                  """),
                  }}

    chat_prompt_template = build_standard_chat_prompt_template(input_)

    pipeline = chat_prompt_template | model | output_parser

    return pipeline
