def recommend_insurance_plans(user_responses, insurance_plans):
    """
    Generate insurance recommendations based on user responses and available plans.
    
    :param user_responses: Dictionary containing user's responses (e.g., budget, trip type, etc.)
    :param insurance_plans: List of insurance plans fetched from the database
    :return: List of recommended insurance plans (max 3)
    """
    recommendations = []

    # Extract user preferences
    budget = user_responses.get("budget")
    trip_type = user_responses.get("trip_type")
    medical_conditions = user_responses.get("medical_conditions")
    adventure_activities = user_responses.get("adventure_activities")

    for plan in insurance_plans:
        # Filter plans based on budget
        if budget and plan["price"] > budget:
            continue

        # Filter plans based on trip type
        if trip_type and plan["plan_type"] != trip_type:
            continue

        # Filter plans based on medical coverage (if user has medical conditions)
        if medical_conditions == "Yes" and plan["medical_coverage"] == 0:
            continue

        # Filter plans based on adventure activities coverage
        if adventure_activities == "Yes" and not plan["emergency_evacuation"]:
            continue

        # If the plan passes all filters, add it to recommendations
        recommendations.append(plan)

    # Sort recommendations by price (ascending)
    recommendations.sort(key=lambda x: x["price"])

    # Return only the top 3 plans
    return recommendations[:3]