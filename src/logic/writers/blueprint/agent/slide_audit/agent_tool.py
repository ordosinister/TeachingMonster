import importlib
import json
import os
from textwrap import dedent
from glob import glob

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable, RunnableParallel
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field

from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.structured_output import StudentProfileInterpretation, LessonBlueprint
from src.logic.writers.blueprint.agent.slide_audit import prereq_SYSTEM_PROMPT, jargon_SYSTEM_PROMPT
from src.path.path_definition import get_project_dir


class Inputs(BaseModel):
    request_id: str = Field(description="An ID which has the following structure `celery_[d]{4}_[d]{10}`")


SLIDE_AUDIT_MERGE_PROMPT = dedent("""\
# Goal
Merge prerequisite gap and jargon overload findings into a single unified report with de-duplication, scoring, and an overall verdict.

# Role
You are an enterprise training material audit integrator. You combine parallel diagnostic results into a coherent assessment.

# Inputs
- PREREQUISITE GAP: per-slide gap descriptions with reasons
- JARGON OVERLOAD: per-slide list of undefined or regionally ambiguous terms

# Rules
- Preserve each gap description and term exactly as received. Never annotate with extra values or interpretations.
- De-duplicate: if the same gap appears in both analyses, list it once under the more detailed description.
- Missing knowledge_gap coverage = blocking issue -> Needs Major Rework.
- Scores must cite the rubric tier. Never combine or sum scores.

# Constraints
- Score assignments must follow the rubric exactly. No interpolation between tiers.

# Output
# SlideAuditTool

Slide <N>: Gap -- <description>
Slide <N>: Jargon -- <term>
...

Prerequisite Gap Score: <score> -- <reason>
Jargon Overload Score: <score> -- <reason>
Overall Verdict: <Pass / Needs Minor Fixes / Needs Major Rework>
""")


SUMMARIZE_AUDIT_PROMPT = dedent("""\
# Goal
Summarize the audit report in 2-3 sentences, including key scores and the most critical issues.

# Role
You are a concise report summarizer.

# Inputs
- AUDIT REPORT: the full slide audit text

# Rules
- Include key scores.
- Highlight the most critical issues.
- Be concise.

# Constraints
- Maximum 3 sentences.

# Output
A 2-3 sentence summary of the audit.
""")

class SlideAuditTool(BaseTool):
    input_parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=Inputs)
    input_format_instructions: str = input_parser.get_format_instructions()

    name: str = "slide_audit_tool"
    description_template: str = dedent("""\
    Use this tool to audit slides for prerequisite knowledge gaps and jargon overload issues.

    Runs prerequisite gap analysis and jargon overload detection in parallel, then merges into one report.

    input format instructions: {input_format_instructions}
    """)

    description: str = description_template.format(input_format_instructions=input_format_instructions)

    pipeline: Runnable
    summarize_pipeline: Runnable

    @classmethod
    def create(cls, llm: Runnable):

        prereq_input = {
            "system": {"template": prereq_SYSTEM_PROMPT},
            "human": {
                "template": dedent("""
                    TARGET CONTENT: {user_query}

                    COURSE_REQUIREMENT: {course_requirement}

                    KNOWLEDGE_GAPS (learning objectives): {knowledge_gaps}
                """),
                "input_variable": ["user_query", "course_requirement", "knowledge_gaps"]
            }
        }
        prereq_pipeline = build_standard_chat_prompt_template(prereq_input) | llm | StrOutputParser()

        jargon_input = {
            "system": {"template": jargon_SYSTEM_PROMPT},
            "human": {
                "template": dedent("""
                    TARGET CONTENT: {user_query}

                    COURSE_REQUIREMENT: {course_requirement}

                    KNOWLEDGE_GAPS (learning objectives): {knowledge_gaps}
                """),
                "input_variable": ["user_query", "course_requirement", "knowledge_gaps"]
            }
        }
        jargon_pipeline = build_standard_chat_prompt_template(jargon_input) | llm | StrOutputParser()

        parallel = RunnableParallel(
            prerequisite_gap=prereq_pipeline,
            jargon_overload=jargon_pipeline
        )

        merge_input = {
            "system": {"template": SLIDE_AUDIT_MERGE_PROMPT},
            "human": {
                "template": dedent("""
                    PREREQUISITE GAP ANALYSIS:
                    {prerequisite_gap}

                    JARGON OVERLOAD ANALYSIS:
                    {jargon_overload}
                """),
                "input_variable": ["prerequisite_gap", "jargon_overload"]
            }
        }
        merge_pipeline = build_standard_chat_prompt_template(merge_input) | llm | StrOutputParser()

        slide_audit_pipeline = parallel | merge_pipeline

        summarize_input = {
            "system": {"template": SUMMARIZE_AUDIT_PROMPT},
            "human": {"template": "{report}", "input_variable": ["report"]}
        }
        summarize_pipeline = build_standard_chat_prompt_template(summarize_input) | llm | StrOutputParser()

        return cls(pipeline=slide_audit_pipeline, summarize_pipeline=summarize_pipeline)

    def _run(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)

        args = input.get("input", input)

        request_id = args['request_id']
        target_dir = os.path.join(get_project_dir(), "data", request_id)

        with open(os.path.join(target_dir, "input.json"), "r", encoding="utf-8") as f:
            course_requirement = json.load(f)["course_requirement"]

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = self.pipeline.invoke({
            "user_query": query,
            "course_requirement": course_requirement,
            "knowledge_gaps": knowledge_gaps
        })

        feedback_dir = os.path.join(target_dir, "slide_audit")
        if not os.path.isdir(feedback_dir):
            os.makedirs(feedback_dir)

        feedback_filename = os.path.join(feedback_dir, f"version_{len(drafts)-1}.txt")
        with open(feedback_filename, "w", encoding="utf-8") as file:
            file.write(result)

        summary = self.summarize_pipeline.invoke({"report": result})
        return f"# SlideAuditTool\n{summary}"

    async def _arun(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)

        args = input.get("input", input)

        request_id = args['request_id']
        target_dir = os.path.join(get_project_dir(), "data", request_id)

        with open(os.path.join(target_dir, "input.json"), "r", encoding="utf-8") as f:
            course_requirement = json.load(f)["course_requirement"]

        drafts = sorted(glob(f"{os.path.join(target_dir, 'draft')}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = await self.pipeline.ainvoke({
            "user_query": query,
            "course_requirement": course_requirement,
            "knowledge_gaps": knowledge_gaps
        })

        summary = await self.summarize_pipeline.ainvoke({"report": result})
        return f"# SlideAuditTool\n{summary}"

