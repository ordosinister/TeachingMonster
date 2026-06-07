from textwrap import dedent
from typing import Literal, Union

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.logic import build_standard_chat_prompt_template


class GeneralImage(BaseModel):
    name: Literal["general"] = "general"
    image_prompt: str = Field(
        description="Use for conceptual, artistic, or illustrative visualizations (analogies, real-world examples, conceptual flows) that aid intuition and cannot be represented by a plot.")


class MatplotlibImage(BaseModel):
    name: Literal["matplotlib"] = "matplotlib"
    image_prompt: str = Field(
        description="Use for precise technical visualizations where the exact relationship between variables is the primary teaching point (function plots, data charts, geometric proofs).")


class Output(BaseModel):
    reasoning: str = Field(
        description="Explanation of why an image is unnecessary (e.g., textual sufficiency, pure symbolic logic, or avoiding cognitive overload).")
    image_selection: Union[GeneralImage, MatplotlibImage, None] = Field(
        description="The chosen image type if necessary, otherwise None.")

SYSTEM_PROMPT = dedent("""
# ROLE
Instructional designer with extensive experience designing AP-level slide-based presentations. Every visual must exceptionally illuminate the concept and optimize the student's learning experience, calibrated to <STUDENT PERSONA>.

# INPUTS
- <Slide Content>: this slide's bullets and text
- <Speaker Note>: teacher's spoken narration -- primary signal for where comprehension friction occurs
- <Context>: all slides in the deck -- avoid redundancy; defer the visual to a later slide if that slide covers it better
- <Slide Type>: base | puzzle | concept_check | algorithm
- <STUDENT PERSONA>: grade, focus time, background knowledge

# GOAL
Optimize the student's learning experience. Decide if a visualization is necessary, pick the right type, and generate a precise prompt calibrated to <STUDENT PERSONA>.

# TASK
1. Check <Speaker Note> for friction points.
2. Scan <Context> for obvious redundancy or better placement.
3. Use <STUDENT PERSONA> to decide if text-only suffices.
4. Choose exactly one:
   - GeneralImage
   - MatplotlibImage
   - None
5. Generate a concise, implementation-oriented prompt.

# IMAGE TYPES

GeneralImage -- metaphors, analogies, real-world examples, conceptual flows, intuition-building visuals, qualitative mental models.

Use GeneralImage for:
- intuition
- storytelling
- conceptual understanding
- curiosity-building
- qualitative explanation

GeneralImage should:
- focus on one core idea
- minimize clutter
- use concrete and memorable visuals
- prioritize intuition over precision

Avoid GeneralImage for rigorous STEM geometry or exact spatial relationships.

--------------------------------------------------

MatplotlibImage -- use for any visual requiring mathematical or spatial precision:
- geometry
- vectors
- forces
- motion
- coordinate systems
- graphs
- ray diagrams
- circuits
- proportional relationships
- geometric proofs
- technical STEM diagrams

Use MatplotlibImage whenever incorrect geometry could teach the wrong concept.

These visuals must:
- preserve exact spatial relationships
- include all numerical values/constants from the slide; if the slide is purely algebraic, infer reasonable example values from the context (grade level, typical textbook examples) and state them explicitly -- a prompt without concrete values is incomplete
- use clear labels and annotations
- prioritize instructional clarity over artistic style
- avoid decorative imagery
- use equal aspect ratio when geometry matters
- explicitly show vector directions and reference points when relevant

For graphs:
- label axes clearly
- include units when relevant
- highlight the important feature
- avoid unnecessary clutter

For vector diagrams (physics, mathematics):
- When drawing the vector difference Δv = v₂ − v₁:
  1. Place v₁ and v₂ tail-to-tail at the same origin.
  2. Draw Δv as an arrow FROM the tip of v₁ TO the tip of v₂.
  3. Label Δv explicitly and use a distinct color or line style to separate it from v₁ and v₂.
  4. If needed for clarity, redraw Δv with its own tail at a separate origin -- the direction and magnitude must match the original construction exactly.
- If a single plot becomes too cluttered, use subplots to separate conceptual steps while maintaining visual consistency.

MatplotlibImage prompts should read like deterministic plotting instructions for another agent generating matplotlib code, not like artistic image prompts.

--------------------------------------------------

None -- use when:
- text is already self-sufficient
- the image would clutter cognition
- the visual adds little instructional value
- <Context> shows a nearby slide already handling the visualization better

# VISUAL DECISION RULES

Any slide containing vectors, forces, geometric constructions, ray paths, coordinate systems, or proportional diagrams MUST use MatplotlibImage -- regardless of whether the slide is narrative, conceptual, or derivation-style.

If the correctness of the visual depends on geometry or spatial relationships, always prefer MatplotlibImage over GeneralImage.

If the slide primarily needs intuition or emotional engagement, prefer GeneralImage.

If the visual would be redundant or low-value, return None.

# SLIDE TYPE STRATEGY

- base: standard logic. Skip if <Context> shows a prior slide already illustrated this angle.
- puzzle: prefer curiosity-building GeneralImage hints without revealing the answer.
- concept_check: strongly prefer None. Add visuals only if comprehension would otherwise fail.
- algorithm: prefer sequential process visuals. Skip if <Context> already shows the process.

# PERSONA CALIBRATION

- Lower grade -> simpler visuals, fewer simultaneous elements
- Higher grade -> denser abstraction acceptable
- Short focus time -> one focal point per visual
- Background gaps -> add bridging visuals when needed

# OUTPUT REQUIREMENTS

- Be concise.
- Prefer fast heuristic decisions over extensive deliberation.
- MatplotlibImage prompts must be implementation-oriented and directly usable by another agent generating matplotlib code.
- Do not generate artistic/cinematic language for MatplotlibImage.
""")


def create_image_prompt_pipeline(model):

    output_parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = output_parser.get_format_instructions()

    input_ = {"system": {"template": SYSTEM_PROMPT},
              "human": {
                  "template": dedent("""
                  <Context>: {context}
                  
                  <Slide Type>: {slide_type}
                  
                  <Slide Content>: {slide_content}
                  
                  <Speaker Note>: {speaker_notes}

                  <STUDENT PERSONA>: {student_persona}
                
                  Structured Output Instruction: {format_instructions}
                  """),

                  "input_variable": ["slide_content", "speaker_notes", "context", 'slide_type', "student_persona"],
                  "partial_variables": {'format_instructions': format_instructions}}}

    chat_prompt_template = build_standard_chat_prompt_template(input_)

    pipeline = chat_prompt_template | model | output_parser

    return pipeline