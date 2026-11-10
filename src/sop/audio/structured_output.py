from typing import List

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class TTSScript(BaseModel):
    page: int = Field(description="The page number of this script")
    script: str = Field(description="tts script")


class TTSScripts(BaseModel):

    scripts: List[TTSScript] = Field(description="Speaker's note to each of the image.")