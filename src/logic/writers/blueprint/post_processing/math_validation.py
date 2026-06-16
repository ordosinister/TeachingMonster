"""Math verification and correction merge for blueprint slides."""

import logging
import os
from textwrap import dedent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blueprint.math")

from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser

from model_orchestration import get_model_config
from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.agent.mathematic_coder_v2 import SYSTEM_PROMPT as MATH_SYSTEM_PROMPT
from src.logic.writers.blueprint.structured_output import LessonBlueprint

MATH_MERGE_PROMPT = dedent("""\
# ROLE
Merge verified mathematical corrections into slide content. Replace incorrect values and formulas with the audit-verified corrections.
 Preserve all non-math content, slide structure, and speaker notes unchanged.
 
 # INPUTS
 - DRAFT: current slide content
 - MATH_VALID: math audit output with verified corrections
 
 # TASK
 For each correction flagged in MATH_VALID, replace the incorrect math in DRAFT with the verified correct version. 
 Only change what is flagged. Never alter slide count, ordering, or non-math text.
 
 # OUTPUT
 LessonBlueprint JSON with all math corrections applied.
 """)


def run_math_validation(slide_output, target_dir, env: str):
    """Run math audit and merge verified corrections into slides.

    Args:
        slide_output: The current LessonBlueprint slide output.
        target_dir: Directory to save math audit file.

    Returns:
        Updated LessonBlueprint with math corrections applied.
    """
    logger.info("Running final math verification...")
    math_query = "\n\n".join([str(s.model_dump()) for s in slide_output.slides])

    math_input = {
        "system": {"template": MATH_SYSTEM_PROMPT},
        "human": {"template": "SLIDES: {user_query}", "input_variable": ["user_query"]}
    }

    model_main = get_model_config(env)['main']
    model_sub = get_model_config(env)['sub']

    math_pipeline = build_standard_chat_prompt_template(math_input) | model_main | StrOutputParser()
    math_llm_output = math_pipeline.invoke({"user_query": math_query})

    import io
    from contextlib import redirect_stdout

    stdout_capture = io.StringIO()
    try:
        with redirect_stdout(stdout_capture):
            exec(math_llm_output, {"__builtins__": __builtins__})
        raw_output = stdout_capture.getvalue()
    except Exception as e:
        raw_output = f"EXECUTION ERROR: {str(e)}"


    math_dir = os.path.join(target_dir, "mathematic_coder_v2")
    if not os.path.isdir(math_dir):
        os.makedirs(math_dir)
    with open(os.path.join(math_dir, "final_audit.txt"), "w", encoding="utf-8") as f:
        f.write(math_llm_output)
    logger.info("Math audit saved to mathematic_coder_v2/final_audit.txt")

    logger.info("Final merging...")

    output_parser = PydanticOutputParser(pydantic_object=LessonBlueprint)
    format_instructions = output_parser.get_format_instructions()

    merge_input = {
        "system": {"template": MATH_MERGE_PROMPT},
        "human": {"template": dedent("""\
        Fix all the mathematics computation in {draft} with 
        
        Mathematically verified results:
        {math_valid}
        
        Output instruction = {format_instructions}                             
        """),
        "input_variable": ["draft", "math_valid"],
        "partial_variables": {'format_instructions': format_instructions}
        }
    }

    merge_pipeline = build_standard_chat_prompt_template(merge_input) | model_sub | output_parser

    while True:
        try:
            slide_output = merge_pipeline.invoke({"draft": slide_output.model_dump_json(),
                                                  "math_valid": raw_output})
            break
        except Exception as e:
            print(f"Math Validation Merge Failed: {e}")

    return slide_output
