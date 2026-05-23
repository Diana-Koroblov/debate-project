"""Pydantic data contracts for IPC communication."""

from __future__ import annotations

from enum import Enum
from typing import List, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class MessageType(str, Enum):
    """Enumeration of all supported IPC message types."""
    ARGUMENT = "argument"
    TURN_PROMPT = "turn_prompt"
    FINAL_JUDGMENT = "final_judgment"
    TELEMETRY = "telemetry"
    HEARTBEAT = "heartbeat"


class Citation(BaseModel):
    """Source reference for agent arguments."""
    title: str
    url: str


class ArgumentPayload(BaseModel):
    """Structured content for a debate turn."""
    text: str
    search_queries: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)


class ChildToParentMessage(BaseModel):
    """Payload sent from a debater agent to the orchestrator."""
    type: Literal[MessageType.ARGUMENT] = MessageType.ARGUMENT
    agent_id: str
    round_number: int
    payload: ArgumentPayload


class ParentToChildRouter(BaseModel):
    """Payload sent from the orchestrator to a debater agent."""
    type: Literal[MessageType.TURN_PROMPT] = MessageType.TURN_PROMPT
    recipient_id: str
    history: List[str] = Field(default_factory=list)
    game_status: Literal["ACTIVE", "ENDING"]


class JudgmentJustification(BaseModel):
    """Granular justification point for the final judgment."""
    point: str
    evidence: str


class FinalJudgmentSchema(BaseModel):
    """Payload representing the final debate outcome."""
    type: Literal[MessageType.FINAL_JUDGMENT] = MessageType.FINAL_JUDGMENT
    winner_id: str
    differential_score: float
    justification: List[JudgmentJustification]


class TokenUsage(BaseModel):
    """Specific token metrics."""
    input: int
    output: int


class TokenTelemetry(BaseModel):
    """Standardized metric packet for the Token Economy tracking."""
    type: Literal[MessageType.TELEMETRY] = MessageType.TELEMETRY
    agent_id: str
    model: str
    usage: TokenUsage
    latency_ms: float
    timestamp: str


class HeartbeatMessage(BaseModel):
    """Standardized heartbeat signal for health monitoring."""
    type: Literal[MessageType.HEARTBEAT] = MessageType.HEARTBEAT
    agent_id: str
    timestamp: str


# Discriminated Union for all messages
AnyMessage = Union[
    ChildToParentMessage,
    ParentToChildRouter,
    FinalJudgmentSchema,
    TokenTelemetry,
    HeartbeatMessage
]

# Type adapter for easy validation
MESSAGE_ADAPTER: TypeAdapter[AnyMessage] = TypeAdapter(AnyMessage)
