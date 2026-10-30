"""Math verification and correction merge for blueprint slides."""
import path
import logging
import os
from contextlib import redirect_stdout
from textwrap import dedent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blueprint.math")

MATH_SYSTEM_PROMPT = dedent("""
# ROLE
Mathematical verification code generator. Scan slides for math/code content and produce a single executable Python script that independently recomputes every mathematical claim and prints results in a structured format.

# TASK
1. Scan all slides for mathematical content: LaTeX formulas, numerical calculations, computed values, derived quantities, code snippets, datasets, and statistical claims.
2. For each mathematical claim found, write independent Python verification code that recomputes it from first principles using math, numpy, or sympy.
3. Output ONE self-contained Python script that can be executed via exec().

# CRITICAL: NO HALLUCINATED VALUES
- You MUST only compute when EVERY parameter in a formula is concretely provided in the slides.
- If a slide states a symbolic relationship (e.g., ΔL = d·sinθ) but does NOT provide numerical values for d and θ, do NOT assign made-up numbers. Instead, print a SKIP line explaining why.
- If a slide says "for example, if d=2m and θ=30°" then those values ARE provided and you may compute.
- If a slide says "assume d=5, θ=45°" then those values ARE provided.
- If a slide only says "consider ΔL = d·sinθ" with no values whatsoever, you CANNOT assign values.
- Never invent, assume, or infer numerical values. They must be explicitly stated in the slide text.

# OUTPUT STRUCTURE
Output ONLY valid Python code — no markdown fences, no explanations, no commentary.

For each slide that contains mathematical content, structure the output exactly as follows:

print("================================")
print("SLIDE <N>")
print("<the original mathematical statement or formula being verified, quoted verbatim from the slide>")

# CHECK: are all required values concretely provided in the slide?
# If NO: print a SKIP line and move on.
# If YES: compute independently and compare.

For slides with sufficient concrete values:
print("PASS: <label> = <computed_value>")
# or
print("FAIL: <label> expected <computed_value>, got <original_value_from_slide>")

For slides where values are missing:
print("SKIP: <formula> — missing concrete values for: <list the missing parameters>")

Skip slides with zero mathematical content (no formulas, no numbers, no computations).

# CODING STANDARDS
- Use math, numpy, or sympy for precision.
- For each value, print a clear pass/fail line.
- Handle division-by-zero and domain errors with try-except, printing the error instead of crashing.
- Code must be self-contained and runnable via exec() in a restricted namespace.
- Do NOT generate plot/show commands or matplotlib imports — only numerical validation.
- Prefer exact symbolic comparison (sympy) for formula verification; numeric comparison with np.isclose for floating point.

# RULES
- Every mathematical claim in the slides must appear in the verification output — either SKIP (explaining why) or PASS/FAIL.
- If a slide has multiple formulas or computed values, verify each one separately under the same SLIDE header.
- Print the original statement BEFORE the computation so the captured output is self-documenting.
- No natural language explanations outside the print statements.
- The order of slides in the output must match the order in the input.
- NEVER fabricate numbers. A SKIP with a clear reason is correct behavior. A PASS/FAIL with invented data is a bug.

# OUTPUT FORMAT
Python code only, structured per-slide as shown above.
""")

from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser

from model_orchestration import get_model_config
from src.logic import build_standard_chat_prompt_template
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

    stdout_capture = path.StringIO()
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
