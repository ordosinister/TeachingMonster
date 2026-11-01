"""Blueprint generation: creates structured lesson plans from course requirements.

Uses LLM-based pipelines to generate ordered slide sequences with titles,
content, speaker notes, and transitions. Includes subject classification,
multi-agent feedback loops, and mathematical validation.
"""

import hashlib
import logging
import os
import shutil
from typing import Literal, Tuple
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
from src.logic.writers.blueprint.post_processing.consistency_check import run_consistency_check

from src.logic.writers.blueprint.agent import AGENT_INSTRUCTION
from src.logic.writers.blueprint.agent.context import AgentContext
from src.logic.writers.blueprint.agent.finetuning.agent_tool import FineTuningTool
from src.logic.writers.blueprint.agent.slide_audit.agent_tool import SlideAuditTool
from src.logic.writers.blueprint.agent.feedback.agent_tool import FeedbackTool
from src.logic.writers.blueprint.generation_pipeline import (create_presentation_pipeline, create_slide_pipeline,
                                                             create_background_pipeline)
from src.logic.writers.blueprint.structured_output import LessonBlueprint
from src.path.path_definition import get_project_dir

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


def main(request_id: str, course_requirement: str, persona: str) -> Tuple[str, str]:

    env = os.environ['env']

    model_main = get_model_config(env)['main']
    model_sub = get_model_config(env)['sub']

    logger.info(f"{request_id}")

    # Check (course_requirement, persona) cache before running pipeline.
    cache_key = _get_cache_key(course_requirement, persona)
    logger.info(f"cache_key: {cache_key}")

    target_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)

    output_filename = os.path.join(target_dir, "blueprint.json")
    if os.path.isfile(output_filename):
        return course_requirement, persona

    draft_dir = os.path.join(target_dir, "draft")
    if not os.path.isdir(draft_dir):
        os.makedirs(draft_dir)

    draft_v0 = os.path.join(draft_dir, "version_0.json")

    if not os.path.isfile(draft_v0):

        background_pipeline = create_background_pipeline(model_main)

        while True:
            try:
                pedagogical_state = background_pipeline.invoke({
                    "course_requirement": course_requirement,
                    "student_persona": persona
                })
                break
            except OutputParserException:
                logger.info(f"{request_id} Background Parsing Error")

        logger.info(f"{request_id} {cache_key} pedagogical_state: {pedagogical_state}")

        presentation_pipeline = create_presentation_pipeline(get_model_config(env)['master'])

        logger.info(f"Start drafting {request_id}/{cache_key}")

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

        with open(os.path.join(draft_dir, "version_0.json"), "w", encoding="utf-8") as f:
            f.write(output.model_dump_json(indent=2))

    else:
        with open(draft_v0, "r", encoding="utf-8") as f:
            output = LessonBlueprint.model_validate_json(f.read())


    tools = [
             SlideAuditTool.create(llm=model_main),
             FeedbackTool.create(llm=model_main),
             FineTuningTool.create(llm=model_sub)
             ]

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

    context = AgentContext(
        knowledge_gaps=output.student_profile.knowledge_gaps,
        teaching_adjustments=output.student_profile.teaching_adjustments,
        request_id=request_id,
        cache_key=cache_key,
        feedback=None,
        slide_audit=None
    )

    USER_QUERY = "Execute the slide audit and refinement pipeline."

    agent_input = {"messages": HumanMessage(content=USER_QUERY)}
    agent_result = agent.invoke(agent_input, context=context)

    print(agent_result['messages'][-1])

    drafts_final = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)
    with open(drafts_final[-1], "r", encoding="utf-8") as f:
        draft = LessonBlueprint.model_validate_json(f.read())

    slide_pipeline = create_slide_pipeline(model=get_model_config(env)['master'],
                                           pydantic_object=LessonBlueprint)

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

    # --- Consistency Check ---
    slide_output = run_consistency_check(
        slide_output, course_requirement, pedagogical_state, target_dir, env, output_filename
    )
    # Cache the completed blueprint for future (course_requirement, persona) reuse.
    _save_to_cache(cache_key, target_dir)

    return course_requirement, persona


if __name__ == "__main__":

    import json

    from extraction.powerpoint import main as powerpoint_main
    from src.path.path_definition import get_project_dir

    os.environ['env'] = "DEV"

    request_id = powerpoint_main.run(pptx_path=r"data/Attire for Sales Professionals 241113 updated 3.pptx")

    print(request_id)

    input_dir = os.path.join(get_project_dir(), "data", request_id)

    input_filename = os.path.join(input_dir, "input.json")

    with open(input_filename, "r", encoding="utf-8") as f:
        course_requirement = json.load(f)

    course_requirement = json.dumps(course_requirement)

    student_persona = "台灣的新進員工"

    main(request_id, course_requirement, student_persona)
