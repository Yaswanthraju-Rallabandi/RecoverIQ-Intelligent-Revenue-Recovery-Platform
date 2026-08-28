from enum import Enum
from typing import Dict, NamedTuple

class ActionType(str, Enum):
    RETRY_NOW = "retry_now"
    RETRY_LATER = "retry_later"
    RECOVERY_LINK = "recovery_link"
    UNRECOVERABLE = "unrecoverable"
    MANUAL_REVIEW = "manual_review"

class ActionDefinition(NamedTuple):
    action_type: ActionType
    label: str
    description: str
    base_cost: float # In INR
    cooldown_minutes: int

# Operational Action Definitions and Cost Matrix
ACTION_REGISTRY: Dict[ActionType, ActionDefinition] = {
    ActionType.RETRY_NOW: ActionDefinition(
        action_type=ActionType.RETRY_NOW,
        label="Immediate Switch Retry",
        description="Instant re-authorization request via gateway switch without customer involvement.",
        base_cost=0.50, # Nominal gateway interchange API cost
        cooldown_minutes=0
    ),
    ActionType.RETRY_LATER: ActionDefinition(
        action_type=ActionType.RETRY_LATER,
        label="Retry after 15 minutes",
        description="Delayed re-attempt with exponential backoff after network switch congestion clears.",
        base_cost=2.00, # Processing cost + delay latency cost
        cooldown_minutes=15
    ),
    ActionType.RECOVERY_LINK: ActionDefinition(
        action_type=ActionType.RECOVERY_LINK,
        label="Send WhatsApp & SMS Smart Link",
        description="Dispatches 1-click Razorpay recovery link directly to customer device via WhatsApp/SMS.",
        base_cost=5.00, # Customer friction penalty + SMS/WhatsApp API gateway cost
        cooldown_minutes=5
    ),
    ActionType.UNRECOVERABLE: ActionDefinition(
        action_type=ActionType.UNRECOVERABLE,
        label="Mark as Unrecoverable (Give Up)",
        description="Hard stop. Transaction cannot be salvaged; close order to prevent further cost.",
        base_cost=0.00,
        cooldown_minutes=0
    ),
    ActionType.MANUAL_REVIEW: ActionDefinition(
        action_type=ActionType.MANUAL_REVIEW,
        label="Escalate for Manual Review",
        description="Guardrail blocked automatic execution or high-value constraint triggered. Requires merchant sign-off.",
        base_cost=10.00, # Operational review cost
        cooldown_minutes=0
    )
}