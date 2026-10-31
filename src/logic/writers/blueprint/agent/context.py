from typing import List

from pydantic import BaseModel, Field

class AgentContext(BaseModel):
    request_id: str
    cache_key: str
    knowledge_gaps: List[str] = Field(..., description="Gaps blocking understanding")
    teaching_adjustments: List[str] = Field(..., description="Strategies to bridge gaps")