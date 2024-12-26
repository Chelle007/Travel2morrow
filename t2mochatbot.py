from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from openai import AsyncOpenAI
import logging
import os
from dotenv import load_dotenv
from enum import Enum, auto
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re

# Load env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
test_bot_api_key = os.getenv("TELEGRAM_TEST_BOT_API_KEY")

# Initialize OpenAI client
client = AsyncOpenAI(api_key=openai_api_key)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ConversationState(Enum):
    START = auto()
    WHO_TRAVELLING = auto()
    TRIP_TYPE = auto()
    DESTINATION = auto()
    TRAVEL_DATE = auto()
    ADVENTURE_ACTIVITIES = auto()
    ADVENTURE_DETAILS = auto()
    MEDICAL_CONDITIONS = auto()
    MEDICAL_DETAILS = auto()
    BUDGET = auto()
    RECOMMENDATION = auto()
    ADDITIONAL_COVERAGE = auto()
    QUESTIONS = auto()
    MANAGE_INSURANCE = auto()
    LEARN_MORE = auto()

# Store user states and responses
user_states: Dict[int, ConversationState] = {}
user_responses: Dict[int, Dict] = {}

# Human-readable labels for responses
response_labels = {
    'explore': 'Explore travel insurance options',
    'manage': 'Manage existing insurance',
    'learn': 'Learn more about Travel2morrow',
    'solo': 'Solo traveler',
    'family': 'Family',
    'single': 'Single trip',
    'annual': 'Annual coverage',
    'adventure_yes': 'Yes',
    'adventure_no': 'No',
    'medical_yes': 'Yes',
    'medical_no': 'No',
    'budget_50': 'Under $50',
    'budget_100': '$50-$100',
    'budget_above': 'Above $100',
    'view_policy': 'View policy details',
    'update_policy': 'Update policy',
    'file_claim': 'File a claim'
}

def format_choice_history(user_id: int) -> str:
    """Format the user's choice history into a readable summary."""
    if user_id not in user_responses or not user_responses[user_id]:
        return ""
    
    history = []
    state_labels = {
        ConversationState.WHO_TRAVELLING: "Who's travelling",
        ConversationState.TRIP_TYPE: "Trip type",
        ConversationState.DESTINATION: "Destination",
        ConversationState.TRAVEL_DATE: "Travel date",
        ConversationState.ADVENTURE_ACTIVITIES: "Adventure activities",
        ConversationState.ADVENTURE_DETAILS: "Adventure details",
        ConversationState.MEDICAL_CONDITIONS: "Medical conditions",
        ConversationState.MEDICAL_DETAILS: "Medical details",
        ConversationState.BUDGET: "Budget"
    }
    
    for state, response in user_responses[user_id].items():
        if state in state_labels:
            label = state_labels[state]
            value = response_labels.get(response, response)
            history.append(f"{label}: {value}")
    
    if not history:
        return ""
    
    return "Your choices so far:\n" + "\n".join(history) + "\n\n"

def get_keyboard_for_state(state: ConversationState) -> Optional[InlineKeyboardMarkup]:
    keyboards = {
        ConversationState.START: [
            [InlineKeyboardButton("Explore travel insurance options", callback_data='explore')],
            [InlineKeyboardButton("Manage my existing travel insurance", callback_data='manage')],
            [InlineKeyboardButton("Learn more about Travel2morrow", callback_data='learn')]
        ],
        ConversationState.WHO_TRAVELLING: [
            [InlineKeyboardButton("Solo", callback_data='solo')],
            [InlineKeyboardButton("Family", callback_data='family')]
        ],
        ConversationState.TRIP_TYPE: [
            [InlineKeyboardButton("Single trip", callback_data='single')],
            [InlineKeyboardButton("Annual", callback_data='annual')]
        ],
        ConversationState.ADVENTURE_ACTIVITIES: [
            [InlineKeyboardButton("Yes", callback_data='adventure_yes')],
            [InlineKeyboardButton("No", callback_data='adventure_no')]
        ],
        ConversationState.MEDICAL_CONDITIONS: [
            [InlineKeyboardButton("Yes", callback_data='medical_yes')],
            [InlineKeyboardButton("No", callback_data='medical_no')]
        ],
        ConversationState.BUDGET: [
            [InlineKeyboardButton("Under $50", callback_data='budget_50')],
            [InlineKeyboardButton("$50-$100", callback_data='budget_100')],
            [InlineKeyboardButton("Above $100", callback_data='budget_above')]
        ],
        ConversationState.MANAGE_INSURANCE: [
            [InlineKeyboardButton("View existing policy details", callback_data='view_policy')],
            [InlineKeyboardButton("Update policy information", callback_data='update_policy')],
            [InlineKeyboardButton("File a claim", callback_data='file_claim')]
        ]
    }
    
    keyboard = keyboards.get(state)
    if keyboard and state != ConversationState.START:
        # Add "Go Back" button to all screens except START
        keyboard.append([InlineKeyboardButton("◀️ Go Back", callback_data='go_back')])
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def get_message_for_state(state: ConversationState, user_id: int) -> str:
    messages = {
        ConversationState.START: "Hi! Welcome to Travel2morrow. How can I assist you today?",
        ConversationState.WHO_TRAVELLING: "Who's travelling?",
        ConversationState.TRIP_TYPE: "Single trip or annual?",
        ConversationState.DESTINATION: "Which country are you going to?",
        ConversationState.TRAVEL_DATE: "Which date are you going?",
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
    history = format_choice_history(user_id)
    return f"{history}{base_message}"

async def determine_next_state(current_state: ConversationState, user_input: str) -> ConversationState:
    if user_input.lower() in ['back', 'go_back', 'previous']:
        # Define state transitions for going back
        previous_states = {
            ConversationState.TRIP_TYPE: ConversationState.WHO_TRAVELLING,
            ConversationState.DESTINATION: ConversationState.TRIP_TYPE,
            ConversationState.TRAVEL_DATE: ConversationState.DESTINATION,
            ConversationState.ADVENTURE_ACTIVITIES: ConversationState.TRAVEL_DATE,
            ConversationState.ADVENTURE_DETAILS: ConversationState.ADVENTURE_ACTIVITIES,
            ConversationState.MEDICAL_CONDITIONS: ConversationState.ADVENTURE_ACTIVITIES,
            ConversationState.MEDICAL_DETAILS: ConversationState.MEDICAL_CONDITIONS,
            ConversationState.BUDGET: ConversationState.MEDICAL_CONDITIONS,
            ConversationState.RECOMMENDATION: ConversationState.BUDGET,
            ConversationState.ADDITIONAL_COVERAGE: ConversationState.RECOMMENDATION,
            ConversationState.QUESTIONS: ConversationState.ADDITIONAL_COVERAGE
        }
        return previous_states.get(current_state, current_state)
    
    # Define forward state transitions
    next_states = {
        ConversationState.START: ConversationState.WHO_TRAVELLING,
        ConversationState.WHO_TRAVELLING: ConversationState.TRIP_TYPE,
        ConversationState.TRIP_TYPE: ConversationState.DESTINATION,
        ConversationState.DESTINATION: ConversationState.TRAVEL_DATE,
        ConversationState.TRAVEL_DATE: ConversationState.ADVENTURE_ACTIVITIES,
        ConversationState.ADVENTURE_ACTIVITIES: ConversationState.MEDICAL_CONDITIONS,
        ConversationState.ADVENTURE_DETAILS: ConversationState.MEDICAL_CONDITIONS,
        ConversationState.MEDICAL_CONDITIONS: ConversationState.BUDGET,
        ConversationState.MEDICAL_DETAILS: ConversationState.BUDGET,
        ConversationState.BUDGET: ConversationState.RECOMMENDATION,
        ConversationState.RECOMMENDATION: ConversationState.ADDITIONAL_COVERAGE,
        ConversationState.ADDITIONAL_COVERAGE: ConversationState.QUESTIONS,
    }
    return next_states.get(current_state, current_state)

async def chat_with_ai(user_input: str, context: str = "") -> str:
    """Interact with OpenAI API."""
    try:
        system_message = (
            "You are a travel insurance expert assistant. "
            "Keep responses concise and relevant to travel insurance. "
            f"Current context: {context}"
        )
        
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_input},
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error with OpenAI API: {e}")
        return "Sorry, I encountered an error. Please try again later."

async def start(update: Update, context: CallbackContext) -> None:
    """Handle the /start command."""
    user_id = update.effective_user.id
    user_states[user_id] = ConversationState.START
    user_responses[user_id] = {}
    
    keyboard = get_keyboard_for_state(ConversationState.START)
    message = get_message_for_state(ConversationState.START, user_id)
    
    await update.message.reply_text(message, reply_markup=keyboard)

async def validate_with_gpt(state: ConversationState, user_input: str) -> tuple[bool, str, any]:
    """
    Use GPT to validate and interpret user input based on the current state.
    Returns (is_valid, message, processed_value)
    """
    try:
        # Construct context-aware prompt based on the current state
        state_contexts = {
            ConversationState.WHO_TRAVELLING: {
                "valid_options": ["solo", "family"],
                "prompt": "User is choosing between solo or family travel. Is their response valid? If valid, categorize as 'solo' or 'family'. If invalid, explain why."
            },
            ConversationState.TRIP_TYPE: {
                "valid_options": ["single", "annual"],
                "prompt": "User is choosing between single trip or annual coverage. Is their response valid? If valid, categorize as 'single' or 'annual'. If invalid, explain why."
            },
            ConversationState.DESTINATION: {
                "prompt": "User is entering a country name. If it's ambiguous (like 'ind'), ask for clarification. If it's clear, confirm the country. If invalid, explain why."
            },
            ConversationState.TRAVEL_DATE: {
                "prompt": "User is entering a travel date. Is it a valid date format? If valid, confirm the date. If invalid, ask for a clearer date format."
            },
            ConversationState.ADVENTURE_ACTIVITIES: {
                "valid_options": ["yes", "no"],
                "prompt": "User is choosing whether they need adventure activities coverage (yes/no). Is their response valid? If valid, categorize as 'yes' or 'no'. If invalid, explain why."
            },
            ConversationState.MEDICAL_CONDITIONS: {
                "valid_options": ["yes", "no"],
                "prompt": "User is indicating if they have medical conditions (yes/no). Is their response valid? If valid, categorize as 'yes' or 'no'. If invalid, explain why."
            }
        }

        # Check for "go back" intent first
        back_response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Determine if the user wants to go back to the previous question. Respond with only 'yes' or 'no'."},
                {"role": "user", "content": f"Does this message indicate the user wants to go back: '{user_input}'"}
            ]
        )
        
        if 'yes' in back_response.choices[0].message.content.lower():
            return (True, "Going back to previous question...", 'go_back')
        
        # Special handling for travel date
        if state == ConversationState.TRAVEL_DATE:
            current_date = datetime.now()
            
            date_system_prompt = f"""
            Current date: {current_date.strftime('%Y-%m-%d')}
            
            Parse the user's travel date input and validate it according to these rules:
            1. Date must be in the future (after {current_date.strftime('%Y-%m-%d')})
            2. If year is not specified, assume {current_date.year} if the date would be in the future, otherwise assume {current_date.year + 1}
            3. If only date and month are provided, determine the appropriate year based on rule 2
            4. Accept various date formats (e.g., "25 Dec", "December 25", "25/12", "next month", "tomorrow")
            
            Respond in JSON format:
            {{
                "is_valid": true/false,
                "message": "explanation or clarification message",
                "processed_value": "YYYY-MM-DD formatted date if valid, null if invalid",
                "needs_year_confirmation": true/false
            }}
            
            For example:
            - "25 Dec" → Determine year based on whether Dec 25 this year is in the future
            - "next month" → Convert to specific date
            - "tomorrow" → Convert to specific date
            - "25/12" → Same as "25 Dec"
            """

            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": date_system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # If valid but needs year confirmation, ask user
            if result["is_valid"] and result.get("needs_year_confirmation", False):
                try:
                    date_obj = datetime.strptime(result["processed_value"], "%Y-%m-%d")
                    return (False, 
                           f"I understand you want to travel on {date_obj.strftime('%d %B')}, "
                           f"is that {date_obj.year}? Please confirm the year.", None)
                except ValueError:
                    return (False, "Please specify the year for your travel date.", None)
            
            return (result["is_valid"], result["message"], result["processed_value"])

        # Get state context
        context = state_contexts.get(state, {"prompt": "Validate if this is a reasonable response."})
        
        # Create detailed prompt for GPT
        system_prompt = f"""
        Current question state: {state.name}
        {context['prompt']}
        
        Respond in JSON format:
        {{
            "is_valid": true/false,
            "message": "explanation or clarification question",
            "processed_value": "normalized value if valid, null if invalid"
        }}
        """

        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        
        # Parse GPT's response
        import json
        result = json.loads(response.choices[0].message.content)
        
        return (result["is_valid"], result["message"], result["processed_value"])

    except Exception as e:
        logger.error(f"Error in validate_with_gpt: {e}")
        return (False, "Sorry, I couldn't validate your input. Please try again.", None)

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handle text messages."""
    user_id = update.effective_user.id
    user_input = update.message.text
    current_state = user_states.get(user_id, ConversationState.START)
    
    # Validate input using GPT
    is_valid, validation_message, processed_value = await validate_with_gpt(current_state, user_input)
    
    if not is_valid:
        # If input is invalid, send validation message and keep same state
        keyboard = get_keyboard_for_state(current_state)
        await update.message.reply_text(
            validation_message + "\n\n" + get_message_for_state(current_state, user_id),
            reply_markup=keyboard
        )
        return
    
    # Handle "go back" command
    if processed_value == 'go_back':
        next_state = await determine_next_state(current_state, 'back')
        if current_state in user_responses.get(user_id, {}):
            del user_responses[user_id][current_state]
    else:
        # Store validated response
        if current_state not in [ConversationState.START, ConversationState.LEARN_MORE]:
            user_responses.setdefault(user_id, {})
            user_responses[user_id][current_state] = processed_value
            
        next_state = await determine_next_state(current_state, processed_value)
    
    user_states[user_id] = next_state
    
    # If validation message exists and it's not just a simple confirmation,
    # show it before the next question
    if validation_message and not validation_message.startswith("Valid"):
        await update.message.reply_text(validation_message)
    
    # Get appropriate message and keyboard for next state
    message = get_message_for_state(next_state, user_id)
    keyboard = get_keyboard_for_state(next_state)
    
    await update.message.reply_text(message, reply_markup=keyboard)

async def button_handler(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    current_state = user_states.get(user_id, ConversationState.START)
    
    await query.answer()
    
    # Create a message showing what the user selected
    selected_option = response_labels.get(query.data, query.data)
    user_selection_message = f"Selected: {selected_option}"
    await query.message.reply_text(user_selection_message)
    
    # Handle "Go Back" button
    if query.data == 'go_back':
        next_state = await determine_next_state(current_state, 'back')
        if current_state in user_responses.get(user_id, {}):
            del user_responses[user_id][current_state]
    else:
        # Store user response
        if current_state not in [ConversationState.START, ConversationState.LEARN_MORE]:
            user_responses.setdefault(user_id, {})
            user_responses[user_id][current_state] = query.data
        
        # Handle specific button actions
        if query.data == 'explore':
            next_state = ConversationState.WHO_TRAVELLING
        elif query.data == 'manage':
            next_state = ConversationState.MANAGE_INSURANCE
        elif query.data == 'learn':
            next_state = ConversationState.LEARN_MORE
        elif query.data in ['adventure_yes', 'medical_yes']:
            next_state = (ConversationState.ADVENTURE_DETAILS if query.data == 'adventure_yes' 
                         else ConversationState.MEDICAL_DETAILS)
        else:
            next_state = await determine_next_state(current_state, query.data)
    
    user_states[user_id] = next_state
    message = get_message_for_state(next_state, user_id)
    keyboard = get_keyboard_for_state(next_state)
    
    # Send a new message instead of editing
    await query.message.reply_text(text=message, reply_markup=keyboard)

async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle the /help command."""
    await update.message.reply_text(
        "You can control me by sending these commands:\n"
        "/start - Start a conversation\n"
        "/help - Get help on how to use this bot"
    )

def main():
    """Main function to run the bot."""
    bot_api_key = test_bot_api_key
    
    application = Application.builder().token(bot_api_key).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    try:
        logger.info("Starting the bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error starting the bot: {e}")

if __name__ == '__main__':
    main()