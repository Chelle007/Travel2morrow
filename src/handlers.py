from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from conversation_states import ConversationState
from constants import RESPONSE_MAPPING, REVERSE_MAPPING
from keyboards import get_keyboard_for_state
from messages import get_message_for_state
from validation import validate_with_gpt
from db_utils import get_database_connection, save_user_responses, get_user_saved_responses, fetch_insurance_plans
from user_data import user_responses, user_states, user_variables
from recommendation import recommend_insurance_plans

async def start_command(update: Update, context: CallbackContext) -> None:
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
    message = None
    
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
            if next_action == 'yes' or next_action == 'default_yes':
                saved_responses = context.user_data.get('saved_responses', {})
                user_responses[user_id] = saved_responses.copy()
                user_responses[user_id]['telegram_handle'] = f"@{context.user_data.get('username')}"
                user_variables[user_id]['chosen_default'] = True
            elif next_action == 'no' or next_action == 'default_no':
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
        
        print("Generating recommendations...")
        insurance_plans = fetch_insurance_plans()
        print(user_responses.get(user_id, {}))
        recommendations = recommend_insurance_plans(user_responses.get(user_id, {}), insurance_plans)
        
        if recommendations:
            recommendation_message = get_message_for_state(ConversationState.RECOMMENDATION, user_id) + '\n\n'
            for plan in recommendations:
                recommendation_message += (
                    f"{plan['name']} - ${plan['price']:.2f}\n"
                    f"Medical Coverage: ${plan['medical_coverage']:.2f}\n"
                    f"Trip Cancellation Coverage: ${plan['trip_cancellation_coverage']:.2f}\n"
                    f"Baggage Loss Coverage: ${plan['baggage_loss_coverage']:.2f}\n"
                    f"Baggage Delay Coverage: ${plan['baggage_delay_coverage']:.2f}\n"
                )
                if plan["emergency_evacuation"]:
                    recommendation_message += "Emergency Evacuation: Yes\n"
                recommendation_message += f"Buy Link: {plan['express_buy_link']}\n\n"
        else:
            recommendation_message = "No matching insurance plans found. Please adjust your preferences."
        
        message = recommendation_message

    user_states[user_id] = next_state
    print(f"Final next_state: {next_state}")
    
    message = message if message else get_message_for_state(next_state, user_id)
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
    callback_data = REVERSE_MAPPING.get(user_input)
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
            ("" if current_state == ConversationState.START else (validation_message + "\n\n")) + get_message_for_state(current_state, user_id),
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
    
    selected_option = RESPONSE_MAPPING.get(query.data, query.data)
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
