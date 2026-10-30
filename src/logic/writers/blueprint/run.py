"""Blueprint generation: creates structured lesson plans from course requirements.

Uses LLM-based pipelines to generate ordered slide sequences with titles,
content, speaker notes, and transitions. Includes subject classification,
multi-agent feedback loops, and mathematical validation.
"""

import hashlib
import json
import logging
import os
import shutil
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
from model_orchestration import get_model_config
from src.path.path_definition import get_project_dir
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

def _get_cache_key(course_requirement: str, persona: str) -> str:
    """Generate a cache key from (course_requirement, persona).

    One course_requirement may map to multiple persona (e.g. different regions),
    so the cache key includes both fields.
    """
    normalized = f"{course_requirement.strip()}|{persona.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _copy_from_cache(cache_key: str, target_dir: str) -> bool:
    """Copy cached blueprint directory to target_dir if cache exists."""
    cache_dir = os.path.join(get_project_dir(), "data", "cache", "blueprints", cache_key)
    if not os.path.isdir(cache_dir):
        return False
    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir)
    shutil.copytree(cache_dir, target_dir)
    return True


def _save_to_cache(cache_key: str, source_dir: str) -> None:
    """Copy source_dir to cache directory for future reuse."""
    cache_dir = os.path.join(get_project_dir(), "data", "cache", "blueprints", cache_key)
    if os.path.isdir(cache_dir):
        shutil.rmtree(cache_dir)
    shutil.copytree(source_dir, cache_dir)


def main(request_id: str, course_requirement: str, persona: str) -> str:

    env = os.environ['env']

    # Compute subject classification early; needed for pipeline and return value.
    subject = classification(course_requirement, env)

    logger.info(f"{request_id}")

    target_dir = os.path.join(get_project_dir(), "data", request_id)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)

    output_filename = os.path.join(target_dir, "blueprint.json")
    if os.path.isfile(output_filename):
        return subject

    # Check (course_requirement, persona) cache before running pipeline.
    cache_key = _get_cache_key(course_requirement, persona)
    if _copy_from_cache(cache_key, target_dir):
        logger.info(f"{request_id} Cache hit for (course_requirement, persona)")
        return subject

    input_filename = os.path.join(target_dir, "input_v2.json")
    with open(input_filename, "w", encoding="utf-8") as f:
        json.dump({"course_requirement": course_requirement, "student_persona": persona}, f)

    model_main = get_model_config(env)['main']
    model_sub = get_model_config(env)['sub']

    background_pipeline = create_background_pipeline(model_main, subject=subject)

    while True:
        try:
            pedagogical_state = background_pipeline.invoke({
                "course_requirement": course_requirement,
                "student_persona": persona
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
                "student_persona": persona,
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
                "student_persona": persona,
                "pedagogical_state": pedagogical_state
            })
            break
        except Exception as e:
            print(f"request_id: {request_id}, exception: {e}")

    # --- Math Verification ---
    slide_output = run_math_validation(slide_output, target_dir, env)

    slide_output = run_concept_supervision(slide_output, env, output_filename)

    # Cache the completed blueprint for future (course_requirement, persona) reuse.
    _save_to_cache(cache_key, target_dir)

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
    os.environ['env'] = "PROD"
    main("abcdefgh", course_requirement, student_persona)
