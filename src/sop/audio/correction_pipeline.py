from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, SystemMessagePromptTemplate
from langchain_core.runnables import Runnable

from src.sop.audio.structured_output import CorrectedSubtitles

CORRECTION_SYSTEM_PROMPT = """# Goal
Align STT (speech-to-text) output with the original Ground Truth script and produce corrected subtitle segments with accurate timestamps.

# Role
Senior subtitle alignment engineer. You compare Whisper STT segments against the known Ground Truth script, fix transcription errors (homophones, missed words, incorrect punctuation), and map corrected text back to the original timestamps.

# Inputs
- <GROUND_TRUTH_SCRIPT>: The exact script that was fed to TTS. This is the single source of truth.
- <STT_SEGMENTS>: Whisper output segments, each with start_time, end_time, and text.

# Rules
1. **Ground Truth is absolute**: corrected_text must match Ground Truth exactly. Do NOT paraphrase, add, or remove content.
2. **Timestamp preservation**:
   - One-to-one match: keep original segment timestamps.
   - One-to-many split (STT broke one Ground Truth sentence into multiple segments): merge those segments into a single CorrectedSegment using the first segment's start_time and the last segment's end_time.
   - Many-to-one merge (STT merged multiple Ground Truth sentences): try to split by semantics; if impossible, keep the merged timestamp and assign the full combined Ground Truth text.
   - Missing Ground Truth sentence (no matching STT): create a CorrectedSegment with is_aligned=False, start_time=-1.0, end_time=-1.0, and note "Ground truth sentence not found in STT".
3. **Correction scope**:
   - Fix homophone errors (e.g., de/ded/di, zai/zai, zuo/zuo)
   - Fix proper noun errors
   - Fix number/unit errors
   - Fix punctuation that causes wrong segmentation
4. **Output format**: Each CorrectedSegment must include segment_index, start_time, end_time, original_stt_text, corrected_text, is_aligned, correction_notes.
5. **Conservative principle**: If uncertain about alignment, mark is_aligned=False and explain in correction_notes. Never guess.

# Constraints
- Output must be valid JSON with no markdown or extra text.
- All strings in JSON must be properly escaped (backslashes doubled).
"""


def create_pipeline(model) -> Runnable:
    output_parser = PydanticOutputParser(pydantic_object=CorrectedSubtitles)
    format_instructions = output_parser.get_format_instructions()

    system_prompt = PromptTemplate(
        template=CORRECTION_SYSTEM_PROMPT,
        input_variables=[],
        partial_variables={"format_instructions": format_instructions}
    )

    system_message = SystemMessagePromptTemplate(prompt=system_prompt)

    chat_prompt_template = ChatPromptTemplate.from_messages(
        [system_message,
         ("human", "<GROUND_TRUTH_SCRIPT>: {ground_truth}\n\n<STT_SEGMENTS>: {stt_segments}")])

    pipeline = chat_prompt_template | model | output_parser
    return pipeline
