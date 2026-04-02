def generate_smart_recommendations(student):
    recs = []
    score = student["score"]
    clicks = student["clicks"]
    risk = student["risk"]

    if score == 0:
        recs.append(
            "URGENT: No academic record found. "
            "Please verify if the student has submitted any assignments."
        )
    elif score < 40:
        recs.append(
            f"Critical Academic Alert: Current average ({score:.1f}) is failing. "
            "Immediate intervention required."
        )
    elif 40 <= score < 60:
        recs.append(
            f"Warning: Score ({score:.1f}) is borderline pass. "
            "Focus on upcoming quizzes to improve safety margin."
        )
    elif score >= 90:
        recs.append(
            "Achievement: Outstanding academic performance. "
            "Consider this student for peer-tutoring roles."
        )

    if clicks < 10:
        recs.append(
            "Disengagement Alert: Almost zero interaction with VLE. "
            "Check for login issues or withdrawal intent."
        )
    elif clicks < 50:
        recs.append(
            f"Low Activity: Only {int(clicks)} clicks recorded. "
            "Encourage viewing lecture materials and forums."
        )
    elif clicks > 500:
        recs.append(
            "High Engagement: Student is very active. "
            "Ensure this effort translates into assessment results."
        )

    if risk == 1:
        if score > 70:
            recs.append(
                "Anomaly Detected: Student has good scores but is predicted 'High Risk'. "
                "Likely due to sudden drop in recent activity."
            )
        if clicks > 200 and score < 50:
            recs.append(
                "Efficiency Issue: High effort (clicks) but low scores. "
                "Student may be struggling to understand the material."
            )
        if not recs:
            recs.append(
                "General Risk: The predictive model indicates a high probability of dropout "
                "based on historical patterns."
            )

    if risk == 0 and not recs:
        recs.append("Student is on track. No specific interventions needed at this time.")

    return recs