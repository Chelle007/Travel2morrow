from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from openai import AsyncOpenAI
import requests
import logging
import os
from dotenv import load_dotenv

# Load env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = AsyncOpenAI(api_key=api_key)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Handlers
async def start(update: Update, context: CallbackContext) -> None:
    """Handle the /start command."""
    keyboard = [
        [InlineKeyboardButton("Insurance Options 1", callback_data='insurance1')],
        [InlineKeyboardButton("Insurance Options 2", callback_data='insurance2')],
        [InlineKeyboardButton("Insurance Options 3", callback_data='insurance3')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to Travel2morrow! How can I assist you today?",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle the /help command."""
    keyboard = [
        [InlineKeyboardButton("Insurance Options 1", callback_data='insurance1')],
        [InlineKeyboardButton("Insurance Options 2", callback_data='insurance2')],
        [InlineKeyboardButton("Insurance Options 3", callback_data='insurance3')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "You can control me by sending these commands:\n"
        "/start - Start a conversation\n"
        "/help - Get help on how to use this bot",
        reply_markup=reply_markup
    )

async def cat(update: Update, context: CallbackContext) -> None:
    """Handle the /cat command."""
    try:
        response = requests.get("https://api.thecatapi.com/v1/images/search")
        response.raise_for_status()
        cat_url = response.json()[0]['url']
        await update.message.reply_photo(cat_url)
    except Exception as e:
        logger.error(f"Error fetching cat image: {e}")
        await update.message.reply_text("Sorry, I couldn't fetch a cat image right now. Please try again later.")

async def handle_message(update: Update, context: CallbackContext) -> None:
    logger.info(f"Received message: {update.message.text}")
    user_input = update.message.text
    
    try:
        # Call the updated chat_with_ai function
        ai_response = await chat_with_ai(user_input)
        await update.message.reply_text(ai_response)
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("Sorry, I encountered an error while processing your request. Please try again later.")

async def chat_with_ai(user_input: str) -> str:
    """Interact with OpenAI API using the updated interface."""
    try:
        # Use the new chat completion method
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert assistant specializing in travel insurance."},
                {"role": "user", "content": user_input},
            ]
        )
        # Extract the AI's reply
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error with OpenAI API: {e}")
        return "Sorry, I encountered an error while processing your request. Please try again later."

async def button_handler(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    option = query.data

    try:
        if option == 'insurance1':
            await query.answer()
            await query.edit_message_text("You selected Insurance Option 1. Here are the details...")
        elif option == 'insurance2':
            await query.answer()
            await query.edit_message_text("You selected Insurance Option 2. Here are the details...")
        elif option == 'insurance3':
            await query.answer()
            await query.edit_message_text("You selected Insurance Option 3. Here are the details...")
        else:
            await query.answer("Invalid option selected.")
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
        await query.answer("An error occurred while processing your request.")

def main():
    """Main function to run the bot."""
    # Replace with your actual Telegram bot API token
    api_key = '7796404774:AAGYjzXfk0oDC9F-0_K5K9JDPiK0hxtZU7A' # test bot

    application = Application.builder().token(api_key).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cat", cat))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start polling
    try:
        logger.info("Starting the bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error starting the bot: {e}")

if __name__ == '__main__':
    main()