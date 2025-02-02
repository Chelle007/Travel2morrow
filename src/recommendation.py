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

    # Filter plans based on user preferences
    for plan in insurance_plans:
        # Filter plans based on trip type
        # if trip_type and plan["plan_type"] != trip_type:
        #     continue

        # Filter plans based on medical coverage (if user has medical conditions)
        if medical_conditions == "Yes" and plan["medical_coverage"] == 0:
            continue

        # Filter plans based on adventure activities coverage
        # if adventure_activities == "Yes" and not plan["emergency_evacuation"]:
        #     continue

        # If the plan passes all filters, add it to recommendations
        recommendations.append(plan)

    # Parse custom budget range if provided
    if isinstance(budget, str) and ("to" in budget.lower() or "-" in budget):
        try:
            lower_bound, upper_bound = map(float, budget.lower().replace("around", "").replace("to", "").replace("-", "").replace("$", "").split())
        except ValueError:
            lower_bound, upper_bound = None, None
    elif isinstance(budget, str) and ("under" in budget.lower()):
        try:
            lower_bound = float(budget.lower().replace("under", "").replace(" ", "").replace("$", ""))
            upper_bound = None
        except ValueError:
            lower_bound, upper_bound = None, None
    elif isinstance(budget, str) and ("above" in budget.lower()):
        try: 
            upper_bound = float(budget.lower().replace("above", "").replace(" ", "").replace("$", ""))
            lower_bound = None
        except ValueError:
            lower_bound, upper_bound = None, None
    else:
        lower_bound, upper_bound = None, None

    # Filter plans based on budget
    if lower_bound is not None and upper_bound is not None:
        priority_plans = [plan for plan in recommendations if lower_bound <= plan["price"] <= upper_bound]
        if not priority_plans:
            recommendations = [plan for plan in recommendations if plan["price"] < lower_bound]
        else:
            recommendations = priority_plans
    elif lower_bound is not None:
        recommendations = [plan for plan in recommendations if plan["price"] < lower_bound]
    elif upper_bound is not None:
        priority_plans = [plan for plan in recommendations if plan["price"] >= upper_bound]
        if not priority_plans:
            recommendations = [plan for plan in recommendations if plan["price"] < upper_bound]
        else:
            recommendations = priority_plans

    # If no plans match the budget, return an empty list
    if not recommendations:
        return []

    # Calculate total coverage for each plan
    for plan in recommendations:
        plan["total_coverage"] = (
            plan["medical_coverage"] +
            plan["trip_cancellation_coverage"] +
            plan["baggage_loss_coverage"] +
            plan["baggage_delay_coverage"]
        )

    # Sort recommendations by total coverage (descending) and price (ascending)
    recommendations.sort(key=lambda x: (-x["total_coverage"], x["price"]))

    # Return only the top 3 plans
    return recommendations[:3]