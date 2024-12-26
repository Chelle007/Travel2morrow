from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from openai import AsyncOpenAI
import logging
import os
from dotenv import load_dotenv
from enum import Enum, auto
from typing import Dict, List, Optional

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

# Store user states
user_states: Dict[int, ConversationState] = {}
user_responses: Dict[int, Dict] = {}

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
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def get_message_for_state(state: ConversationState, user_data: Dict = None) -> str:
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
    return messages.get(state, "How can I help you?")

async def determine_next_state(current_state: ConversationState, user_input: str) -> ConversationState:
    if "back" in user_input.lower():
        # Define state transitions for going back
        previous_states = {
            ConversationState.TRIP_TYPE: ConversationState.WHO_TRAVELLING,
            ConversationState.DESTINATION: ConversationState.TRIP_TYPE,
            ConversationState.TRAVEL_DATE: ConversationState.DESTINATION,
            ConversationState.ADVENTURE_ACTIVITIES: ConversationState.TRAVEL_DATE,
            ConversationState.MEDICAL_CONDITIONS: ConversationState.ADVENTURE_ACTIVITIES,
            ConversationState.BUDGET: ConversationState.MEDICAL_CONDITIONS,
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
    message = get_message_for_state(ConversationState.START)
    
    await update.message.reply_text(message, reply_markup=keyboard)

async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle the /help command."""
    await update.message.reply_text(
        "You can control me by sending these commands:\n"
        "/start - Start a conversation\n"
        "/help - Get help on how to use this bot"
    )
    
async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handle text messages."""
    user_id = update.effective_user.id
    user_input = update.message.text
    current_state = user_states.get(user_id, ConversationState.START)
    
    # Store user response
    user_responses.setdefault(user_id, {})
    user_responses[user_id][current_state] = user_input
    
    # Get AI assistance for understanding user input
    context_str = f"Current state: {current_state}, User input: {user_input}"
    ai_interpretation = await chat_with_ai(
        f"Based on the user's message '{user_input}', help interpret their intent in the context of {current_state}.",
        context_str
    )
    
    # Determine next state
    next_state = await determine_next_state(current_state, user_input)
    user_states[user_id] = next_state
    
    # Get appropriate message and keyboard for next state
    message = get_message_for_state(next_state, user_responses.get(user_id))
    keyboard = get_keyboard_for_state(next_state)
    
    await update.message.reply_text(message, reply_markup=keyboard)

async def button_handler(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    current_state = user_states.get(user_id, ConversationState.START)
    
    await query.answer()
    
    # Store user response
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
    message = get_message_for_state(next_state, user_responses.get(user_id))
    keyboard = get_keyboard_for_state(next_state)
    
    await query.edit_message_text(text=message, reply_markup=keyboard)

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