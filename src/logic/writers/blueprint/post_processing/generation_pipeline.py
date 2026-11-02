import logging
from textwrap import dedent

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser

from model_orchestration import get_model_config
from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.post_processing import CONSISTENCY_SYSTEM_PROMPT, CONSISTENCY_MERGE_PROMPT
from src.logic.writers.blueprint.structured_output import LessonBlueprint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blueprint.post_processing.generation_pipeline")


def create_audit_pipeline(env: str):

    logger.info("Create audit pipeline for consistency check...")

    input_ = {
        "system": {"template": CONSISTENCY_SYSTEM_PROMPT},
        "human": {
            "template": dedent("""\
                    <SLIDES>:
                    {slides}

                    <COURSE_REQUIREMENT>:
                    {course_requirement}

                    <STUDENT_PERSONA>:
                    {persona}

                    <BACKGROUND_ADAPTATIONS>:
                    {adaptations}
                """),
        }
    }

    pipeline = (
            build_standard_chat_prompt_template(input_)
            | get_model_config(env)['master']
            | StrOutputParser()
    )

    return pipeline


def create_merge_pipeline(env: str):

    logger.info("Create merge pipeline for consistency check...")

    output_parser = PydanticOutputParser(pydantic_object=LessonBlueprint)
    format_instructions = output_parser.get_format_instructions()

    input_ = {
        "system": {"template": CONSISTENCY_MERGE_PROMPT,
                   "partial_variables": {'format_instructions': format_instructions}},
        "human": {
            "template": dedent("""\
                    Fix all consistency issues in 

                    <DRAFT>: {draft} 

                    with

                    <CONSISTENCY_AUDIT>: {audit}

                    <COURSE_REQUIREMENT>: {course_requirement}

                    <STUDENT_PERSONA>: {persona}
                """)
        }
    }

    model = get_model_config(env)['sub']
    pipeline = build_standard_chat_prompt_template(input_) | model | output_parser

    return pipeline