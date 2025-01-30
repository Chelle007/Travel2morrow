from constants import RESPONSE_MAPPING
from conversation_states import ConversationState
from user_data import user_variables

def get_message_for_state(state: ConversationState, user_id: int) -> str:
    messages = {
        ConversationState.START: "Hi! Welcome to Travel2morrow. How can I assist you today?",
        ConversationState.DEFAULT_ANSWER: "Would you like to use previous answers?",
        ConversationState.WHO_TRAVELLING: "Who's travelling?",
        ConversationState.TRIP_TYPE: "Single trip or annual?",
        ConversationState.DESTINATION: "Which country are you going to?",
        ConversationState.TRAVEL_DATE: "Which date are you going?",
        ConversationState.DURATION: "How many days are you going?",
        ConversationState.ADVENTURE_ACTIVITIES: "Do you need extra protection for adventure or risky activities/sports?",
        ConversationState.ADVENTURE_DETAILS: "Which activities are you participating in?",
        ConversationState.MEDICAL_CONDITIONS: "Do you have any pre-existing medical conditions?",
        ConversationState.MEDICAL_DETAILS: "Please specify if you'd like additional support for your condition:",
        ConversationState.BUDGET: "Do you have a budget in mind?",
        ConversationState.RECOMMENDATION: "Based on your preferences, here's our recommendation:",
        ConversationState.ADDITIONAL_COVERAGE: "Would you like to customize your plan with additional coverage for trip interruption, lost luggage, or delays?",
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
                ConversationState.ADDITIONAL_COVERAGE: "Additional coverage"
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
