from __future__ import annotations

import csv
from io import StringIO
from sqlalchemy import func

from models import Agent, Audit, CalibrationScore, User, db


def agent_score_trends():
    rows = (
        db.session.query(Agent.name, func.avg(Audit.score))
        .join(Audit)
        .group_by(Agent.id)
        .order_by(func.avg(Audit.score).desc())
        .all()
    )
    return [{'label': name, 'value': round(float(score), 2)} for name, score in rows]


def qa_performance():
    rows = (
        db.session.query(User.name, func.avg(Audit.score), func.count(Audit.id))
        .join(Audit, Audit.auditor_id == User.id)
        .filter(User.role == 'QA')
        .group_by(User.id)
        .order_by(User.name)
        .all()
    )
    return [
        {'label': name, 'avg_score': round(float(avg_score), 2), 'audits': count}
        for name, avg_score, count in rows
    ]


def calibration_variance_report():
    rows = (
        db.session.query(User.name, func.avg(CalibrationScore.variance))
        .join(CalibrationScore, CalibrationScore.auditor_id == User.id)
        .group_by(User.id)
        .all()
    )
    return [{'label': name, 'value': round(float(variance), 2)} for name, variance in rows]


def export_agent_scores_csv():
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Agent', 'Average Score'])
    for row in agent_score_trends():
        writer.writerow([row['label'], row['value']])
    return buffer.getvalue()
