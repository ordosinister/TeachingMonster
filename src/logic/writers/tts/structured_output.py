from pydantic import BaseModel, Field

class Vibe(BaseModel):
 inferred_level: str = Field(..., description="Estimated academic level")
 prior_knowledge: List[str] = Field(..., description="What the student likely already knows")
 knowledge_gaps: List[str] = Field(..., description="Potential gaps to scaffold around")
 teaching_adjustments: List[str] = Field(..., description="How explanations will be adapted")