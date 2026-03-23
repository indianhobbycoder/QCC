from __future__ import annotations

from collections import Counter

from models import Feedback, db


def create_feedback(agent_id, audit_id, feedback_text, severity, feedback_date):
    feedback = Feedback(
        agent_id=agent_id,
        audit_id=audit_id,
        feedback_text=feedback_text,
        severity=severity,
        date=feedback_date,
    )
    db.session.add(feedback)
    db.session.commit()
    return feedback


def repeated_feedback_alerts():
    feedback_items = Feedback.query.order_by(Feedback.date.desc()).all()
    counter = Counter(item.agent_id for item in feedback_items)
    alerts = []
    for item in feedback_items:
        repeats = counter[item.agent_id]
        if repeats >= 2:
            alerts.append(
                {
                    'agent': item.agent.name,
                    'feedback_text': item.feedback_text,
                    'repeats': repeats,
                    'action': 'PIP' if repeats >= 3 else 'Training',
                }
            )
            counter[item.agent_id] = 0
    return alerts
