from constants import RESPONSE_MAPPING
from conversation_states import ConversationState
from user_data import user_variables

def get_message_for_state(state: ConversationState, user_id: int) -> str:
    messages = {
        ConversationState.START: "Hi! Welcome to Travel2morrow. How can I assist you today?",
        ConversationState.DEFAULT_ANSWER: "Would you like to use previous answers?",
        ConversationState.WHO_TRAVELLING: "Who's travelling?",
        ConversationState.AGE_GROUP: "What is your age group?",
        ConversationState.TRIP_TYPE: "Would you like to purchase a single-trip or an annual plan?\nA single-trip plan provides coverage for this trip only, while an annual plan covers multiple trips throughout the year-so you won't need to buy insurance every time you travel.",
        ConversationState.DESTINATION: "Which country are you traveling to? 🌏",
        ConversationState.DEPARTURE_DATE: "What is your departure date?\n(Please provide your departure date in the format: [YYYY-MM-DD])",
        ConversationState.RETURN_DATE: "What is your return date?\n(Please provide your departure date in the format: [YYYY-MM-DD])",
        ConversationState.ADVENTURE_ACTIVITIES: "Will you be participating in adventure or high-risk activities?",
        ConversationState.ADVENTURE_DETAILS: "Which adventure activities will you be doing during your trip?\n\nFor example:\n- Scuba diving\n- Snorkeling\n- Hiking\n- Skiing or snowboarding\n- Skydiving\n- Parasailing\n- Cycling\n- Trekking",
        ConversationState.MEDICAL_CONDITIONS: "Do you have any pre-existing medical conditions?",
        ConversationState.MEDICAL_DETAILS: "Please share the details of your condition so we can tailor the best coverage for you.\n(For example: asthma, diabetes, heart disease)",
        ConversationState.BUDGET: "What is your budget for travel insurance?",
        ConversationState.RECOMMENDATION: "Based on your preferences, here's our recommendation:",
        ConversationState.QUESTIONS: "Do you have any questions about your recommended plan?",
        ConversationState.MANAGE_INSURANCE: "Please select an option:",
        ConversationState.LEARN_MORE: "Working on it..."
    }
    
    base_message = messages.get(state, "How can I help you?")
    
    # If we're at DEFAULT_ANSWER state and there are saved responses, show them
    if state == ConversationState.DEFAULT_ANSWER:
        saved_response_lines = []
        saved_responses = user_variables.get(user_id, {}).get('saved_responses', {})
        
        if saved_responses:
            labels_map = {
                ConversationState.WHO_TRAVELLING: "Who's travelling",
                ConversationState.TRIP_TYPE: "Trip type",
                ConversationState.ADVENTURE_ACTIVITIES: "Adventure activities",
                ConversationState.ADVENTURE_DETAILS: "Adventure details",
                ConversationState.MEDICAL_CONDITIONS: "Medical conditions",
                ConversationState.MEDICAL_DETAILS: "Medical details",
                ConversationState.BUDGET: "Budget",
            }
            
            for state_key, label in labels_map.items():
                if state_key in saved_responses:
                    value = saved_responses[state_key]
                    # Convert the value to a readable format using RESPONSE_MAPPING if available
                    display_value = RESPONSE_MAPPING.get(value, value)
                    saved_response_lines.append(f"{label}: {display_value}")
            
            if saved_response_lines:
                return "\n".join(saved_response_lines) + "\n\n" + base_message
    
    return base_message
