import json
import importlib
from textwrap import dedent

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field

from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.structured_output import StudentProfileInterpretation



class Inputs(BaseModel):
    user_query: str = Field(description="The target content/lesson to analyze for prerequisites")


class PrerequisiteGapTool(BaseTool):
    input_parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=Inputs)
    input_format_instructions: str = input_parser.get_format_instructions()

    name: str = "Prerequisite gap analysis tool"
    description_template: str = dedent("""\
    Use this tool to identify prerequisite knowledge gaps and suggest how to bridge them.
    
    Analyzes the `user_query` against `knowledge_gaps` to:
    - Extract implicit prerequisites from the content
    - Detect gaps between what the student knows and what they need to know
    - Identify dependency ordering issues among learning objectives
    - Propose concrete gap-filling strategies for a smooth learning experience
    
    input format instructions: {input_format_instructions}
    """)

    description: str = description_template.format(input_format_instructions=input_format_instructions)

    pipeline: Runnable

    @classmethod
    def create(cls, llm: Runnable, subject: str):

        module_path = f"src.logic.writers.blueprint.prerequisite_gap.{subject}"
        module = importlib.import_module(module_path)

        input_ = {"system": {"template": module.SYSTEM_PROMPT},
                  "human": {"template": dedent("""
                                            TARGET CONTENT: {user_query}

                                            COURSE_REQUIREMENT: {course_requirement}
                                            
                                            KNOWLEDGE_GAPS (learning objectives): {knowledge_gaps}
                                            """),
                            "input_variable": ["user_query", "course_requirement", "knowledge_gaps"]}}

        chat_prompt_template = build_standard_chat_prompt_template(input_)

        pipeline = chat_prompt_template | llm | StrOutputParser()

        return cls(pipeline=pipeline)

    def _run(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)

        args = input.get("input", input)

        query = args['user_query']
        course_requirement = args.get('course_requirement', "")

        result = self.pipeline.invoke({"user_query": query,
                                       "course_requirement": course_requirement,
                                       'knowledge_gaps': knowledge_gaps})
        return result

    async def _arun(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        knowledge_gaps = "\n".join(runtime.context.knowledge_gaps)

        args = input.get("input", input)

        query = args['user_query']
        course_requirement = args.get('course_requirement', "")

        result = await self.pipeline.ainvoke({"user_query": query,
                                              "course_requirement": course_requirement,
                                              'knowledge_gaps': knowledge_gaps})
        return result
