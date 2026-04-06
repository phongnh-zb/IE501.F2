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

    # ── Tier 3: Critical ─────────────────────────────────────────────────────
    if risk == 3:
        if withdrew_early:
            recs.append(
                "Student has formally unregistered. "
                "Immediate personal outreach is required to understand the reason and explore re-engagement."
            )
        else:
            recs.append(
                "Critical risk level detected. Multiple severe signals present — "
                "escalate to personal contact within 48 hours."
            )
        if score < 40:
            recs.append(
                f"Average score is {score:.1f} — well below the passing threshold. "
                "Academic counselling and catch-up sessions are strongly recommended."
            )
        if submission_rate < 0.25:
            recs.append(
                f"Only {submission_rate:.0%} of assessments submitted. "
                "Check for technical access issues or personal circumstances affecting participation."
            )
        if prev_attempts >= 2:
            recs.append(
                f"This is attempt #{prev_attempts + 1} at this module. "
                "Review prior support records and tailor intervention accordingly."
            )
        return recs

    # ── Tier 2: High Risk ────────────────────────────────────────────────────
    if risk == 2:
        recs.append(
            "Predicted high dropout risk. Active academic support is recommended before the next assessment deadline."
        )
        if score < 60:
            recs.append(
                f"Score of {score:.1f} indicates consistent underperformance. "
                "Consider structured study sessions or peer-tutoring."
            )
        if submission_rate < 0.6:
            recs.append(
                f"Submission rate at {submission_rate:.0%}. "
                "Missing assessments compound dropout risk — encourage submissions even if incomplete."
            )
        if avg_days_early < -3:
            recs.append(
                f"Assessments submitted on average {abs(avg_days_early):.1f} days late. "
                "Work with the student on deadline management."
            )
        if clicks > 200 and score < 50:
            recs.append(
                "High VLE activity but low scores — the student may be struggling to convert effort into results. "
                "A one-to-one tutorial is recommended."
            )
        if forum_clicks < 5:
            recs.append(
                "Very low forum engagement. Peer learning has been linked to better retention — "
                "prompt the student to join study groups."
            )
        return recs

    # ── Tier 1: Watch ────────────────────────────────────────────────────────
    if risk == 1:
        recs.append(
            "Student is on a passing trajectory but showing early warning signals. "
            "Light-touch check-in recommended in the next two weeks."
        )
        if score < 60:
            recs.append(
                f"Score of {score:.1f} is below the comfortable passing margin. "
                "Encourage focus on upcoming assessments."
            )
        if submission_rate < 0.6:
            recs.append(
                f"Submission rate at {submission_rate:.0%}. "
                "Remind the student of upcoming deadlines and the impact of missing work."
            )
        if active_days < 10:
            recs.append(
                f"Only {active_days} active day(s) in the VLE. "
                "Encourage consistent, regular engagement with course materials."
            )
        if avg_days_early < -7:
            recs.append(
                "Pattern of late submissions detected. "
                "A brief conversation about workload management may help."
            )
        if not recs or len(recs) == 1:
            recs.append(
                "No immediate action required, but continue monitoring engagement over the next module weeks."
            )
        return recs

    # ── Tier 0: Safe ─────────────────────────────────────────────────────────
    if score >= 90:
        recs.append(
            "Outstanding performance. "
            "Consider this student for peer-tutoring or advanced challenge tasks."
        )
    elif active_days > 0:
        recs.append("Student is on track. No interventions needed at this time.")
    else:
        recs.append("No activity recorded yet. Verify the student has accessed the course materials.")

    return recs