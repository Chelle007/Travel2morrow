import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configuration variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TEST_BOT_API_KEY = os.getenv("TELEGRAM_TEST_BOT_API_KEY")

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)