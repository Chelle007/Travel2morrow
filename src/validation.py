from openai import AsyncOpenAI
from datetime import datetime, timedelta
from conversation_states import ConversationState
from config import OPENAI_API_KEY, logger

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

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
        result = json.loads(response.choices[0].message.content)
        
        return (result["is_valid"], result["message"], result["processed_value"])

    except Exception as e:
        logger.error(f"Error in validate_with_gpt: {e}")
        return (False, "Sorry, I couldn't validate your input. Please try again.", None)
