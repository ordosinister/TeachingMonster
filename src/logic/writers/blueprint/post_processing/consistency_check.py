import json
import logging
import os

from langchain_core.exceptions import OutputParserException

from src.logic.writers.blueprint.post_processing.generation_pipeline import create_audit_pipeline, create_merge_pipeline
from src.logic.writers.blueprint.structured_output import LessonBlueprint, StudentProfileInterpretation


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blueprint.consistency")


def run_consistency_check(slide_output: LessonBlueprint, course_requirement: str,
                          pedagogical_state: StudentProfileInterpretation, target_dir: str,
                          env: str, output_filename: str) -> LessonBlueprint:
    """Run consistency audit and merge corrections into slides.

    Args:
        slide_output: The current LessonBlueprint image output.
        course_requirement: The original course requirement string.
        pedagogical_state: StudentProfileInterpretation from the background pipeline.
        target_dir: Directory to save audit artifacts.
        env: Environment key for MODEL_CONFIGURATIONS.
        output_filename: Path to save the final JSON output.

    Returns:
        Updated LessonBlueprint with consistency corrections applied.
    """
    logger.info("Running enterprise training consistency check...")

    audit_pipeline = create_audit_pipeline(env)

    slide_text = "\n\n".join([
        f"Slide {s.slide_number}: {s.slide_title}\n"
        f"Content: {' | '.join(s.slide_content)}\n"
        f"Notes: {s.speaker_notes}\n"
        f"Transition: {s.transition_to_next}"
        for s in slide_output.slides
    ])

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

    merge_pipeline = create_merge_pipeline(env)

    while True:
        try:
            slide_output = merge_pipeline.invoke({
                "draft": slide_output.model_dump_json(),
                "audit": audit_result,
                "course_requirement": course_requirement,
                "persona": str(pedagogical_state),
            })
            break
        except OutputParserException:
            pass

    logger.info(f"Save the script to filename: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as f2:
        json.dump(slide_output.model_dump(), f2, ensure_ascii=False, indent=2)

    return slide_output
