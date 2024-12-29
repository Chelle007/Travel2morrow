-- Drop the existing users table if it exists
DROP TABLE IF EXISTS users;

-- Create the new users table with the who_traveling field
-- CREATE TYPE who_travelling_type AS ENUM ('solo', 'family');

CREATE TABLE users (
    user_id UUID PRIMARY KEY,                     -- Primary key, uniquely identifies the user
    telegram_handle VARCHAR(15) NOT NULL,         
	phone_number VARCHAR(15),
    who_travelling who_travelling_type NOT NULL DEFAULT 'solo',  -- Enum type for who is traveling (solo or family)
    trip_type VARCHAR(10) CHECK (trip_type IN ('single', 'annual')),  -- Trip type (single or annual)
    adventure_activities BOOLEAN NOT NULL,        -- Indicates if the user participates in adventure activities
    adventure_details TEXT,                       -- Details about the adventure activities
    medical_conditions BOOLEAN NOT NULL,          -- Indicates if the user has any medical conditions
    medical_details TEXT,                         -- Details about medical conditions
    budget VARCHAR(20),                           -- User's budget range
    additional_coverage TEXT,                    -- Additional coverage details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp when the record is created
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Timestamp for last update (can be used for auditing)
);

-- Add a trigger to automatically update 'updated_at' on row update
CREATE OR REPLACE FUNCTION update_users_updated_at() 
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at_trigger
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_users_updated_at();