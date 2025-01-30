from enum import Enum, auto
from typing import Dict, Optional
from conversation_states import ConversationState

class UserDataManager:
    def __init__(self):
        self._user_data = {}
    
    def initialize_user(self, user_id: int, username: str = None):
        """Initialize or reset user data."""
        self._user_data[user_id] = {
            'state': ConversationState.START,
            'responses': {},
            'variables': {
                'chosen_default': False,
                'default_data_existed': False,
                'saved_responses': {},
                'username': username
            }
        }
        if username:
            self._user_data[user_id]['responses']['telegram_handle'] = f"@{username}"
    
    def get_state(self, user_id: int) -> ConversationState:
        """Get current conversation state for user."""
        return self._user_data.get(user_id, {}).get('state', ConversationState.START)
    
    def set_state(self, user_id: int, state: ConversationState):
        """Set conversation state for user."""
        if user_id in self._user_data:
            self._user_data[user_id]['state'] = state
    
    def get_responses(self, user_id: int) -> dict:
        """Get user's responses."""
        return self._user_data.get(user_id, {}).get('responses', {})
    
    def set_response(self, user_id: int, state: ConversationState, value: str):
        """Set a specific response for user."""
        if user_id in self._user_data:
            self._user_data[user_id]['responses'][state] = value
    
    def get_variable(self, user_id: int, key: str):
        """Get a specific variable for user."""
        return self._user_data.get(user_id, {}).get('variables', {}).get(key)
    
    def set_variable(self, user_id: int, key: str, value: any):
        """Set a specific variable for user."""
        if user_id in self._user_data:
            self._user_data[user_id]['variables'][key] = value