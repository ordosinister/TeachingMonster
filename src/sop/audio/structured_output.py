from typing import List

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class TTSScript(BaseModel):
    page: int = Field(description="The page number of this script")
    script: str = Field(description="tts script")


class TTSScripts(BaseModel):

    scripts: List[TTSScript] = Field(description="Speaker's note to each of the image.")

class CorrectedSegment(BaseModel):
    segment_index: int = Field(description='Segment index matching the original STT segment')
    start_time: float = Field(description='Start time in seconds from the original STT')
    end_time: float = Field(description='End time in seconds from the original STT')
    original_stt_text: str = Field(description='Original STT transcription text')
    corrected_text: str = Field(description='Corrected text aligned with ground truth script')
    is_aligned: bool = Field(description='Whether this segment could be confidently aligned with ground truth')
    correction_notes: str = Field(description='Brief explanation of what was corrected, merged, or why alignment failed')


class CorrectedSubtitles(BaseModel):
    slide_number: int = Field(description='The slide/page number')
    segments: List[CorrectedSegment] = Field(description='List of corrected subtitle segments with timestamps preserved from STT')

