from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import logger, TELEGRAM_TEST_BOT_API_KEY, TELEGRAM_BOT_API_KEY
from handlers import start_command, help_command, handle_message, button_handler

def main():
    """Main function to run the bot."""
    bot_api_key = TELEGRAM_TEST_BOT_API_KEY
    
    application = Application.builder().token(bot_api_key).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
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