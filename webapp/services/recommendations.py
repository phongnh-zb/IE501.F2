def generate_smart_recommendations(student):
    recs = []
    score           = student.get("score", 0)
    clicks          = student.get("clicks", 0)
    risk            = student.get("risk", 0)
    active_days     = student.get("active_days", 0)
    submission_rate = student.get("submission_rate", 0)
    withdrew_early  = student.get("withdrew_early", 0)
    prev_attempts   = student.get("num_prev_attempts", 0)
    avg_days_early  = student.get("avg_days_early", 0)
    forum_clicks    = student.get("forum_clicks", 0)

    # Withdrawal — highest priority
    if withdrew_early:
        recs.append(
            "Student has formally unregistered from this module. "
            "Immediate outreach recommended to understand the reason."
        )
        return recs

    # Previous attempts
    if prev_attempts >= 2:
        recs.append(
            f"Repeat attempt #{prev_attempts + 1}. "
            "Review what interventions were tried in prior presentations."
        )

    # Score signals
    if score == 0:
        recs.append(
            "No academic record found. "
            "Verify whether the student has submitted any assessments."
        )
    elif score < 40:
        recs.append(
            f"Critical: average score {score:.1f} is below passing threshold. "
            "Immediate academic support required."
        )
    elif score < 60:
        recs.append(
            f"Score {score:.1f} is borderline. "
            "Focus on upcoming assessments to build a safety margin."
        )
    elif score >= 90:
        recs.append(
            "Outstanding academic performance. "
            "Consider this student for peer-tutoring or advanced challenges."
        )

    # VLE engagement
    if clicks < 10:
        recs.append(
            "Almost zero VLE interaction recorded. "
            "Check for login issues or early disengagement."
        )
    elif active_days < 5:
        recs.append(
            f"Only {active_days} active day(s) in the VLE. "
            "Encourage regular, consistent engagement with course materials."
        )

    # Forum engagement
    if forum_clicks < 5 and risk == 1:
        recs.append(
            "Very low forum activity. "
            "Peer discussion has been linked to better retention — prompt the student to engage."
        )

    # Submission behaviour
    if submission_rate == 0:
        recs.append(
            "No assessments submitted. "
            "Contact the student urgently to clarify their situation."
        )
    elif submission_rate < 0.5:
        recs.append(
            f"Submission rate is {submission_rate:.0%}. "
            "Missing assessments significantly increase dropout risk."
        )

    # Late submission pattern
    if avg_days_early < -3:
        recs.append(
            f"Assessments submitted on average {abs(avg_days_early):.1f} days late. "
            "Work with the student on time management and deadline awareness."
        )

    # Anomaly: high score but still at risk
    if risk == 1 and score > 70:
        recs.append(
            "Good scores but predicted high risk — likely caused by a recent sharp drop "
            "in activity. Monitor engagement closely over the next two weeks."
        )

    # High effort, low output
    if risk == 1 and clicks > 200 and score < 50:
        recs.append(
            "High VLE activity but low scores suggest the student is struggling "
            "to convert effort into results. Consider a one-to-one tutorial."
        )

    # Default safe message
    if risk == 0 and not recs:
        recs.append("Student is on track. No interventions needed at this time.")

    # Fallback risk message
    if risk == 1 and not recs:
        recs.append(
            "Predicted high dropout risk based on combined behavioural signals. "
            "Proactive contact is recommended."
        )

    return recs