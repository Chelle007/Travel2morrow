from telegram import ReplyKeyboardMarkup
from typing import Optional
from conversation_states import ConversationState

def get_keyboard_for_state(state: ConversationState) -> Optional[ReplyKeyboardMarkup]:
    keyboards = {
        ConversationState.START: [
            ["Explore travel insurance options"],
            ["Manage my existing travel insurance (View, modify, or file a claim)"],
            ["Learn more about Travel2morrow (Discover our services and benefits)"]
        ],
        ConversationState.DEFAULT_ANSWER: [
            ["Yes"],
            ["No"]
        ],
        ConversationState.WHO_TRAVELLING: [
            ["Solo"],
            ["Family"]
        ],
        ConversationState.AGE_GROUP: [
            ["Child (Under 18)"],
            ["Adult (18 - 64)"],
            ["Elderly (65 and above)"]
        ],
        ConversationState.TRIP_TYPE: [
            ["Single trip"],
            ["Annual"]
        ],
        ConversationState.ADVENTURE_ACTIVITIES: [
            ["Yes"],
            ["No"]
        ],
        ConversationState.MEDICAL_CONDITIONS: [
            ["Yes"],
            ["No"]
        ],
        ConversationState.BUDGET: [
            ["Under $50"],
            ["$50 - $100"],
            ["Above $100"]
        ],
        ConversationState.MANAGE_INSURANCE: [
            ["View existing policy details"],
            ["Update policy information"],
            ["File a claim"]
        ]
    }
    
    keyboard = keyboards.get(state, [])
    if state != ConversationState.START:
        keyboard.append(["◀️ Go Back"])
    
    return ReplyKeyboardMarkup(
        keyboard if keyboard else [[]], 
        resize_keyboard=True,
        one_time_keyboard=True  # Keyboard will hide after selection
    )
