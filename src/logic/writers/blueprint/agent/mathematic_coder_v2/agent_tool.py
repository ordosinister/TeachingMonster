import path
from contextlib import redirect_stdout
from textwrap import dedent

from langchain.tools import BaseTool, ToolRuntime
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field

from src.logic.writers.blueprint.agent.mathematic_coder_v2 import SYSTEM_PROMPT
from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.structured_output import StudentProfileInterpretation

MATHEMATIC_VALIDATION_PROMPT = dedent("""
# ROLE
Code auditor. Given a block of matplotlib code, identify every numerical computation that could be wrong and generate an independent verification script.

# TASK
1. Scan the code for all computed values: constants, formula results, coordinate positions, angle calculations, derived quantities.
2. For each value, write independent verification code that re-computes it from first principles using math/numpy/sympy.
3. Compare: print PASS if the value matches, FAIL with expected-vs-actual if it doesn"t.
4. Output ONLY the verification script -- no explanations, no markdown fences.

# RULES
- Use math, numpy, or sympy for precision.
- Handle division-by-zero and domain errors with try-except.
- Print results clearly: "PASS: <label> = <value>" or "FAIL: <label> expected <expected>, got <actual>".
- Code must be self-contained and runnable via exec().
- Do NOT generate plot/show commands -- only numerical validation.
""")

class Inputs(BaseModel):
    code: str = Field(description="The matplotlib code")


class MathTool(BaseTool):
    input_parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=Inputs)
    input_format_instructions: str = input_parser.get_format_instructions()

    name: str = "Math_verification_tool"
    description_template: str = dedent("""\
    Use this tool to verify all mathematical content in the latest slide draft: LaTeX formulas, numerical calculations, code snippets, datasets, and statistical claims.

    The tool reads the current draft, generates independent Python verification code, executes it, and returns corrections.

    input format instructions: {input_format_instructions}
    """)

    description: str = description_template.format(input_format_instructions=input_format_instructions)

    pipeline: Runnable
    validation_pipeline: Runnable
    # summarize_pipeline: Runnable

    @classmethod
    def create(cls, llm: Runnable):
        math_input = {
            "system": {"template": SYSTEM_PROMPT},
            "human": {
                "template": dedent("""
                    SLIDES: {user_query}
                """),
                "input_variable": ["user_query"]
            }
        }
        pipeline = build_standard_chat_prompt_template(math_input) | llm | StrOutputParser()

        validation_input = {
            "system": {"template": MATHEMATIC_VALIDATION_PROMPT},
            "human": {"template": "{code}", "input_variable": ["code"]}
        }
        validation_pipeline = build_standard_chat_prompt_template(validation_input) | llm | StrOutputParser()

        # summarize_input = {
        #     "system": {"template": SUMMARIZE_AUDIT_PROMPT},
        #     "human": {"template": "{report}", "input_variable": ["report"]}
        # }
        # summarize_pipeline = build_standard_chat_prompt_template(summarize_input) | llm | StrOutputParser()

        return cls(pipeline=pipeline, validation_pipeline=validation_pipeline,
                   # summarize_pipeline=summarize_pipeline
                   )

    def _run(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        args = input.get("input", input)
        code = args["code"]

        verification_script = self.validation_pipeline.invoke({"code": code})

        stdout_capture = path.StringIO()
        try:
            with redirect_stdout(stdout_capture):
                exec(verification_script, {"__builtins__": __builtins__})
            raw_output = stdout_capture.getvalue()
        except Exception as e:
            raw_output = f"EXECUTION ERROR: {str(e)}"

        return raw_output
        # summarized = self.summarize_pipeline.invoke({"report": raw_output})
        # return summarized

    async def _arun(self, runtime: ToolRuntime[StudentProfileInterpretation], **input):
        print(f"Running {self.name}...")
        args = input.get("input", input)
        code = args["code"]

        verification_script = await self.validation_pipeline.ainvoke({"code": code})

        stdout_capture = path.StringIO()
        try:
            with redirect_stdout(stdout_capture):
                exec(verification_script, {"__builtins__": __builtins__})
            raw_output = stdout_capture.getvalue()
        except Exception as e:
            raw_output = f"EXECUTION ERROR: {str(e)}"

        return raw_output
        # summarized = await self.summarize_pipeline.ainvoke({"report": raw_output})
        # return summarized


