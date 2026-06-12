"""Subject classification for determining the academic domain.

Classifies course requirements into physics, biology, mathematics,
or computer_science to select the appropriate system prompts.
"""

import os
from typing import Literal
from textwrap import dedent

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.prompts import PromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from model_orchestration import get_model_config

class Subject(BaseModel):
 name: Literal["physics", "biology", "mathematics", "computer_science"] = Field(..., description="Subject name")
def classification(course_requirement: str, env: Literal['Dev', 'PROD']) -> str:

    output_parser = PydanticOutputParser(pydantic_object=Subject)
    format_instructions = output_parser.get_format_instructions()

    system_message = SystemMessage(content="You are a helpful AI assistant. Identify the subject according to <COURSE_REQUIREMENT>")
    human_prompt = PromptTemplate(template=dedent("""
    <COURSE_REQUIREMENT>: {course_requirement}
   
    format_instructions: {format_instructions}
    """),
    input_variables=["course_requirement", "student_persona"],
    partial_variables={'format_instructions': format_instructions}
    )
    human_message = HumanMessagePromptTemplate(prompt=human_prompt)

    chat_prompt = ChatPromptTemplate.from_messages([system_message,
    human_message
    ])

    model = get_model_config(env)['sub']

    pipeline = chat_prompt | model | output_parser

    return pipeline.invoke({"course_requirement": course_requirement}).name