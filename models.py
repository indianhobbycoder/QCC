from __future__ import annotations

from datetime import date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, event
from sqlalchemy.engine import Engine
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


@event.listens_for(Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


class TimestampMixin:
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )


class User(TimestampMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    managed_agents = db.relationship('Agent', back_populates='manager', lazy=True)
    audits_conducted = db.relationship('Audit', back_populates='auditor', lazy=True)
    calibration_scores = db.relationship('CalibrationScore', back_populates='auditor', lazy=True)
    bandwidth = db.relationship('QABandwidth', back_populates='auditor', uselist=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Agent(TimestampMixin, db.Model):
    __tablename__ = 'agents'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    process = db.Column(db.String(120), nullable=False, index=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))

    manager = db.relationship('User', back_populates='managed_agents')
    audits = db.relationship('Audit', back_populates='agent', lazy=True, cascade='all, delete-orphan')
    feedback_entries = db.relationship(
        'Feedback', back_populates='agent', lazy=True, cascade='all, delete-orphan'
    )


class Audit(TimestampMixin, db.Model):
    __tablename__ = 'audits'

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    parameters_json = db.Column(db.JSON, nullable=False)

    agent = db.relationship('Agent', back_populates='audits')
    auditor = db.relationship('User', back_populates='audits_conducted')
    feedback_entries = db.relationship(
        'Feedback', back_populates='audit', lazy=True, cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('idx_audits_agent_id', 'agent_id'),
        Index('idx_audits_agent_date', 'agent_id', 'date'),
    )


class Parameter(TimestampMixin, db.Model):
    __tablename__ = 'parameters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    weight = db.Column(db.Float, nullable=False)


class Feedback(TimestampMixin, db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    audit_id = db.Column(db.Integer, db.ForeignKey('audits.id', ondelete='CASCADE'), nullable=False)
    feedback_text = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(30), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)

    agent = db.relationship('Agent', back_populates='feedback_entries')
    audit = db.relationship('Audit', back_populates='feedback_entries')


class CalibrationSession(TimestampMixin, db.Model):
    __tablename__ = 'calibration_sessions'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(30), nullable=False, default='Open')

    scores = db.relationship(
        'CalibrationScore', back_populates='session', lazy=True, cascade='all, delete-orphan'
    )


class CalibrationScore(TimestampMixin, db.Model):
    __tablename__ = 'calibration_scores'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey('calibration_sessions.id', ondelete='CASCADE'), nullable=False
    )
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    variance = db.Column(db.Float, nullable=False)

    session = db.relationship('CalibrationSession', back_populates='scores')
    auditor = db.relationship('User', back_populates='calibration_scores')


class QABandwidth(TimestampMixin, db.Model):
    __tablename__ = 'qa_bandwidth'

    id = db.Column(db.Integer, primary_key=True)
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    max_capacity = db.Column(db.Integer, nullable=False)
    allocated = db.Column(db.Integer, nullable=False, default=0)

    auditor = db.relationship('User', back_populates='bandwidth')

    @property
    def utilization_pct(self) -> float:
        if not self.max_capacity:
            return 0.0
        return round((self.allocated / self.max_capacity) * 100, 2)
