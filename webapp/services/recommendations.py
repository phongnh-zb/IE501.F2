def generate_smart_recommendations(student):
    score           = student.get("score", 0)
    clicks          = student.get("clicks", 0)
    risk            = student.get("risk", 0)
    active_days     = student.get("active_days", 0)
    submission_rate = student.get("submission_rate", 0)
    withdrew_early  = student.get("withdrew_early", 0)
    prev_attempts   = student.get("num_prev_attempts", 0)
    avg_days_early  = student.get("avg_days_early", 0)
    forum_clicks    = student.get("forum_clicks", 0)

    def rec(text, level):
        return {"text": text, "level": level}

    recs = []

    # ── Tier 3: Critical ──────────────────────────────────────────────────────
    if risk == 3:
        if withdrew_early:
            recs.append(rec(
                "Student has formally unregistered. Immediate personal outreach "
                "is required to understand the reason and explore re-engagement.",
                "crit",
            ))
        else:
            recs.append(rec(
                "Multiple severe risk signals detected. Escalate to personal "
                "contact within 48 hours.",
                "crit",
            ))
        if score < 40:
            recs.append(rec(
                f"Average score is {score:.1f} — well below the passing threshold. "
                "Academic counselling and catch-up sessions are strongly recommended.",
                "crit",
            ))
        if submission_rate < 0.25:
            recs.append(rec(
                f"Only {submission_rate:.0%} of assessments submitted. "
                "Check for access issues or personal circumstances affecting participation.",
                "high",
            ))
        if prev_attempts >= 2:
            recs.append(rec(
                f"This is attempt #{prev_attempts + 1} at this module. "
                "Review prior support records and tailor the intervention accordingly.",
                "high",
            ))
        return recs

    # ── Tier 2: High Risk ─────────────────────────────────────────────────────
    if risk == 2:
        recs.append(rec(
            "High dropout risk predicted. Active academic support is recommended "
            "before the next assessment deadline.",
            "high",
        ))
        if score < 60:
            recs.append(rec(
                f"Score of {score:.1f} indicates consistent underperformance. "
                "Consider structured study sessions or peer-tutoring.",
                "high",
            ))
        if submission_rate < 0.6:
            recs.append(rec(
                f"Submission rate at {submission_rate:.0%}. "
                "Encourage submissions even if incomplete — missed work compounds risk.",
                "high",
            ))
        if avg_days_early < -3:
            recs.append(rec(
                f"Assessments submitted on average {abs(avg_days_early):.1f} days late. "
                "Work with the student on deadline management strategies.",
                "watch",
            ))
        if clicks > 200 and score < 50:
            recs.append(rec(
                "High VLE activity but low scores — the student may be struggling to "
                "convert effort into results. A one-to-one tutorial is recommended.",
                "watch",
            ))
        if forum_clicks < 5:
            recs.append(rec(
                "Very low forum engagement. Peer learning improves retention — "
                "prompt the student to join study groups.",
                "watch",
            ))
        return recs

    # ── Tier 1: Watch ─────────────────────────────────────────────────────────
    if risk == 1:
        recs.append(rec(
            "Student is on a passing trajectory but showing early warning signals. "
            "A light-touch check-in is recommended in the next two weeks.",
            "watch",
        ))
        if score < 60:
            recs.append(rec(
                f"Score of {score:.1f} is below the comfortable passing margin. "
                "Encourage focus on upcoming assessments.",
                "watch",
            ))
        if submission_rate < 0.6:
            recs.append(rec(
                f"Submission rate at {submission_rate:.0%}. "
                "Remind the student of upcoming deadlines and the impact of missing work.",
                "watch",
            ))
        if active_days < 10:
            recs.append(rec(
                f"Only {active_days} active day(s) in the VLE. "
                "Encourage consistent, regular engagement with course materials.",
                "watch",
            ))
        if avg_days_early < -7:
            recs.append(rec(
                "Pattern of late submissions detected. "
                "A brief conversation about workload management may help.",
                "watch",
            ))
        if len(recs) == 1:
            recs.append(rec(
                "No immediate action required. Continue monitoring engagement "
                "over the next module weeks.",
                "safe",
            ))
        return recs

    # ── Tier 0: Safe ──────────────────────────────────────────────────────────
    if score >= 90:
        recs.append(rec(
            "Outstanding performance. Consider this student for peer-tutoring "
            "or advanced challenge tasks.",
            "safe",
        ))
    elif active_days > 0:
        recs.append(rec("Student is on track. No interventions needed at this time.", "safe"))
    else:
        recs.append(rec(
            "No activity recorded yet. Verify the student has accessed the course materials.",
            "watch",
        ))

    return recs