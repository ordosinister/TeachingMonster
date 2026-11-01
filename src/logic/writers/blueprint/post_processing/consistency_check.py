"""Consistency check for enterprise training blueprint slides."""

import json
import logging
import os
from textwrap import dedent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blueprint.consistency")

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser

from model_orchestration import get_model_config
from src.logic import build_standard_chat_prompt_template
from src.logic.writers.blueprint.structured_output import LessonBlueprint, StudentProfileInterpretation

CONSISTENCY_SYSTEM_PROMPT = dedent("""\
# Goal
Audit enterprise training slides for internal consistency, requirement coverage, and residual cultural assumptions that the background pipeline missed.

# Role
You are an enterprise training material consistency auditor. You catch contradictions, coverage gaps, and unadapted source-culture assumptions before delivery.

# Inputs
- <SLIDES>: full slide sequence with titles, content, speaker notes, and transitions
- <COURSE_REQUIREMENT>: the original topic, learning goals, and key points
- <STUDENT_PERSONA>: target audience description (region, background, role)
- <BACKGROUND_ADAPTATIONS>: teaching adjustments already identified by the background pipeline

# Rules
- Flag contradictions: two slides asserting mutually exclusive facts, policies, or definitions.
- Flag coverage gaps: any key point from COURSE_REQUIREMENT with zero or only implicit coverage.
- Flag cultural residues: examples, idioms, brand names, regulatory references, or workflow steps that assume the source region context without explanation for the target audience.
- Do NOT flag background-adapted topics as residue unless they still contain unexplained source-culture assumptions.

# Constraints
- Never audit mathematical correctness, formula derivation, or scientific facts. Enterprise training has no universal STEM truths.
- Never propose removing content to fix a gap; propose an additional slide or expansion.
- Cultural residue only when the target audience would be confused, not merely when wording is unfamiliar.

# Output
# ConsistencyCheck

Slide <N>: Issue -- <one-sentence description>
...

Coverage Gaps: <comma-separated missing topics, or "None">
Cultural Residues: <comma-separated unadapted assumptions, or "None">
Overall Verdict: <Pass / Needs Minor Fixes / Needs Major Rework>
""")

CONSISTENCY_MERGE_PROMPT = dedent("""\
# Goal
Merge consistency audit corrections into the existing slide draft, preserving structure and filling identified gaps.

# Role
You are a slide content merger and gap-filler for enterprise training materials.

# Inputs
- <DRAFT>: current LessonBlueprint JSON
- <CONSISTENCY_AUDIT>: the auditor findings
- <COURSE_REQUIREMENT>: the original topic, learning goals, and key points

# Rules
- Apply each fix to its corresponding slide. For coverage gaps, insert new slides or expand existing ones.
- Preserve all slide fields (title, content, speaker_notes, transition_to_next).
- If a cultural residue is flagged, add a brief bridging sentence or footnote to make the reference accessible.

# Constraints
- Output must be valid JSON matching the LessonBlueprint schema.
- If a fix conflicts with the course requirement, prioritize the course requirement.

# Output
Format instruction: {format_instructions}
""")


def run_consistency_check(slide_output: LessonBlueprint, course_requirement: str,
                          pedagogical_state: StudentProfileInterpretation, target_dir: str,
                          env: str, output_filename: str) -> LessonBlueprint:
    """Run consistency audit and merge corrections into slides.

    Args:
        slide_output: The current LessonBlueprint slide output.
        course_requirement: The original course requirement string.
        pedagogical_state: StudentProfileInterpretation from the background pipeline.
        target_dir: Directory to save audit artifacts.
        env: Environment key for MODEL_CONFIGURATIONS.
        output_filename: Path to save the final JSON output.

    Returns:
        Updated LessonBlueprint with consistency corrections applied.
    """
    logger.info("Running enterprise training consistency check...")

    slide_text = "\n\n".join([
        f"Slide {s.slide_number}: {s.slide_title}\n"
        f"Content: {' | '.join(s.slide_content)}\n"
        f"Notes: {s.speaker_notes}\n"
        f"Transition: {s.transition_to_next}"
        for s in slide_output.slides
    ])

    audit_input = {
        "system": {"template": CONSISTENCY_SYSTEM_PROMPT},
        "human": {
            "template": dedent("""\
                <SLIDES>:
                {slides}

                <COURSE_REQUIREMENT>:
                {course_requirement}

                <STUDENT_PERSONA>:
                {persona}

                <BACKGROUND_ADAPTATIONS?:
                {adaptations}
            """),
            "input_variable": ["slides", "course_requirement", "persona", "adaptations"]
        }
    }

    audit_pipeline = (
        build_standard_chat_prompt_template(audit_input)
        | get_model_config(env)['master']
        | StrOutputParser()
    )

    audit_result = audit_pipeline.invoke({
        "slides": slide_text,
        "course_requirement": course_requirement,
        "persona": str(pedagogical_state),
        "adaptations": "\n".join(pedagogical_state.teaching_adjustments)
    })

    logger.info(f"Consistency audit result: {audit_result[:200]}...")

    audit_dir = os.path.join(target_dir, "consistency_check")
    if not os.path.isdir(audit_dir):
        os.makedirs(audit_dir)
    with open(os.path.join(audit_dir, "audit.txt"), "w", encoding="utf-8") as f2:
        f2.write(audit_result)
    logger.info("Consistency audit saved to consistency_check/audit.txt")

    logger.info("Final merging consistency corrections...")

    output_parser = PydanticOutputParser(pydantic_object=LessonBlueprint)
    format_instructions = output_parser.get_format_instructions()

    merge_input = {
        "system": {"template": CONSISTENCY_MERGE_PROMPT,
                   "partial_variables": {'format_instructions': format_instructions}},
        "human": {
            "template": dedent("""\
                Fix all consistency issues in 
                
                <DRAFT>: {draft} 
                
                with

                <CONSISTENCY_AUDIT>: {audit}

                <COURSE_REQUIREMENT>: {course_requirement}
            """)
        }
    }

    model_sub = get_model_config(env)['sub']
    merge_pipeline = build_standard_chat_prompt_template(merge_input) | model_sub | output_parser

    while True:
        try:
            slide_output = merge_pipeline.invoke({
                "draft": slide_output.model_dump_json(),
                "audit": audit_result,
                "course_requirement": course_requirement
            })
            break
        except OutputParserException:
            pass

    logger.info(f"Save the script to filename: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as f2:
        json.dump(slide_output.model_dump(), f2, ensure_ascii=False, indent=2)

    return slide_output
