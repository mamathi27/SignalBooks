
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_paise: float
    latency_ms: int
    fallback_used: bool
