"""Versioned records for the first vertical slice; no service-specific extraction."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[1] = 1


class Message(Record):
    id: str
    owner_id: str
    conversation_id: str
    request_id: str
    role: Literal['user', 'assistant']
    content: str
    created_at: datetime
    status: Literal['saved', 'generating', 'complete', 'failed']
    provider: str | None = None
    model: str | None = None


class Source(Record):
    message_id: str
    conversation_id: str
    managed_event_id: str
    evidence_type: Literal['user_statement', 'user_correction']
    attribution_method: Literal['managed_event_reference', 'application_verified']


class MemoryProjection(Record):
    id: str
    owner_id: str
    managed_memory_id: str
    managed_updated_at: datetime
    text: str
    category: Literal['about_me', 'people', 'interests', 'experiences', 'current_life']
    status: Literal['pending', 'active', 'superseded', 'removal_pending', 'deleted']
    sources: list[Source]
    created_at: datetime
    updated_at: datetime
    revision: int = Field(ge=1)
    embedding_model: str
    embedding_dimensions: int = Field(gt=0)

    @model_validator(mode='after')
    def active_requires_provenance(self):
        if self.status == 'active' and not self.sources:
            raise ValueError('Active memories require attributable sources')
        return self


class SynchronizationTask(Record):
    id: str
    owner_id: str
    conversation_id: str
    message_ids: list[str]
    delivery: Literal['queued', 'sending', 'uncertain', 'confirmed', 'failed']
    extraction: Literal['pending', 'observed', 'complete', 'failed']
    projection: Literal['pending', 'ready', 'quarantined', 'failed']
    attempts: int = Field(default=0, ge=0)
    last_error_code: str | None = None
    next_attempt_at: datetime | None = None
    managed_event_ids: dict[str, str] = Field(default_factory=dict)


def eligible(memory: MemoryProjection, owner_id: str, current_revision: int) -> bool:
    """Final eligibility check in addition to pre-ranking owner/status filters."""
    return (memory.owner_id == owner_id and memory.status == 'active'
            and bool(memory.sources) and memory.revision == current_revision)
