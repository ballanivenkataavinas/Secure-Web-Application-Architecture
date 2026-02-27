from datetime import datetime, timedelta

# Store recent offenses in memory (lightweight, safe)
user_recent_activity = {}


def time_based_escalation(score):
    current_hour = datetime.now().hour

    # 12 AM – 5 AM stricter
    if 0 <= current_hour < 5:
        score += 1

    return score


def repeat_escalation(user_id: str, score):
    now = datetime.now()

    if user_id in user_recent_activity:
        last_time = user_recent_activity[user_id]

        # If repeated within 10 minutes → multiply
        if now - last_time < timedelta(minutes=10):
            score *= 1.5

    # Update timestamp
    user_recent_activity[user_id] = now

    return score