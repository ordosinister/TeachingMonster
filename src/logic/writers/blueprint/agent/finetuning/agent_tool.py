
import json
import os
from glob import glob
from textwrap import dedent
from typing import Any

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field

from src.logic.writers.blueprint.agent.finetuning import SYSTEM_PROMPT, MERGE_SYSTEM_PROMPT
from src.logic import build_standard_chat_prompt_template
from src.path.path_definition import get_project_dir
from src.logic.writers.blueprint.agent.context import AgentContext
from src.logic.writers.blueprint.structured_output import LessonBlueprint


class FineTuningTool(BaseTool):

    name: str = "finetuning_tool"

    description: str = dedent("""\
    Use this tool to extract improvements from audit feedback and merge them into the image content and speaker notes.
    """)

    pipeline: Runnable

    @classmethod
    def create(cls, llm: Runnable):
        system_prompt = SYSTEM_PROMPT
        improve_input = {
            "system": {"template": system_prompt},
            "human": {
                "template": dedent("""
                    <SLIDE>: {user_query}

                    <COURSE_REQUIREMENT>: {course_requirement}

                    <FEEDBACK>: {feedback}
                    
                    <SLIDE_AUDIT>: {slide_audit}
                    
                    <PERSONA>: {persona}
                    
                    <KNOWLEDGE_GAPS>: {knowledge_gaps}
                """),
            }
        }
        improve_pipeline = build_standard_chat_prompt_template(improve_input) | llm | StrOutputParser()

        output_parser = PydanticOutputParser(pydantic_object=LessonBlueprint)
        format_instructions = output_parser.get_format_instructions()

        merge_input = {
            "system": {"template": MERGE_SYSTEM_PROMPT,
                       "partial_variables": {"format_instructions": format_instructions}},
            "human": {
                "template": dedent("""
                    <SLIDES>: {user_query}

                    <IMPROVEMENTS>: {improvements}

                    <COURSE_REQUIREMENT>: {course_requirement}
                """),
                "input_variable": ["user_query", "improvements", "course_requirement"],
            }
        }
        merge_pipeline = build_standard_chat_prompt_template(merge_input) | llm | output_parser

        pipeline = (
            RunnablePassthrough.assign(improvements=improve_pipeline)
            | merge_pipeline
        )
        return cls(pipeline=pipeline)

    def _run(self, runtime: ToolRuntime[AgentContext, Any], **input):
        print(f"Running {self.name}...")
        args = input.get("input", input)

        feedback = args.get("feedback", "")

        request_id = runtime.context.request_id
        cache_key = runtime.context.cache_key
        persona = runtime.context.persona
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)

        input_filename = os.path.join(get_project_dir(), "data", request_id, "input.json")
        target_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

        slide_audit = runtime.context.slide_audit
        if slide_audit is None:
            return "Slide audit is not available, please call the Tool `slide_audit_tool`"

        feedback = runtime.context.feedback
        if feedback is None:
            return "Feedback is not available, please call the Tool `feedback_tool`"

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(input_filename, "r", encoding="utf-8") as f:
            input_data = json.load(f)

        course_requirement = input_data["course_requirement"]

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = self.pipeline.invoke({
            "user_query": query,
            "course_requirement": course_requirement,
            "feedback": feedback,
            "slide_audit": slide_audit,
            "persona": persona,
            "knowledge_gaps": knowledge_gaps,
        })

        filename = os.path.join(target_dir, "draft", f"version_{len(drafts)}.json")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        runtime.context.slide_audit = None
        runtime.context.feedback = None

        return f"Merged draft saved to {filename}"

    async def _arun(self, runtime: ToolRuntime[AgentContext, Any], **input):
        print(f"Running {self.name}...")
        args = input.get("input", input)

        feedback = args.get("feedback", "")

        request_id = runtime.context.request_id
        cache_key = runtime.context.cache_key
        persona = runtime.context.persona
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)

        input_filename = os.path.join(get_project_dir(), "data", request_id, "input.json")
        target_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(input_filename, "r", encoding="utf-8") as f:
            input_data = json.load(f)

        course_requirement = input_data["course_requirement"]

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        slide_audit = runtime.context.slide_audit
        if slide_audit is None:
            return "Slide audit is not available, please call the Tool `slide_audit_tool`"

        feedback = runtime.context.feedback
        if feedback is None:
            return "Feedback is not available, please call the Tool `feedback_tool`"

        result = await self.pipeline.ainvoke({
            "user_query": query,
            "course_requirement": course_requirement,
            "feedback": feedback,
            "slide_audit": slide_audit,
            "persona": persona,
            "knowledge_gaps": knowledge_gaps,
        })

        filename = os.path.join(target_dir, "draft", f"version_{len(drafts)}.json")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        runtime.context.slide_audit = None
        runtime.context.feedback = None

        return f"Merged draft saved to {filename}"
