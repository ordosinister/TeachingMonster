"""Concept supervision and correction merge for blueprint slides."""

import json
import logging
from textwrap import dedent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blueprint.supervision")

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser

from model_orchestration import get_model_config
from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.structured_output import LessonBlueprint

SUPERVISION_SYSTEM_PROMPT = dedent("""\
# ROLE
STEM-field AP Lecturer with deep subject-matter expertise. Identify every factually incorrect statement in slide_content and speaker_notes -- conceptual errors, misattributed properties, wrong definitions, flawed causal chains, and inaccurate narratives. Provide the correct statement for each.

# INPUTS
- SLIDES: full slide content including slide_content and speaker_notes for every slide

# TASK
Scan every slide for incorrect statements. For each error found, output the slide number, the incorrect statement verbatim, and the correct version.

# RULES
- Only flag factual errors. Never flag style, pedagogy, or missing depth.
- Quote the incorrect statement verbatim. Provide the correction in equally concise language.
- Skip slides with no errors.
- If a correction requires domain-specific precision, provide it unapologetically.

# CHAIN OF THOUGHT
1. Read each slide''s slide_content and speaker_notes.
2. For each statement: verify against established domain knowledge.
3. If incorrect, note the slide number, quote the error, write the correction.

# OUTPUT FORMAT
# SupervisionTool
Slide <N>: incorrect statement | correct statement
...
No markdown, no commentary beyond the format above.
""")


SUPERVISION_MERGE_PROMPT = dedent("""\
# ROLE
Merge verified concept corrections into slide content and speaker notes. Replace incorrect statements with audit-verified corrections. Preserve slide structure, correct math, and unaffected text unchanged.

# INPUTS
- DRAFT: current slide content
- CONCEPT_VALID: supervision audit output with verified corrections (format: incorrect statement | correct statement)

# TASK
For each correction flagged in CONCEPT_VALID, replace the incorrect statement in DRAFT with the correct version. Apply to both slide_content and speaker_notes if the error appears in either. Only change what is flagged. Never alter slide count, ordering, or unaffected text.

# OUTPUT
LessonBlueprint JSON with all concept corrections applied.
""")


def run_concept_supervision(slide_output, env, output_filename):
    """Run concept supervision audit and merge verified corrections into slides.

    Args:
        slide_output: The current LessonBlueprint slide output.
        env: Environment key for MODEL_CONFIGURATIONS ("DEV" or "PROD").
        output_filename: Path to save the final JSON output.

    Returns:
        Updated LessonBlueprint with concept corrections applied.
    """
    math_query = "\n\n".join([str(s.model_dump()) for s in slide_output.slides])

    supervision_input = {
        "system": {"template": SUPERVISION_SYSTEM_PROMPT},
        "human": {"template": "SLIDES: {user_query}", "input_variable": ["user_query"]}
    }
    supervision_pipeline = build_standard_chat_prompt_template(supervision_input) | get_model_config(env)['master'] | StrOutputParser()
    supervision_llm_output = supervision_pipeline.invoke({"user_query": math_query})

    logger.info(f"Supervision Process Correction: {supervision_llm_output}")

    output_parser = PydanticOutputParser(pydantic_object=LessonBlueprint)
    format_instructions = output_parser.get_format_instructions()

    supervision_merge_input = {
        "system": {"template": SUPERVISION_MERGE_PROMPT},
        "human": {"template": dedent("""\
            Fix all the concept errors in {draft} with

            Concept verification results:
            {concept_valid}

            Output instruction = {format_instructions}
            """),
            "input_variable": ["draft", "concept_valid"],
            "partial_variables": {'format_instructions': format_instructions}
        }
    }

    model_sub = get_model_config(env)['sub']

    supervision_merge_pipeline = build_standard_chat_prompt_template(supervision_merge_input) | model_sub | output_parser

    while True:
        try:
            slide_output = supervision_merge_pipeline.invoke({"draft": slide_output.model_dump_json(),
                                                              "concept_valid": supervision_llm_output})
            break
        except OutputParserException:
            pass

    logger.info(f"Save the script to filename: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(slide_output.model_dump(), f, ensure_ascii=False, indent=2)

    return slide_output
