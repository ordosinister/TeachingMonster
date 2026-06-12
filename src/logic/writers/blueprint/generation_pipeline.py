"""Pipeline builders for lesson blueprint generation.

Each pipeline chains a system prompt, human input template, LLM model,
and Pydantic output parser into a LangChain Runnable.
"""

import importlib
from textwrap import dedent
from typing import Literal

from langchain_core.messages import SystemMessage
from langchain_core.prompts import PromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough

from src.logic.writers.blueprint.structured_output import LessonBlueprint, StudentProfileInterpretation, AdaptabilityOutput
from src.logic.writers.blueprint import background_system_prompt

"""Pipeline builders for lesson blueprint generation.

Each pipeline chains a system prompt, human input template, LLM model,
and Pydantic output parser into a LangChain Runnable.
"""

def _build_decompress_prompt(subject: str) -> str:
    module_path = f"src.logic.writers.blueprint.decompress_prompt.{subject}"
    module = importlib.import_module(module_path)
    return module.SYSTEM_PROMPT


def create_presentation_pipeline(model, subject: Literal["physics", "biology", "mathematics", "computer_science"]) -> Runnable:

    module_path = f"src.logic.writers.blueprint.system_prompt.{subject}"
    module = importlib.import_module(module_path)

    system_prompt = module.SYSTEM_PROMPT

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


def create_slide_pipeline(model, subject, pydantic_object) -> Runnable:
    """Multi-stage decompression: EXPAND -> SELF-AUDIT -> REFINE."""

    decompress_prompt = _build_decompress_prompt(subject)

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

def create_background_pipeline(model, subject: Literal["physics", "biology", "mathematics", "computer_science"]) -> Runnable:

    module_path = f"src.logic.writers.blueprint.background_system_prompt.{subject}"
    module = importlib.import_module(module_path)

    system_prompt = module.SYSTEM_PROMPT

    output_parser = PydanticOutputParser(pydantic_object=StudentProfileInterpretation)
    format_instructions = output_parser.get_format_instructions()

    system_message = SystemMessage(content=system_prompt)
    human_prompt = PromptTemplate(template=dedent("""
    <COURSE_REQUIREMENT>: {course_requirement}
    <STUDENT_PERSONA>: {student_persona}

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

def create_adaptability_pipeline(model, pydantic_object) -> Runnable:
    ADAPTABILITY_SYSTEM_PROMPT = dedent("""
# ROLE
AP Lecturer with deep STEM expertise and many years of AP classroom experience. Expert at diagnosing learning friction and adapting lesson content so every student, regardless of background, can master new concepts at their level. You know how to bridge the gap between what a student knows and what <COURSE REQUIREMENT> demands.

# INPUTS
- <DRAFT>: current lesson
- <COURSE REQUIREMENT>: learning goals
- <STUDENT PERSONA>: grade, focus time, background knowledge
- <STUDENT CONFUSIONS>: primary friction signal -- per-slide issues flagged by the student (pace, scaffolding, jargon, gaps, depth, completeness)

# TASK
For each confusion, diagnose the root cause and fix the underlying gap in the lesson. Write a direct, persona-calibrated answer to each of the student's questions.

# RULES
- Diagnose root cause: jargon | prerequisite | pacing | assumption | background_gap.
- Fix in script: bridge content, expand thin sections, reorder for dependency, split overloaded slides.
- Answer style: use student vocabulary, validate the question, explain clearly, connect to <COURSE REQUIREMENT>. Never dismiss or talk down.
- Persona alignment: match language, abstraction, and examples to <STUDENT PERSONA>. Scaffold above-level concepts with analogies or smaller steps.
- Course fidelity: only add or reorder. Never remove key concepts.
- Rhythm: match pace to focus time and grade processing speed.
- Proactive scaffolding: anticipate confusion beyond the minimum. Add layered explanations where students at this level typically stumble.

# CHAIN OF THOUGHT
1. Parse <STUDENT CONFUSIONS>: what is the student feeling, and what are they asking for?
2. Diagnose each issue: jargon, missing prerequisite, pacing, unstated assumption, or background gap?
3. Plan fixes: explain terms, insert prerequisite slides, split dense sections, add analogies.
4. Write a direct answer to each question at <STUDENT PERSONA> level.
5. Apply fixes to the lesson script.
6. Verify: all confusions resolved, gaps bridged, pacing set, persona-appropriate, course-complete.

# OUTPUT
JSON with advise (per-issue diagnosis and answer) and updated_script (adapted lesson).
""")

    output_parser = PydanticOutputParser(pydantic_object=pydantic_object)
    format_instructions = output_parser.get_format_instructions()

    system_message = SystemMessage(content=ADAPTABILITY_SYSTEM_PROMPT)

    human_prompt = PromptTemplate(template=dedent("""
    <DRAFT>:
    {draft}

    <COURSE REQUIREMENT>:
    {course_requirement}

    <STUDENT PERSONA>:
    {student_persona}

    <STUDENT_CONFUSIONS>:
    {student_confusions}

    Output format instructions: {format_instructions}
    """),
    input_variables=["draft", "course_requirement", "student_persona", "student_confusions"],
    partial_variables={'format_instructions': format_instructions}
    )

    human_message = HumanMessagePromptTemplate(prompt=human_prompt)

    chat_prompt = ChatPromptTemplate.from_messages([system_message,
    human_message,
    ])

    pipeline = chat_prompt | model | output_parser

    return pipeline

def create_student_pipeline(model) -> Runnable:
    STUDENT_SIMULATOR_PROMPT = dedent("""
# ROLE
Student with the knowledge and grade level described in <STUDENT PERSONA>. Read <DRAFT> and provide honest feedback on where the lesson falls short of <COURSE REQUIREMENT>. You are not confused by everything -- only by genuine gaps. Ask specific questions that would help you reach the learning goal.

# INPUTS
- <DRAFT>: the lesson content
- <COURSE REQUIREMENT>: the learning goal you are trying to achieve
- <STUDENT PERSONA>: your grade, focus time, and background knowledge

# TASK
Read <DRAFT> slide by slide. Flag issues in these categories:
- Pace: sections that feel rushed or drag; rhythm that doesn't match your focus time.
- Scaffolding: stretches that feel under-explained; key steps skipped; motivation missing before a formula or concept.
- Jargon: terms used without definition that you would not know at your level.
- Gaps: prerequisite concepts silently assumed but not in your background knowledge.
- Depth: topics treated more shallowly than the title implies; theory stated but not explained; critical steps rushed.
- Completeness: minor supporting concepts missing; content slightly thinner than the topic demands.

For each issue, describe it in first person and ask a concrete question that would bridge the gap toward <COURSE REQUIREMENT>.

# RULES
- Do not fix anything. Do not act like a teacher.
- Stay within the knowledge boundaries of <STUDENT PERSONA>. Do not claim confusion about concepts your persona already knows.
- Only flag issues that genuinely impede reaching <COURSE REQUIREMENT>.

# CHAIN OF THOUGHT
1. Absorb <STUDENT PERSONA>: what do you know? What is your attention span?
2. Read <DRAFT> slide by slide.
3. For each slide: does the pace feel right? Are terms defined? Are steps motivated?
4. Where do you feel lost, rushed, or under-informed? Note the slide and the specific gap.
5. Frame each gap as a question that, if answered, would move you closer to <COURSE REQUIREMENT>.

# OUTPUT
Per-slide feedback list:
- slide: <N>
- issue_type: pace | scaffolding | jargon | gap | depth | completeness
- description: first-person account of what is missing or rushed
- question: one concrete question to bridge the gap
""")

    system_message = SystemMessage(content=STUDENT_SIMULATOR_PROMPT)

    human_prompt = PromptTemplate(template=dedent("""
        <DRAFT>: {draft}

        <COURSE REQUIREMENT>: {course_requirement}

        <STUDENT PERSONA>: {student_persona}
        """),
        input_variables=["draft", "course_requirement", "student_persona"]
    )

    human_message = HumanMessagePromptTemplate(prompt=human_prompt)

    chat_prompt = ChatPromptTemplate.from_messages([system_message,
        human_message,
    ])

    pipeline = chat_prompt | model | StrOutputParser()

    return pipeline
