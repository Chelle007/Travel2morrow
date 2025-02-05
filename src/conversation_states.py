from enum import Enum, auto

class ConversationState(Enum):
    START = auto()
    DEFAULT_ANSWER = auto()
    DESTINATION = auto()
    DEPARTURE_DATE = auto()
    RETURN_DATE = auto()
    WHO_TRAVELLING = auto()
    TRIP_TYPE = auto()
    ADVENTURE_ACTIVITIES = auto()
    ADVENTURE_DETAILS = auto()
    MEDICAL_CONDITIONS = auto()
    MEDICAL_DETAILS = auto()
    BUDGET = auto()
    RECOMMENDATION = auto()
    QUESTIONS = auto()
    MANAGE_INSURANCE = auto()
    LEARN_MORE = auto()
