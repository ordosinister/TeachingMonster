"""Pipeline builders for lesson blueprint generation.

Each pipeline chains a system prompt, human input template, LLM model,
and Pydantic output parser into a LangChain Runnable.
"""
from textwrap import dedent

from langchain_core.messages import SystemMessage
from langchain_core.prompts import PromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate, \
    SystemMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable

from src.logic.writers.blueprint.structured_output import LessonBlueprint, StudentProfileInterpretation
from src.logic.writers.blueprint.system_prompt_warehouse.background import SYSTEM_PROMPT as BACKGROUND_SYSTEM_PROMPT


def create_presentation_pipeline(model) -> Runnable:

    from src.logic.writers.blueprint.system_prompt_warehouse.presentation import SYSTEM_PROMPT

    system_prompt = SYSTEM_PROMPT

    output_parser = PydanticOutputParser(pydantic_object=LessonBlueprint)
    format_instructions = output_parser.get_format_instructions()

    system_message = SystemMessage(content=system_prompt)
    human_prompt = PromptTemplate(template=dedent("""
    <COURSE_REQUIREMENT>: {course_requirement}
    <STUDENT_PERSONA>: {student_persona}
    <PEDAGOGICAL_STATE>: {pedagogical_state}
    
    Output format instructions: {format_instructions}
    """),
    input_variables=["course_requirement", "student_persona"],
    partial_variables={'format_instructions': format_instructions}
    )
    human_message = HumanMessagePromptTemplate(prompt=human_prompt)

    chat_prompt = ChatPromptTemplate.from_messages([system_message,
    human_message
    ])

    pipeline = chat_prompt | model | output_parser

    return pipeline


def create_slide_pipeline(model, pydantic_object) -> Runnable:
    """Multi-stage decompression: EXPAND -> SELF-AUDIT -> REFINE."""

    from src.logic.writers.blueprint.decompress_prompt import SYSTEM_PROMPT as DECOMPRESS_SYSTEM_PROMPT
    decompress_prompt = DECOMPRESS_SYSTEM_PROMPT

    output_parser = PydanticOutputParser(pydantic_object=pydantic_object)
    format_instructions = output_parser.get_format_instructions()

    system_message = SystemMessage(content=decompress_prompt)
    human_prompt = PromptTemplate(template=dedent("""
        <DRAFT>:
        {draft}

        <COURSE_REQUIREMENT>: {course_requirement}
        <STUDENT_PERSONA>: {student_persona}
        <PEDAGOGICAL_STATE>: {pedagogical_state}

        Output format instructions: {format_instructions}
        """),
                                  input_variables=["draft", "course_requirement", "student_persona", "pedagogical_state"],
                                  partial_variables={'format_instructions': format_instructions}
                                  )
    human_message = HumanMessagePromptTemplate(prompt=human_prompt)

    chat_prompt = ChatPromptTemplate.from_messages([system_message,
                                                    human_message
                                                    ])

    pipeline = chat_prompt | model | output_parser

    return pipeline

def create_background_pipeline(model) -> Runnable:
    """Build the background pipeline with a fixed, subject-agnostic SYSTEM_PROMPT.

    The prompt is designed to diagnose gaps between <STUDENT_PERSONA> and
    <COURSE_REQUIREMENT> across publishers / regions, without assuming a
    specific STEM discipline.
    """

    output_parser = PydanticOutputParser(pydantic_object=StudentProfileInterpretation)
    format_instructions = output_parser.get_format_instructions()

    system_prompt = PromptTemplate(template=BACKGROUND_SYSTEM_PROMPT,
                                   partial_variables={'format_instructions': format_instructions})

    system_message = SystemMessagePromptTemplate(prompt=system_prompt)

    human_prompt = PromptTemplate(template=dedent("""
    <COURSE_REQUIREMENT>: {course_requirement}
    <STUDENT_PERSONA>: {student_persona}
    """),
    input_variables=["course_requirement", "student_persona"],

    )
    human_message = HumanMessagePromptTemplate(prompt=human_prompt)

    chat_prompt = ChatPromptTemplate.from_messages([
        system_message,
        human_message
    ])

    pipeline = chat_prompt | model | output_parser

    return pipeline