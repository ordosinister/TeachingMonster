from typing import Literal, Union

from pydantic import BaseModel, Field


class GeneralImage(BaseModel):
    name: Literal["general"] = "general"
    image_prompt: str = Field(
        description="Natural-language textual description (never code). Use for conceptual, artistic, or illustrative visualizations (analogies, real-world examples, conceptual flows, well-defined classical setups like pendulum, inclined plane, lever, or Bohr model) that aid intuition and do not require precise numerical coordinates.")


class MatplotlibImage(BaseModel):
    name: Literal["matplotlib"] = "matplotlib"
    image_prompt: str = Field(
        description="Natural-language textual description (NEVER Python/matplotlib code). Use for visuals requiring precise numerical coordinates or specified equations: histograms with specific numbers, objects moving in 2D space with given equations, functions with specified equations, geometric proofs with concrete values.")


class Output(BaseModel):
    reasoning: str = Field(
        description="Explanation of why an image is unnecessary (e.g., textual sufficiency, pure symbolic logic, or avoiding cognitive overload).")
    image_selection: Union[GeneralImage, MatplotlibImage, None] = Field(
        description="The chosen image type if necessary, otherwise None.")