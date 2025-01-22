from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, MenuButton, MenuButtonCommands
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from openai import AsyncOpenAI
import logging
import os
from dotenv import load_dotenv
from enum import Enum, auto
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import psycopg2
import uuid

# INITIALIZE
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
    DEFAULT_ANSWER = auto()
    DESTINATION = auto()
    TRAVEL_DATE = auto()
    DURATION = auto()
    WHO_TRAVELLING = auto()
    TRIP_TYPE = auto()
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
user_variables: Dict[int, Dict] = {}

# Human-readable labels for responses
response_labels = {
    'explore': 'Explore travel insurance options',
    'manage': 'Manage existing insurance',
    'learn': 'Learn more about Travel2morrow',
    'default_yes': 'Yes',
    'default_no': 'No',
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
    'coverage_interruption': 'Trip Interruption',
    'coverage_luggage': 'Lost Luggage',
    'coverage_delays': 'Travel Delays',
    'coverage_none': 'No Additional Coverage',
    'go_back': 'Go Back',
    'view_policy': 'View policy details',
    'update_policy': 'Update policy',
    'file_claim': 'File a claim'
}

response_mapping = {
    "Explore travel insurance options": "explore",
    "Manage my existing travel insurance": "manage",
    "Learn more about Travel2morrow": "learn",
    "Yes": "default_yes",
    "No": "default_no",
    "Solo": "solo",
    "Family": "family",
    "Single trip": "single",
    "Annual": "annual",
    "Under $50": "budget_50",
    "$50-$100": "budget_100",
    "Above $100": "budget_above",
    "Trip Interruption": "coverage_interruption",
    "Lost Luggage": "coverage_luggage",
    "Travel Delays": "coverage_delays",
    "No Additional Coverage": "coverage_none",
    "View existing policy details": "view_policy",
    "Update policy information": "update_policy",
    "File a claim": "file_claim",
    "◀️ Go Back": "go_back"
}


# FUNCTIONS
def get_database_connection():
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        print("Database connection successful!")
        return connection
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

def save_user_responses(connection, user_id: int, responses: dict) -> Optional[str]:
    """Save or update user responses in the database."""
    try:
        cursor = connection.cursor()

        # Extract the telegram_handle from responses
        telegram_handle = responses.get('telegram_handle')
        if not telegram_handle:
            logger.error("No telegram_handle provided in responses.")
            return None

        # Extract other values from responses
        who_travelling = responses.get(ConversationState.WHO_TRAVELLING)
        trip_type = responses.get(ConversationState.TRIP_TYPE)
        adventure_activities = responses.get(ConversationState.ADVENTURE_ACTIVITIES) == 'adventure_yes'
        adventure_details = responses.get(ConversationState.ADVENTURE_DETAILS)
        medical_conditions = responses.get(ConversationState.MEDICAL_CONDITIONS) == 'medical_yes'
        medical_details = responses.get(ConversationState.MEDICAL_DETAILS)
        budget = responses.get(ConversationState.BUDGET)
        additional_coverage = responses.get(ConversationState.ADDITIONAL_COVERAGE)

        # Map budget values to database format
        budget_mapping = {
            'budget_50': 'Under $50',
            'budget_100': '$50-$100',
            'budget_above': 'Above $100'
        }
        budget_value = budget_mapping.get(budget) if budget else None

        # Map additional coverage values to readable format
        coverage_mapping = {
            'coverage_interruption': 'Trip Interruption',
            'coverage_luggage': 'Lost Luggage',
            'coverage_delays': 'Travel Delays',
            'coverage_none': 'No Additional Coverage'
        }
        coverage_value = coverage_mapping.get(additional_coverage) if additional_coverage else None

        # Check if the telegram_handle already exists
        check_query = "SELECT user_id FROM users WHERE telegram_handle = %s"
        cursor.execute(check_query, (telegram_handle,))
        existing_user = cursor.fetchone()

        if existing_user:
            # Update the existing row
            update_query = """
            UPDATE users
            SET who_travelling = %s,
                trip_type = %s,
                adventure_activities = %s,
                adventure_details = %s,
                medical_conditions = %s,
                medical_details = %s,
                budget = %s,
                additional_coverage = %s
            WHERE telegram_handle = %s
            """
            cursor.execute(update_query, (
                who_travelling,
                trip_type,
                adventure_activities,
                adventure_details,
                medical_conditions,
                medical_details,
                budget_value,
                coverage_value,
                telegram_handle
            ))
            db_user_id = existing_user[0]
            logger.info(f"Updated existing user: {db_user_id}")
        else:
            # Insert a new row
            db_user_id = str(uuid.uuid4())
            insert_query = """
            INSERT INTO users (
                user_id, telegram_handle, who_travelling, trip_type, 
                adventure_activities, adventure_details, medical_conditions, 
                medical_details, budget, additional_coverage
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                db_user_id,
                telegram_handle,
                who_travelling,
                trip_type,
                adventure_activities,
                adventure_details,
                medical_conditions,
                medical_details,
                budget_value,
                coverage_value
            ))
            logger.info(f"Added to database: {db_user_id}")

        connection.commit()
        cursor.close()

        return db_user_id
        
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
        connection.rollback()
        return None

def get_user_saved_responses(connection, telegram_handle: str) -> Optional[dict]:
    """Fetch saved responses for a user from the database."""
    try:
        cursor = connection.cursor()
        query = """
        SELECT who_travelling, trip_type, adventure_activities, 
               adventure_details, medical_conditions, medical_details,
               budget, additional_coverage
        FROM users 
        WHERE telegram_handle = %s
        """
        cursor.execute(query, (telegram_handle,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            # Map database values back to callback_data format
            budget_mapping = {
                'Under $50': 'budget_50',
                '$50-$100': 'budget_100',
                'Above $100': 'budget_above'
            }
            
            coverage_mapping = {
                'Trip Interruption': 'coverage_interruption',
                'Lost Luggage': 'coverage_luggage',
                'Travel Delays': 'coverage_delays',
                'No Additional Coverage': 'coverage_none'
            }
            
            return {
                ConversationState.WHO_TRAVELLING: result[0].lower() if result[0] else None,
                ConversationState.TRIP_TYPE: result[1].lower() if result[1] else None,
                ConversationState.ADVENTURE_ACTIVITIES: 'adventure_yes' if result[2] else 'adventure_no',
                ConversationState.ADVENTURE_DETAILS: result[3],
                ConversationState.MEDICAL_CONDITIONS: 'medical_yes' if result[4] else 'medical_no',
                ConversationState.MEDICAL_DETAILS: result[5],
                ConversationState.BUDGET: budget_mapping.get(result[6]),
                ConversationState.ADDITIONAL_COVERAGE: coverage_mapping.get(result[7])
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching saved responses: {e}")
        return None

def format_saved_responses(saved_responses: dict) -> str:
    """Format saved responses into a readable summary."""
    if not saved_responses:
        return ""
    
    formatted = ["Here are your previous answers:"]
    state_labels = {
        ConversationState.WHO_TRAVELLING: "Who's travelling",
        ConversationState.TRIP_TYPE: "Trip type",
        ConversationState.ADVENTURE_ACTIVITIES: "Adventure activities",
        ConversationState.ADVENTURE_DETAILS: "Adventure details",
        ConversationState.MEDICAL_CONDITIONS: "Medical conditions",
        ConversationState.MEDICAL_DETAILS: "Medical details",
        ConversationState.BUDGET: "Budget",
        ConversationState.ADDITIONAL_COVERAGE: "Additional coverage"
    }
    
    for state, value in saved_responses.items():
        if state in state_labels and value:
            label = state_labels[state]
            display_value = response_labels.get(value, value)
            formatted.append(f"{label}: {display_value}")
    
    return "\n".join(formatted)

def get_keyboard_for_state(state: ConversationState) -> Optional[ReplyKeyboardMarkup]:
    keyboards = {
        ConversationState.START: [
            ["Explore travel insurance options"],
            ["Manage my existing travel insurance"],
            ["Learn more about Travel2morrow"]
        ],
        ConversationState.DEFAULT_ANSWER: [
            ["Yes"],
            ["No"]
        ],
        ConversationState.WHO_TRAVELLING: [
            ["Solo"],
            ["Family"]
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
            ["$50-$100"],
            ["Above $100"]
        ],
        ConversationState.ADDITIONAL_COVERAGE: [
            ["Trip Interruption"],
            ["Lost Luggage"],
            ["Travel Delays"],
            ["No Additional Coverage"]
        ],
        ConversationState.MANAGE_INSURANCE: [
            ["View existing policy details"],
            ["Update policy information"],
            ["File a claim"]
        ]
    }
    
    keyboard = keyboards.get(state)
    if keyboard and state != ConversationState.START:
        keyboard.append(["◀️ Go Back"])
    
    return ReplyKeyboardMarkup(
        keyboard if keyboard else [[]], 
        resize_keyboard=True,
        one_time_keyboard=True  # Keyboard will hide after selection
    )

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
                    # Convert the value to a readable format using response_labels if available
                    display_value = response_labels.get(value, value)
                    saved_response_lines.append(f"{label}: {display_value}")
            
            if saved_response_lines:
                return "\n".join(saved_response_lines) + "\n\n" + base_message
    
    return base_message

async def determine_next_state(current_state: ConversationState, user_input: str) -> ConversationState:
    """Determine the next state based on current state and user input."""
    states = [
        ConversationState.START,
        ConversationState.DEFAULT_ANSWER,
        ConversationState.DESTINATION,
        ConversationState.TRAVEL_DATE,
        ConversationState.DURATION,
        ConversationState.WHO_TRAVELLING,
        ConversationState.TRIP_TYPE,
        ConversationState.ADVENTURE_ACTIVITIES,
        ConversationState.MEDICAL_CONDITIONS,
        ConversationState.BUDGET,
        ConversationState.ADDITIONAL_COVERAGE,
        ConversationState.RECOMMENDATION,
        ConversationState.QUESTIONS,
    ]

    try:
        current_index = states.index(current_state)
    except ValueError:
        return current_state

    if user_input.lower() in ['back', 'go_back', 'previous']:
        next_index = max(0, current_index - 1)
    else:
        next_index = min(len(states) - 1, current_index + 1)

    return states[next_index]

async def validate_with_gpt(state: ConversationState, user_input: str) -> tuple[bool, str, any]:
    """
    Use GPT to validate and interpret user input based on the current state.
    Returns (is_valid, message, processed_value)
    """
    try:
        # Check for "go back" intent first, but only if the input suggests backwards movement
        go_back_indicators = ["back", "previous", "return", "go back"]
        if any(indicator in user_input.lower() for indicator in go_back_indicators):
            back_response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Determine if the user wants to go back to the previous question. Respond with only 'yes' or 'no'."},
                    {"role": "user", "content": f"Does this message indicate the user wants to go back: '{user_input}'"}
                ]
            )
            
            if 'yes' in back_response.choices[0].message.content.lower():
                return (True, "Going back to previous question...", 'go_back')

        # Construct context-aware prompt based on the current state
        state_contexts = {
            ConversationState.START: {
                "valid_options": ["explore", "manage", "learn"],
                "prompt": "User is choosing between explore travel insurance options, manage their existing travel insurance, or learn more about Travel2morrow. Is their response valid? If valid, categorize as 'explore', 'manage', or 'learn'. If invalid, explain why."
            },
            ConversationState.DEFAULT_ANSWER: {
                "valid_options": ["yes", "no"],
                "prompt": "User is choosing whether they want to use default answer (yes/no). Is their response valid? If valid, categorize as 'yes' or 'no'. If invalid, explain why."
            },
            ConversationState.DESTINATION: {
                "prompt": "User is entering a country name. If it's valid, confirm the country. If invalid, explain why."
            },
            ConversationState.TRAVEL_DATE: {
                "prompt": "User is entering a travel date. Is it a valid date format? If valid, confirm the date. If invalid, ask for a clearer date format."
            },
            ConversationState.DURATION: {
                "prompt": "User is entering a duration. Is it a valid duration format less than 365 days? If valid, transform the duration in days. If invalid, explain why."
            },
            ConversationState.WHO_TRAVELLING: {
                "valid_options": ["solo", "family"],
                "prompt": "User is choosing between solo or family travel. Is their response valid? If valid, categorize as 'solo' or 'family'. If invalid, explain why."
            },
            ConversationState.TRIP_TYPE: {
                "valid_options": ["single", "annual"],
                "prompt": "User is choosing between single trip or annual coverage. Is their response valid? If valid, categorize as 'single' or 'annual'. If invalid, explain why."
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

        # Special handling for travel date
        if state == ConversationState.TRAVEL_DATE:
            current_date = datetime.now()
            ninety_days_later = current_date + timedelta(days=90)
            
            date_system_prompt = f"""
            Current date: {current_date.strftime('%Y-%m-%d')}
            
            Parse the user's travel date input and validate it according to these rules:
            1. Date must be in the future (after {current_date.strftime('%Y-%m-%d')})
            2. Date must not exceed 90 days later (must be before {ninety_days_later.strftime('%Y-%m-%d')})
            3. If year is not specified, assume {current_date.year} if the date would be in the future, otherwise assume {current_date.year + 1}
            4. If only date and month are provided, determine the appropriate year based on rule 2
            5. Accept various date formats (e.g., "25 Dec", "December 25", "25/12", "next month", "tomorrow")
            
            Respond in JSON format:
            {{
                "is_valid": true/false,
                "message": "If it is valid, answer with this format: 'Selected: YYYY-MM-DD formatted date'. Else clarification question",
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

        # Special handling for duration state
        if state == ConversationState.DURATION:
            duration_system_prompt = """
                User is entering a trip duration. Convert any duration format to days.
                Accept and convert:
                - Direct day inputs (e.g., "5 days", "7d")
                - Hours (e.g., "48 hours", "72h")
                - Weeks (e.g., "2 weeks", "3w")
                - Months (e.g., "1 month", "2m")
                - Mixed formats (e.g., "1 week 3 days", "2 weeks and 4 days")
                - Numbers only (assume days if just a number)
                
                Rules:
                1. Maximum duration is 365 days
                2. Convert all inputs to whole number of days
                3. For months, use 30 days per month
                4. Round up partial days
                
                Response must be in format:
                {
                    "is_valid": true/false,
                    "message": "Selected: X days" or explanation if invalid,
                    "processed_value": "X" (just the number of days as string)
                }
                """

            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": duration_system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            if result["is_valid"]:
                days = int(result["processed_value"])
                if days > 365:
                    return (False, "Duration cannot exceed 365 days. Please enter a shorter duration.", None)
                return (True, f"Selected: {days} days", str(days))
            return (False, result["message"], None)

        # Get state context
        context = state_contexts.get(state, {"prompt": "Validate if this is a reasonable response."})
        
        # Create detailed prompt for GPT
        system_prompt = f"""
        Current question state: {state.name}
        {context['prompt']}
        
        Respond in JSON format:
        {{
            "is_valid": true/false,
            "message": "If it is valid, answer with this format: 'Selected: user's choice'. Else clarification question",
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

async def handle_state_transition(
    user_id: int, 
    current_state: ConversationState,
    next_action: str,
    context: CallbackContext
) -> tuple[ConversationState, str, ReplyKeyboardMarkup]:
    """
    Handle state transitions based on button_handler logic.
    Returns tuple of (next_state, message, keyboard)
    """
    print("\nSTATE TRANSITION")
    print(f"User ID: {user_id}")
    print(f"Current state: {current_state}")
    print(f"Action: {next_action}")

    # Initialize next_state
    next_state = await determine_next_state(current_state, next_action)
    
    if next_action == 'go_back':
        print(f"GO BACK STATE: {current_state}")
        if current_state == ConversationState.DESTINATION and user_variables[user_id]['default_data_existed']:
            next_state = ConversationState.DEFAULT_ANSWER
        elif current_state == ConversationState.RECOMMENDATION and user_variables[user_id]['chosen_default']:
            next_state = ConversationState.DURATION
        else:
            next_state = await determine_next_state(current_state, 'back')
        if current_state in user_responses.get(user_id, {}):
            del user_responses[user_id][current_state]
    else:
        print(f"HANDLING NON-BACK STATE: {current_state}")
        
        # Handle 'explore' option from START state
        if current_state == ConversationState.START and next_action == 'explore':
            username = context.user_data.get('username')
            if username:
                telegram_handle = f"@{username}"
                connection = get_database_connection()
                if connection:
                    saved_responses = get_user_saved_responses(connection, telegram_handle)
                    connection.close()
                    
                    if saved_responses and not user_variables[user_id]['chosen_default']:
                        user_variables[user_id]['default_data_existed'] = True
                        user_variables[user_id]['saved_responses'] = saved_responses
                        context.user_data['saved_responses'] = saved_responses
                        next_state = ConversationState.DEFAULT_ANSWER
                    else:
                        next_state = ConversationState.DESTINATION
        
        # Handle default answer choice
        elif current_state == ConversationState.DEFAULT_ANSWER:
            print(f"Processing default answer: {next_action}")
            if next_action == 'default_yes':
                saved_responses = context.user_data.get('saved_responses', {})
                user_responses[user_id] = saved_responses.copy()
                user_responses[user_id]['telegram_handle'] = f"@{context.user_data.get('username')}"
                user_variables[user_id]['chosen_default'] = True
            elif next_action == 'default_no':
                user_responses[user_id] = {'telegram_handle': f"@{context.user_data.get('username')}"}
                user_variables[user_id]['chosen_default'] = False
        
        # Handle travel date state when using default answers
        elif current_state == ConversationState.DURATION and user_variables[user_id]['chosen_default']:
            print("Processing travel date with default answers")
            next_state = ConversationState.RECOMMENDATION
        
        # Handle other button callbacks
        else:
            if current_state not in [ConversationState.START, ConversationState.LEARN_MORE]:
                user_responses.setdefault(user_id, {})
                user_responses[user_id][current_state] = next_action
            
                if next_action == 'manage':
                    next_state = ConversationState.MANAGE_INSURANCE
                elif next_action == 'learn':
                    next_state = ConversationState.LEARN_MORE

    # Save to database when reaching recommendation state
    if next_state == ConversationState.RECOMMENDATION:
        print("Saving to database")
        connection = get_database_connection()
        if connection:
            db_user_id = save_user_responses(connection, user_id, user_responses.get(user_id, {}))
            if db_user_id:
                context.user_data['db_user_id'] = db_user_id
            connection.close()
    
    user_states[user_id] = next_state
    print(f"Final next_state: {next_state}")
    
    message = get_message_for_state(next_state, user_id)
    keyboard = get_keyboard_for_state(next_state)
    
    return next_state, message, keyboard

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handle text messages."""
    print("\nENTERING HANDLE_MESSAGE")
    user_id = update.effective_user.id
    user_input = update.message.text
    current_state = user_states.get(user_id, ConversationState.START)
    
    print(f"User input: {user_input}")
    print(f"Current state: {current_state}")
    
    # Initialize user if not exists
    if user_id not in user_variables:
        user_variables[user_id] = {
            "chosen_default": False,
            "default_data_existed": False
        }
    
    # Map the keyboard button text to the callback data
    callback_data = response_mapping.get(user_input)
    if callback_data:
        # Process the mapped input like a button callback
        if user_id not in user_responses:
            user_responses[user_id] = {}
            username = update.effective_user.username
            if username:
                user_responses[user_id]['telegram_handle'] = f"@{username}"
        
        context.user_data['username'] = update.effective_user.username
        
        next_state, message, keyboard = await handle_state_transition(
            user_id,
            current_state,
            callback_data,
            context
        )
        
        await update.message.reply_text(
            text=message, 
            reply_markup=keyboard or ReplyKeyboardRemove()  # Remove keyboard if None
        )
        return
    
    # Handle free text input states (like DESTINATION, TRAVEL_DATE, etc.)
    is_valid, validation_message, processed_value = await validate_with_gpt(current_state, user_input)
    print(f"Validation: valid={is_valid}, value={processed_value}")
    
    if not is_valid:
        keyboard = get_keyboard_for_state(current_state)
        await update.message.reply_text(
            validation_message + "\n\n" + get_message_for_state(current_state, user_id),
            reply_markup=keyboard
        )
        return

    context.user_data['username'] = update.effective_user.username
    
    next_state, message, keyboard = await handle_state_transition(
        user_id, 
        current_state, 
        processed_value, 
        context
    )
    
    if validation_message and not validation_message.startswith("Valid"):
        await update.message.reply_text(validation_message)
    
    await update.message.reply_text(
        text=message, 
        reply_markup=keyboard or ReplyKeyboardRemove()
    )

async def button_handler(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    print("\nENTERING BUTTON_HANDLER")
    query = update.callback_query
    user_id = query.from_user.id
    
    # Store the latest message_id for each user
    if not hasattr(context, 'latest_message_ids'):
        context.latest_message_ids = {}
    
    # Check if this callback is from an old message
    if (user_id in context.latest_message_ids and 
        query.message.message_id < context.latest_message_ids[user_id]):
        await query.answer("Please use the buttons from the most recent message.", show_alert=True)
        return
    
    # Update the latest message ID
    context.latest_message_ids[user_id] = query.message.message_id
    
    if user_id not in user_variables:
        user_variables[user_id] = {
            "chosen_default": False,
            "default_data_existed": False
        }
    
    current_state = user_states.get(user_id, ConversationState.START)
    print(f"Button pressed: {query.data}")
    print(f"Current state: {current_state}")
    
    await query.answer()
    
    selected_option = response_labels.get(query.data, query.data)
    await query.message.reply_text(f"Selected: {selected_option}")

    # Store username for state transition
    context.user_data['username'] = query.from_user.username
    
    next_state, message, keyboard = await handle_state_transition(
        user_id, 
        current_state, 
        query.data, 
        context
    )
    
    await query.message.reply_text(text=message, reply_markup=keyboard)

async def setup_menu_button(application: Application) -> None:
    """Set up the menu button for the bot."""
    try:
        # Get the bot instance
        bot = application.bot
        
        # Set the menu button to show commands
        await bot.set_chat_menu_button(
            menu_button=MenuButtonCommands()
        )
        logger.info("Menu button setup successful")
    except Exception as e:
        logger.error(f"Error setting up menu button: {e}")

async def start(update: Update, context: CallbackContext) -> None:
    """Handle the /start command."""
    user_id = update.effective_user.id
    user_states[user_id] = ConversationState.START
    user_responses[user_id] = {}
    
    username = update.effective_user.username
    if username:
        user_responses[user_id]['telegram_handle'] = f"@{username}"
    
    keyboard = get_keyboard_for_state(ConversationState.START)
    message = get_message_for_state(ConversationState.START, user_id)
    
    await update.message.reply_text(
        text=message, 
        reply_markup=keyboard
    )

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
        application.job_queue.run_once(setup_menu_button, 0)
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error starting the bot: {e}")

if __name__ == '__main__':
    main()