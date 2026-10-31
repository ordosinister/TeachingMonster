import os
from textwrap import dedent
from glob import glob

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field

from src.path.path_definition import get_project_dir
from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.structured_output import LessonBlueprint
from src.logic.writers.blueprint.agent.feedback import SYSTEM_PROMPT
from src.logic.writers.blueprint.agent.context import AgentContext

SUMMARIZE_AUDIT_PROMPT = dedent("""\
# Goal
Summarize the audit report concisely, stating the four dimension scores and total.

# Role
You are a concise report summarizer.

# Inputs
- AUDIT REPORT: the full feedback audit text

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
    def create(cls, llm: Runnable):

        input_ = {
            "system": {"template": SYSTEM_PROMPT},
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

    def _run(self, runtime: ToolRuntime[AgentContext], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)
        teaching_adjustments = "\n".join(runtime.context.teaching_adjustments)
        request_id = runtime.context.request_id
        cache_key = runtime.context.cache_key

        target_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = self.pipeline.invoke({
            "user_query": query,
            "knowledge_gaps": knowledge_gaps,
            "teaching_adjustments": teaching_adjustments,
        })

        feedback_dir = os.path.join(target_dir, "feedback")
        if not os.path.isdir(feedback_dir):
            os.makedirs(feedback_dir)

        feedback_filename = os.path.join(feedback_dir, f"version_{len(drafts)-1}.txt")
        with open(feedback_filename, "w", encoding="utf-8") as file:
            file.write(result)

        summary = self.summarize_pipeline.invoke({"report": result})
        return f"# FeedbackTool\n{summary}"

    async def _arun(self, runtime: ToolRuntime[AgentContext], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)
        teaching_adjustments = "\n".join(runtime.context.teaching_adjustments)
        request_id = runtime.context.request_id
        cache_key = runtime.context.cache_key

        # args = input.get("input", input)
        target_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = await self.pipeline.ainvoke({
            "user_query": query,
            "knowledge_gaps": knowledge_gaps,
            "teaching_adjustments": teaching_adjustments,
        })
        feedback_dir = os.path.join(target_dir, "feedback")
        if not os.path.isdir(feedback_dir):
            os.makedirs(feedback_dir)

        feedback_filename = os.path.join(feedback_dir, f"version_{len(drafts)-1}.txt")
        with open(feedback_filename, "w", encoding="utf-8") as file:
            file.write(result)

        summary = await self.summarize_pipeline.ainvoke({"report": result})
        return f"# FeedbackTool\n{summary}"
