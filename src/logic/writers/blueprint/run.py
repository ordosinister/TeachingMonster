"""Blueprint generation: creates structured lesson plans from course requirements.

Uses LLM-based pipelines to generate ordered slide sequences with titles,
content, speaker notes, and transitions. Includes subject classification,
multi-agent feedback loops, and mathematical validation.
"""

import json
import logging
import os
from typing import Literal
from textwrap import dedent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blueprint")

from langchain.agents import create_agent
from langchain.agents.middleware.tool_retry import ToolRetryMiddleware
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage
from glob import glob
from langchain_core.runnables import RunnablePassthrough
from ollama._types import ResponseError

"""Blueprint generation: creates structured lesson plans from course requirements.

Uses LLM-based pipelines to generate ordered slide sequences with titles,
content, speaker notes, and transitions. Includes subject classification,
multi-agent feedback loops, and mathematical validation.
"""

from model_orchestration import get_model_config
from src.io.path_definition import get_project_dir
from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.generation_pipeline import (create_presentation_pipeline, create_slide_pipeline,
                                                             create_background_pipeline, create_adaptability_pipeline,
                                                             create_student_pipeline)
from src.logic.writers.blueprint.subject_classifier import classification
from src.logic.writers.blueprint.agent.finetuning_v2.agent_tool import FineTuningTool
from src.logic.writers.blueprint.agent.slide_audit.agent_tool import SlideAuditTool
from src.logic.writers.blueprint.agent.feedback_v2.agent_tool import FeedbackTool
from src.logic.writers.blueprint.structured_output import LessonBlueprint, AdaptabilityOutput, StudentProfileInterpretation
from src.logic.writers.blueprint.agent import AGENT_INSTRUCTION
from src.logic.writers.blueprint.post_processing.math_validation import run_math_validation

from src.logic.writers.blueprint.post_processing.concept_supervision import run_concept_supervision

def main(request_id: str, course_requirement: str, student_persona: str) -> str:

    env = os.environ['env']

    subject = classification(course_requirement, env=env)

    logger.info(f"{request_id} subject: {subject}")

    target_dir = os.path.join(get_project_dir(), "data", request_id)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)

    output_filename = os.path.join(target_dir, "blueprint.json")
    if os.path.isfile(output_filename):
        return subject

    input_filename = os.path.join(target_dir, "input.json")
    with open(input_filename, "w", encoding="utf-8") as f:
        json.dump({"course_requirement": course_requirement, "student_persona": student_persona}, f)

    model_main = get_model_config(env)['main']
    model_sub = get_model_config(env)['sub']

    background_pipeline = create_background_pipeline(model_main, subject=subject)

    while True:
        try:
            pedagogical_state = background_pipeline.invoke({
                "course_requirement": course_requirement,
                "student_persona": student_persona
            })
            break
        except OutputParserException:
            logger.info(f"{request_id} Background Parsing Error")

    logger.info(f"{request_id} pedagogical_state: {pedagogical_state}")

    presentation_pipeline = create_presentation_pipeline(get_model_config(env)['master'], subject=subject)

    logger.info(f"Start drafting {request_id}")

    while True:
        try:
            output = presentation_pipeline.invoke({
                "course_requirement": course_requirement,
                "student_persona": student_persona,
                "pedagogical_state": pedagogical_state
            })
            break
        except OutputParserException:
            logger.info(f"{request_id} Drafting Parsing Error")

    draft_dir = os.path.join(target_dir, "draft")
    if not os.path.isdir(draft_dir):
        os.makedirs(draft_dir)

    with open(os.path.join(draft_dir, "version_0.json"), "w", encoding="utf-8") as f:
        f.write(output.model_dump_json(indent=2))

    tools = [SlideAuditTool.create(llm=model_main, subject=subject),
             FeedbackTool.create(llm=model_main, subject=subject),
             FineTuningTool.create(llm=model_sub, subject=subject)]

    agent = create_agent(
        model=model_main,
        name="planning_blueprint_reflection_agent",
        tools=tools,
        system_prompt=AGENT_INSTRUCTION,
        middleware=[
            ToolRetryMiddleware(max_retries=2),
            ToolCallLimitMiddleware(exit_behavior='end',
                                    run_limit=4,
                                    tool_name="finetuning_tool")
        ]
    )

    agent_input = {"messages": HumanMessage(content=request_id)}
    agent_result = agent.invoke(agent_input, context=output.student_profile)

    print(agent_result['messages'][-1])

    drafts_final = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)
    with open(drafts_final[-1], "r", encoding="utf-8") as f:
        draft = LessonBlueprint.model_validate_json(f.read())

    slide_pipeline = create_slide_pipeline(model=get_model_config(env)['master'],
                                           subject=subject, pydantic_object=LessonBlueprint)

    while True:
        try:
            logger.info(f"Start the final script generation")
            slide_output = slide_pipeline.invoke({
                "draft": draft.model_dump_json(),
                "course_requirement": course_requirement,
                "student_persona": student_persona,
                "pedagogical_state": pedagogical_state
            })
            break
        except Exception as e:
            print(f"request_id: {request_id}, exception: {e}")

    # --- Math Verification ---
    slide_output = run_math_validation(slide_output, target_dir, env)

    slide_output = run_concept_supervision(slide_output, env, output_filename)

    return subject


if __name__ == "__main__":

    course_requirement = dedent("""
          Big Concept: Triangle Centers
Topic: Comparing Triangle Centers in Different Contexts
Bloom's Taxonomy: analyze, evaluate
Learning Goal: Analyze: Compare centroid, incenter, and circumcenter
Evaluate: Determine the most appropriate center in different scenarios and justify the reasoning
Key Learning Points: Properties of centroid, incenter, and circumcenter
Distance relationships (to sides vs vertices)
Functional differences of triangle centers
          """)

    student_persona = dedent("""
         Grade: 9th gradeFocus Time: 15 minutesBackground Knowledge: Has: basic definitions of triangle centersLacks: ability to compare and apply concepts in different contexts
          """)
    main("abcdefgh", course_requirement, student_persona, env="")
