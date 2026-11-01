
import json
import os
from glob import glob
from textwrap import dedent
from typing import Any

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import StrOutputParser

from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.agent.context import AgentContext
from src.logic.writers.blueprint.agent.feedback import SYSTEM_PROMPT
from src.logic.writers.blueprint.structured_output import LessonBlueprint
from src.path.path_definition import get_project_dir


SUMMARIZE_AUDIT_PROMPT = dedent("""\
# Goal
Summarize the audit report concisely, stating the four dimension scores and total.

# Role
You are a concise report summarizer.

# Inputs
- <AUDIT_REPORT>: the full feedback audit text

# Rules
- State each dimension score.
- State the total.
- If total < +4, output "NOT DONE".
- If total = +4, output "DONE".

# Constraints
- Output must be 2-3 sentences maximum.

# Output
A 2-3 sentence summary with scores and DONE/NOT DONE status.
""")

class FeedbackTool(BaseTool):
    name: str = "feedback_tool"

    description: str = dedent("""\
    Use this tool to audit slide quality across four dimensions: scaffolding, calculation-vs-concept balance, content completeness, and explanatory depth.

    Returns numeric scores + brief reasons for each dimension.

    input format instructions: {input_format_instructions}
    """)

    pipeline: Runnable
    summarize_pipeline: Runnable

    @classmethod
    def create(cls, llm: Runnable):

        input_ = {
            "system": {"template": SYSTEM_PROMPT},
            "human": {
                "template": dedent("""
                    <SLIDE>: {user_query}

                    <KNOWLEDGE_GAP>: {knowledge_gaps}

                    <TEACHING_ADJUSTMENTS>: {teaching_adjustments}
                    
                    <PERSONA>: {persona}
                """),
            }
        }
        pipeline = build_standard_chat_prompt_template(input_) | llm | StrOutputParser()

        summarize_input = {
            "system": {"template": SUMMARIZE_AUDIT_PROMPT},
            "human": {"template": "<AUDIT_REPORT>: {report}"}
        }
        summarize_pipeline = build_standard_chat_prompt_template(summarize_input) | llm | StrOutputParser()

        return cls(pipeline=pipeline, summarize_pipeline=summarize_pipeline)

    def _run(self, runtime: ToolRuntime[AgentContext, Any], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)
        teaching_adjustments = "\n".join(runtime.context.teaching_adjustments)
        persona = runtime.context.persona
        request_id = runtime.context.request_id
        cache_key = runtime.context.cache_key

        input_filename = os.path.join(get_project_dir(), "data", request_id, "input.json")
        target_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

        with open(input_filename, "r", encoding="utf-8") as f:
            course_requirement = json.load(f)["course_requirement"]

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = self.pipeline.invoke({
            "user_query": query,
            "knowledge_gaps": knowledge_gaps,
            "teaching_adjustments": teaching_adjustments,
            "persona": persona,
        })

        feedback_dir = os.path.join(target_dir, "feedback")
        if not os.path.isdir(feedback_dir):
            os.makedirs(feedback_dir)

        feedback_filename = os.path.join(feedback_dir, f"version_{len(drafts)-1}.txt")
        with open(feedback_filename, "w", encoding="utf-8") as file:
            file.write(result)

        runtime.context.feedback = result

        summary = self.summarize_pipeline.invoke({"report": result})
        return f"# FeedbackTool\n{summary}"

    async def _arun(self, runtime: ToolRuntime[AgentContext, Any], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)
        teaching_adjustments = "\n".join(runtime.context.teaching_adjustments)
        persona = runtime.context.persona
        request_id = runtime.context.request_id
        cache_key = runtime.context.cache_key

        input_filename = os.path.join(get_project_dir(), "data", request_id, "input.json")
        target_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

        with open(input_filename, "r", encoding="utf-8") as f:
            course_requirement = json.load(f)["course_requirement"]

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = await self.pipeline.ainvoke({
            "user_query": query,
            "knowledge_gaps": knowledge_gaps,
            "teaching_adjustments": teaching_adjustments,
            "persona": persona,
        })
        feedback_dir = os.path.join(target_dir, "feedback")
        if not os.path.isdir(feedback_dir):
            os.makedirs(feedback_dir)

        feedback_filename = os.path.join(feedback_dir, f"version_{len(drafts)-1}.txt")
        with open(feedback_filename, "w", encoding="utf-8") as file:
            file.write(result)

        runtime.context.feedback = result

        summary = await self.summarize_pipeline.ainvoke({"report": result})
        return f"# FeedbackTool\n{summary}"
