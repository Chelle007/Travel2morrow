from telegram import ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from typing import Tuple, Optional
from conversation_states import ConversationState
from data_manager import UserDataManager
from db_utils import get_database_connection, get_user_saved_responses, save_user_responses
from keyboard_utils import get_keyboard_for_state
from message_utils import get_message_for_state
from response_formatter import format_user_responses

class StateTransitionManager:
    def __init__(self, user_data_manager: UserDataManager):
        self.user_data = user_data_manager
        
        # Define state transition rules
        self.transition_rules = {
            ConversationState.START: {
                'explore': self._handle_explore,
                'manage': lambda user_id, _: (ConversationState.MANAGE_INSURANCE, None),
                'learn': lambda user_id, _: (ConversationState.LEARN_MORE, None)
            },
            ConversationState.DEFAULT_ANSWER: {
                'default_yes': self._handle_default_yes,
                'default_no': self._handle_default_no
            }
        }
    
    async def handle_transition(
        self, 
        user_id: int, 
        action: str,
        context: CallbackContext
    ) -> Tuple[ConversationState, str, ReplyKeyboardMarkup]:
        """
        Main method to handle state transitions.
        Returns (next_state, message, keyboard)
        """
        current_state = self.user_data.get_state(user_id)
        
        if action == 'go_back':
            return await self._handle_go_back(user_id, current_state)
        
        state_handlers = self.transition_rules.get(current_state, {})
        handler = state_handlers.get(action)
        
        if handler:
            next_state, additional_data = await handler(user_id, context)
        else:
            next_state = await self._determine_next_state(current_state, action)
            self.user_data.set_response(user_id, current_state, action)
        
        if next_state == ConversationState.RECOMMENDATION:
            await self._handle_recommendation_state(user_id, context)
        
        self.user_data.set_state(user_id, next_state)
        message = self._get_state_message(next_state, user_id)
        keyboard = get_keyboard_for_state(next_state)
        
        return next_state, message, keyboard

    # TODO