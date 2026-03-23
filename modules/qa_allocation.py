from __future__ import annotations

from models import QABandwidth, User, db


def upsert_bandwidth(auditor_id: int, max_capacity: int, allocated: int) -> QABandwidth:
    bandwidth = QABandwidth.query.filter_by(auditor_id=auditor_id).first()
    if bandwidth is None:
        bandwidth = QABandwidth(auditor_id=auditor_id, max_capacity=max_capacity, allocated=allocated)
        db.session.add(bandwidth)
    else:
        bandwidth.max_capacity = max_capacity
        bandwidth.allocated = allocated
    db.session.commit()
    return bandwidth


def get_utilization_snapshot() -> list[dict]:
    rows = []
    for bandwidth in QABandwidth.query.join(User).order_by(User.name).all():
        rows.append(
            {
                'auditor': bandwidth.auditor.name,
                'allocated': bandwidth.allocated,
                'max_capacity': bandwidth.max_capacity,
                'utilization_pct': bandwidth.utilization_pct,
                'threshold_breached': bandwidth.utilization_pct >= 90,
            }
        )
    return rows
