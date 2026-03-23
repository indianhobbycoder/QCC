from __future__ import annotations

from sqlalchemy import func

from models import Agent, Audit, Parameter, QABandwidth, User, db


DEFAULT_PARAMETER_WEIGHTS = {
    'Greeting': 0.15,
    'Resolution': 0.35,
    'Compliance': 0.30,
    'Customer Experience': 0.20,
}


class CapacityError(ValueError):
    pass


def ensure_default_parameters() -> None:
    for name, weight in DEFAULT_PARAMETER_WEIGHTS.items():
        existing = Parameter.query.filter_by(name=name).first()
        if not existing:
            db.session.add(Parameter(name=name, weight=weight))
    db.session.commit()


def calculate_weighted_score(raw_scores: dict[str, float]) -> tuple[float, list[dict]]:
    parameters = Parameter.query.all()
    if not parameters:
        ensure_default_parameters()
        parameters = Parameter.query.all()
    total = 0.0
    breakdown = []
    for parameter in parameters:
        value = float(raw_scores.get(parameter.name, 0))
        weighted = value * parameter.weight
        total += weighted
        breakdown.append(
            {
                'parameter': parameter.name,
                'weight': parameter.weight,
                'score': value,
                'weighted_score': round(weighted, 2),
            }
        )
    return round(total, 2), breakdown


def check_bandwidth(auditor_id: int) -> QABandwidth:
    bandwidth = QABandwidth.query.filter_by(auditor_id=auditor_id).first()
    if not bandwidth:
        raise CapacityError('No QA bandwidth configuration found for selected auditor.')
    projected = bandwidth.allocated + 1
    if projected > bandwidth.max_capacity * 0.9:
        raise CapacityError('QA auditor exceeds the 90% governance utilization threshold.')
    return bandwidth


def create_audit(agent_id: int, auditor_id: int, audit_date, raw_scores: dict[str, float]) -> Audit:
    bandwidth = check_bandwidth(auditor_id)
    score, breakdown = calculate_weighted_score(raw_scores)
    audit = Audit(
        agent_id=agent_id,
        auditor_id=auditor_id,
        date=audit_date,
        score=score,
        parameters_json=breakdown,
    )
    bandwidth.allocated += 1
    db.session.add(audit)
    db.session.commit()
    return audit


def get_filtered_audits(agent_id=None, start_date=None, end_date=None, process=None, page=1, per_page=10):
    query = Audit.query.join(Agent).join(User, Audit.auditor_id == User.id)
    if agent_id:
        query = query.filter(Audit.agent_id == agent_id)
    if start_date:
        query = query.filter(Audit.date >= start_date)
    if end_date:
        query = query.filter(Audit.date <= end_date)
    if process:
        query = query.filter(Agent.process.ilike(f'%{process}%'))
    return query.order_by(Audit.date.desc()).paginate(page=page, per_page=per_page, error_out=False)


def average_quality_score() -> float:
    avg = db.session.query(func.avg(Audit.score)).scalar() or 0
    return round(float(avg), 2)
