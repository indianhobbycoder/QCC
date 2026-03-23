from __future__ import annotations

from sqlalchemy import func

from models import CalibrationScore, CalibrationSession, db


def create_session(session_date, status, auditor_id, variance):
    session = CalibrationSession(date=session_date, status=status)
    db.session.add(session)
    db.session.flush()
    score = CalibrationScore(session_id=session.id, auditor_id=auditor_id, variance=variance)
    db.session.add(score)
    db.session.commit()
    return session


def calibration_alerts() -> list[CalibrationScore]:
    return CalibrationScore.query.filter(CalibrationScore.variance > 10).order_by(CalibrationScore.created_at.desc()).all()


def average_variance() -> float:
    avg = db.session.query(func.avg(CalibrationScore.variance)).scalar() or 0
    return round(float(avg), 2)
