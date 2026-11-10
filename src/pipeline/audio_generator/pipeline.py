"""Pipeline builder for TTS vibe/instructions generation."""
from textwrap import dedent

from langchain_core.messages import SystemMessage
from langchain_core.prompts import PromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

from src.logic.writers.audio import SYSTEM_PROMPT


def create_tts_vibe_pipeline(model):
    """Build pipeline to generate TTS narration vibe description."""
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    human_prompt = PromptTemplate(template=dedent("""
        <COURSE_REQUIREMENT>: {course_requirement}
        <PERSONA>: {student_persona}
    """))
    human_message = HumanMessagePromptTemplate(prompt=human_prompt)
    chat_prompt = ChatPromptTemplate.from_messages([system_message, human_message])
    pipeline = chat_prompt | model | StrOutputParser()
    return pipeline
