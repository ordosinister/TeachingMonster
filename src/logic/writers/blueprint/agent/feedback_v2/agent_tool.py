import importlib
import json
import os
from textwrap import dedent
from glob import glob

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field

from src.path.path_definition import get_project_dir
from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.structured_output import StudentProfileInterpretation, LessonBlueprint

SUMMARIZE_AUDIT_PROMPT = dedent("""\nSummarize the following audit report. State the four dimension scores and the total. If total < +4, output "NOT DONE". If total = +4, output "DONE". Be concise.\n""")


class Inputs(BaseModel):
    request_id: str = Field(description="An id which has the following structure `celery_[d]{4}_[d]{10}`")


class FeedbackTool(BaseTool):
    input_parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=Inputs)
    input_format_instructions: str = input_parser.get_format_instructions()

    name: str = "feedback_tool"
    description_template: str = dedent("""\
    Use this tool to audit slide quality across four dimensions: scaffolding, calculation-vs-concept balance, content completeness, and explanatory depth.

    Returns numeric scores + brief reasons for each dimension.

    input format instructions: {input_format_instructions}
    """)

    description: str = description_template.format(input_format_instructions=input_format_instructions)

    pipeline: Runnable
    summarize_pipeline: Runnable

    @classmethod
    def create(cls, llm: Runnable, subject: str):
        module_path = f"src.logic.writers.blueprint.agent.feedback_v2.{subject}"
        module = importlib.import_module(module_path)

        input_ = {
            "system": {"template": module.SYSTEM_PROMPT},
            "human": {
                "template": dedent("""
                    SLIDE: {user_query}

                    KNOWLEDGE_GAP: {knowledge_gaps}

                    TEACHING_ADJUSTMENTS: {teaching_adjustments}
                """),
                "input_variable": ["user_query", "knowledge_gaps", "teaching_adjustments"]
            }
        }
        pipeline = build_standard_chat_prompt_template(input_) | llm | StrOutputParser()

        summarize_input = {
            "system": {"template": SUMMARIZE_AUDIT_PROMPT},
            "human": {"template": "{report}", "input_variable": ["report"]}
        }
        summarize_pipeline = build_standard_chat_prompt_template(summarize_input) | llm | StrOutputParser()

        return cls(pipeline=pipeline, summarize_pipeline=summarize_pipeline)

    def _run(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)
        teaching_adjustments = "\n".join(runtime.context.teaching_adjustments)

        args = input.get("input", input)

        request_id = args['request_id']
        target_dir = os.path.join(get_project_dir(), "data", request_id)

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = self.pipeline.invoke({
            "user_query": query,
            "knowledge_gaps": knowledge_gaps,
            "teaching_adjustments": teaching_adjustments,
        })

        feedback_dir = os.path.join(target_dir, "feedback_v2")
        if not os.path.isdir(feedback_dir):
            os.makedirs(feedback_dir)

        feedback_filename = os.path.join(feedback_dir, f"version_{len(drafts)-1}.txt")
        with open(feedback_filename, "w", encoding="utf-8") as file:
            file.write(result)

        summary = self.summarize_pipeline.invoke({"report": result})
        return f"# FeedbackTool\n{summary}"

    async def _arun(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)
        teaching_adjustments = "\n".join(runtime.context.teaching_adjustments)

        args = input.get("input", input)

        request_id = args['request_id']
        target_dir = os.path.join(get_project_dir(), "data", request_id)

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = await self.pipeline.ainvoke({
            "user_query": query,
            "knowledge_gaps": knowledge_gaps,
            "teaching_adjustments": teaching_adjustments,
        })
        feedback_dir = os.path.join(target_dir, "feedback_v2")
        if not os.path.isdir(feedback_dir):
            os.makedirs(feedback_dir)

        feedback_filename = os.path.join(feedback_dir, f"version_{len(drafts)-1}.txt")
        with open(feedback_filename, "w", encoding="utf-8") as file:
            file.write(result)

        summary = await self.summarize_pipeline.ainvoke({"report": result})
        return f"# FeedbackTool\n{summary}"
