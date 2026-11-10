"""Slide content generation entry point."""
import logging

from langchain_core.exceptions import OutputParserException

from poc.slide_content.models import LessonBlueprint
from poc.slide_content.pipeline import create_slide_content_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("slide_content")


def generate_slide_content(model, user_input, max_retries=2):
    """Generate a 4-slide LessonBlueprint from user input."""
    pipeline = create_slide_content_pipeline(model)
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = pipeline.invoke({"input": user_input})
            logger.info("Slide content generated successfully (%d slides)", len(result.slides))
            return result
        except OutputParserException as exc:
            last_error = exc
            logger.warning(
                "Slide content parsing failed (attempt %d/%d): %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )

    raise RuntimeError(
        f"Failed to generate slide content after {max_retries + 1} attempts: {last_error}"
    )