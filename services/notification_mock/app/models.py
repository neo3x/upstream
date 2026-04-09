"""
Pydantic models for the Notification mock service.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class NotificationType(str, Enum):
    TEAM_ALERT = "team_alert"
    REPORTER_UPDATE = "reporter_update"
    SECURITY_ALERT = "security_alert"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: f"NOTIF-{uuid4().hex[:8].upper()}")
    type: NotificationType
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    related_ticket_id: Optional[str] = None
    related_incident_id: Optional[str] = None
    sent_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationCreate(BaseModel):
    type: NotificationType
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    related_ticket_id: Optional[str] = None
    related_incident_id: Optional[str] = None
