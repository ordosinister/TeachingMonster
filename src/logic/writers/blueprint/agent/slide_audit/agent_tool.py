
import json
import os
from glob import glob
from typing import Any
from textwrap import dedent

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable, RunnableParallel
from langchain_core.output_parsers import StrOutputParser

from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.agent.context import AgentContext
from src.logic.writers.blueprint.agent.slide_audit import prereq_SYSTEM_PROMPT, jargon_SYSTEM_PROMPT
from src.logic.writers.blueprint.structured_output import LessonBlueprint
from src.path.path_definition import get_project_dir


SLIDE_AUDIT_MERGE_PROMPT = dedent("""\
# Goal
Merge prerequisite gap and jargon overload findings into a single unified report with de-duplication, scoring, and an overall verdict.

# Role
You are an enterprise training material audit integrator. You combine parallel diagnostic results into a coherent assessment.

# Inputs
- <PREREQUISITE_GAP>: per-slide gap descriptions with reasons
- <JARGON_OVERLOAD>: per-slide list of undefined or regionally ambiguous terms

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
- <AUDIT_REPORT>: the full slide audit text

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
    name: str = "slide_audit_tool"

    description: str = dedent("""\
        Use this tool to audit slides for prerequisite knowledge gaps and jargon overload issues.

        Runs prerequisite gap analysis and jargon overload detection in parallel, then merges into one report.
        """)

    pipeline: Runnable
    summarize_pipeline: Runnable

    @classmethod
    def create(cls, llm: Runnable):

        prereq_input = {
            "system": {"template": prereq_SYSTEM_PROMPT},
            "human": {
                "template": dedent("""
                    <TARGET_CONTENT>: {user_query}

                    <COURSE_REQUIREMENT>: {course_requirement}
                    
                    <KNOWLEDGE_GAPS> (learning objectives): {knowledge_gaps}
                    
                    <PERSONA>: {persona}
                """),
                "input_variable": ["user_query", "course_requirement", "knowledge_gaps", "persona"]
            }
        }
        prereq_pipeline = build_standard_chat_prompt_template(prereq_input) | llm | StrOutputParser()

        jargon_input = {
            "system": {"template": jargon_SYSTEM_PROMPT},
            "human": {
                "template": dedent("""
                    <TARGET_CONTENT>: {user_query}

                    <COURSE_REQUIREMENT>: {course_requirement}
                    
                    <PERSONA>: {persona}
                    
                    <KNOWLEDGE_GAPS> (learning objectives): {knowledge_gaps}
                """),
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
                    <PREREQUISITE_GAP>:
                    {prerequisite_gap}

                    <JARGON_OVERLOAD>:
                    {jargon_overload}
                """),
            }
        }
        merge_pipeline = build_standard_chat_prompt_template(merge_input) | llm | StrOutputParser()

        slide_audit_pipeline = parallel | merge_pipeline

        summarize_input = {
            "system": {"template": SUMMARIZE_AUDIT_PROMPT},
            "human": {"template": "{report}"}
        }
        summarize_pipeline = build_standard_chat_prompt_template(summarize_input) | llm | StrOutputParser()

        return cls(pipeline=slide_audit_pipeline, summarize_pipeline=summarize_pipeline)

    def _run(self, runtime: ToolRuntime[AgentContext, Any], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)

        request_id = runtime.context.request_id
        cache_key = runtime.context.cache_key
        persona = runtime.context.persona

        input_filename = os.path.join(get_project_dir(), "data", request_id, "input.json")
        target_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

        with open(input_filename, "r", encoding="utf-8") as f:
            course_requirement = json.load(f)["course_requirement"]

        drafts = sorted(glob(f"{os.path.join(target_dir, "draft")}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = self.pipeline.invoke({
            "user_query": query,
            "course_requirement": course_requirement,
            "knowledge_gaps": knowledge_gaps,
            "persona": persona
        })

        feedback_dir = os.path.join(target_dir, "slide_audit")
        if not os.path.isdir(feedback_dir):
            os.makedirs(feedback_dir)

        feedback_filename = os.path.join(feedback_dir, f"version_{len(drafts)-1}.txt")
        with open(feedback_filename, "w", encoding="utf-8") as file:
            file.write(result)

        runtime.context.slide_audit = result

        summary = self.summarize_pipeline.invoke({"report": result})
        return f"# SlideAuditTool\n{summary}"

    async def _arun(self, runtime: ToolRuntime[AgentContext, Any], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)

        request_id = runtime.context.request_id
        cache_key = runtime.context.cache_key
        persona = runtime.context.persona

        input_filename = os.path.join(get_project_dir(), "data", request_id, "input.json")
        target_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

        with open(input_filename, "r", encoding="utf-8") as f:
            course_requirement = json.load(f)["course_requirement"]

        drafts = sorted(glob(f"{os.path.join(target_dir, "draft")}/*.json"), key=os.path.getmtime)

        with open(drafts[-1], "r", encoding="utf-8") as f:
            loaded = LessonBlueprint.model_validate_json(f.read())

        query = "\n\n".join([str(slide.model_dump()) for slide in loaded.slides])

        result = await self.pipeline.ainvoke({
            "user_query": query,
            "course_requirement": course_requirement,
            "knowledge_gaps": knowledge_gaps,
            "persona": persona
        })

        feedback_dir = os.path.join(target_dir, "slide_audit")
        if not os.path.isdir(feedback_dir):
            os.makedirs(feedback_dir)

        feedback_filename = os.path.join(feedback_dir, f"version_{len(drafts) - 1}.txt")
        with open(feedback_filename, "w", encoding="utf-8") as file:
            file.write(result)

        runtime.context.slide_audit = result

        summary = await self.summarize_pipeline.ainvoke({"report": result})
        return f"# SlideAuditTool\n{summary}"
