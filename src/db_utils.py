import os
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from typing import Optional
from conversation_states import ConversationState
from config import logger

def get_database_connection():
    try:
        database_url = os.getenv("DATABASE_URL")
        
        # If DATABASE_URL exists, use it for the connection
        if database_url:
            connection = psycopg2.connect(database_url, sslmode='require')
        else:
            # Fall back to individual parameters for local development
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

def fetch_insurance_plans():
    """Fetch all insurance plans from the database."""
    connection = get_database_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("SELECT * FROM insurance_details")
        plans = cursor.fetchall()
        return plans
    except Exception as e:
        print(f"Error fetching insurance plans: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

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
        
        print("BUDGET: " + budget)
        # Map budget values to database format
        budget_mapping = {
            'budget_50': 'Under $50',
            'budget_100': '$50 - $100',
            'budget_above': 'Above $100'
        }
        budget_value = budget_mapping.get(budget) if (budget in ['budget_50', 'budget_100', 'budget_above']) else budget
        print("BUDGET VALUE: " + budget_value)

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
                budget = %s
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
                medical_details, budget
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                budget_value
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
               budget
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
                '$50 - $100': 'budget_100',
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
                ConversationState.BUDGET: budget_mapping.get(result[6]) if (result[6] in ['Under $50', '$50 - $100', 'Above $100']) else result[6]
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching saved responses: {e}")
        return None