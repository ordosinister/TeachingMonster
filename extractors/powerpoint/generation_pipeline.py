from textwrap import dedent
from typing import Literal

from langchain_core.output_parsers import StrOutputParser

from extractors.powerpoint import SYSTEM_PROMPT
from model_orchestration import get_model_config
from src.logic import build_standard_chat_prompt_template


def create_pipeline(env: Literal["DEV", "PROD"]):

    MODEL_NAME = "image_caption"

    model = get_model_config(env)[MODEL_NAME]

    input_ = {
        "system": {"template": SYSTEM_PROMPT},
        "human": {"template": dedent("""
                                        <COURSE_REQUIREMENT>: {course_requirement}
                                        <STUDENT_PERSONA>: {student_persona}
                                        """),
                  }
    }

    pipeline = build_standard_chat_prompt_template(input_) | model | StrOutputParser()

    return pipeline