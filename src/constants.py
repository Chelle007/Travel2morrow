RESPONSE_MAPPING = {
    'explore': 'Explore travel insurance options',
    'manage': 'Manage existing insurance',
    'learn': 'Learn more about Travel2morrow',
    'default_yes': 'Yes, use default answers',
    'default_no': "No, don't use default answers",
    'solo': 'Solo traveler',
    'family': 'Family',
    'single': 'Single trip',
    'annual': 'Annual coverage',
    'adventure_yes': 'Yes, include extra protection',
    'adventure_no': "No, don't include extra protection",
    'medical_yes': 'Yes, I have pre-existing medical conditions',
    'medical_no': "No, I don't have pre-existing medical conditions",
    'budget_50': 'Under $50',
    'budget_100': '$50-$100',
    'budget_above': 'Above $100',
    'coverage_interruption': 'Trip Interruption',
    'coverage_luggage': 'Lost Luggage',
    'coverage_delays': 'Travel Delays',
    'coverage_none': 'No Additional Coverage',
    'go_back': '◀️ Go Back',
    'view_policy': 'View policy details',
    'update_policy': 'Update policy',
    'file_claim': 'File a claim'
}

REVERSE_MAPPING = {display: key for key, display in RESPONSE_MAPPING.items()}
