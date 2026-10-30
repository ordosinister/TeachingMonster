import json
import os
from textwrap import dedent
from glob import glob

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field

from src.logic.writers.blueprint.agent.finetuning_v2 import MERGE_SYSTEM_PROMPT
from src.logic import build_standard_chat_prompt_template
from src.path.path_definition import get_project_dir
from src.logic.writers.blueprint.structured_output import StudentProfileInterpretation, LessonBlueprint


class Inputs(BaseModel):
    request_id: str = Field(description="An id which has the following structure `celery_[d]{4}_[d]{10}`")
    feedback: str = Field(description="Feedback from one audit tool: slide_audit_tool, feedback_tool")


class FineTuningTool(BaseTool):
    input_parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=Inputs)
    input_format_instructions: str = input_parser.get_format_instructions()

    name: str = "finetuning_tool"
    description_template: str = dedent("""\
    Use this tool to extract improvements from audit feedback and merge them into the slide content and speaker notes.

    input format: {input_format_instructions}
    """)

    description: str = description_template.format(input_format_instructions=input_format_instructions)

    pipeline: Runnable

    @classmethod
    def create(cls, llm: Runnable, subject: str):
        import importlib
        mod = importlib.import_module(f"src.logic.writers.blueprint.agent.finetuning_v2.{subject}")
        system_prompt = mod.SYSTEM_PROMPT
        improve_input = {
            "system": {"template": system_prompt},
            "human": {
                "template": dedent("""
                    SLIDE: {user_query}

                    COURSE_REQUIREMENT: {course_requirement}

                    INFERRED_LEVEL: {inferred_level}

                    FEEDBACK: {feedback}
                """),
                "input_variable": ["user_query", "course_requirement", "inferred_level", "feedback"]
            }
        }
        improve_pipeline = build_standard_chat_prompt_template(improve_input) | llm | StrOutputParser()

        output_parser = PydanticOutputParser(pydantic_object=LessonBlueprint)
        format_instructions = output_parser.get_format_instructions()

        merge_input = {
            "system": {"template": MERGE_SYSTEM_PROMPT},
            "human": {
                "template": dedent("""
                    SLIDES: {user_query}

                    IMPROVEMENTS: {improvements}

                    COURSE_REQUIREMENT: {course_requirement}

                    INFERRED_LEVEL: {inferred_level}
                    
                    Output format instructions: {format_instructions}
                """),
                "input_variable": ["user_query", "improvements", "course_requirement", "inferred_level"],
                "partial_variables": {'format_instructions': format_instructions}
            }
        }
        merge_pipeline = build_standard_chat_prompt_template(merge_input) | llm | output_parser

        pipeline = (
            RunnablePassthrough.assign(improvements=improve_pipeline)
            | merge_pipeline
        )
        return cls(pipeline=pipeline)

    @staticmethod
    def _resolve_feedback(target_dir: str, feedback: str) -> str:
        """Detect tool source from feedback tag and load the latest full result."""
        tool_folders = {
            "# SlideAuditTool": "slide_audit",
            "# FeedbackTool": "feedback_v2",
            # "# MathTool": "mathematic_coder_v2",
        }
        for tag, folder in tool_folders.items():
            if tag in feedback:
                full_dir = os.path.join(target_dir, folder)
                if os.path.isdir(full_dir):
                    files = sorted(glob(os.path.join(full_dir, "*.txt")), key=os.path.getmtime)
                    if files:
                        with open(files[-1], "r", encoding="utf-8") as f:
                            return f.read()
                break
        return feedback

    def _run(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        args = input.get("input", input)

        request_id = args['request_id']
        feedback = args.get('feedback', "")
        inferred_level = runtime.context.inferred_level

        target_dir = os.path.join(get_project_dir(), "data", request_id)
        full_feedback = self._resolve_feedback(target_dir, feedback)
        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(os.path.join(target_dir, "input.json"), "r", encoding="utf-8") as f:
            input_data = json.load(f)
        course_requirement = input_data["course_requirement"]

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = self.pipeline.invoke({
            "user_query": query,
            "course_requirement": course_requirement,
            "inferred_level": inferred_level,
            "feedback": full_feedback
        })

        filename = os.path.join(target_dir, "draft", f"version_{len(drafts)}.json")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
        return f"Merged draft saved to {filename}"

    async def _arun(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        args = input.get("input", input)

        request_id = args['request_id']
        feedback = args.get('feedback', "")
        inferred_level = runtime.context.inferred_level

        target_dir = os.path.join(get_project_dir(), "data", request_id)
        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(os.path.join(target_dir, "input.json"), "r", encoding="utf-8") as f:
            input_data = json.load(f)
        course_requirement = input_data["course_requirement"]

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        full_feedback = self._resolve_feedback(target_dir, feedback)

        result = await self.pipeline.ainvoke({
            "user_query": query,
            "course_requirement": course_requirement,
            "inferred_level": inferred_level,
            "feedback": full_feedback
        })

        filename = os.path.join(target_dir, "draft", f"version_{len(drafts)}.json")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        return f"Merged draft saved to {filename}"
