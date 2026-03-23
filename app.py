from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for

from config import Config
from forms import AgentFilterForm, AuditForm, BandwidthForm, CalibrationSessionForm, FeedbackForm, LoginForm
from models import Agent, Audit, CalibrationSession, Feedback, QABandwidth, User, db
from modules.audit_engine import CapacityError, average_quality_score, create_audit, ensure_default_parameters, get_filtered_audits
from modules.calibration_engine import average_variance, calibration_alerts, create_session
from modules.feedback_tracker import create_feedback, repeated_feedback_alerts
from modules.qa_allocation import get_utilization_snapshot, upsert_bandwidth
from modules.reporting_engine import agent_score_trends, calibration_variance_report, export_agent_scores_csv, qa_performance
from utils import current_user, login_required, role_required


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    @app.context_processor
    def inject_user():
        return {'current_user': current_user()}

    @app.cli.command('seed-data')
    def seed_data_command():
        with app.app_context():
            seed_data()
            print('Seed data created.')

    @app.route('/')
    def index():
        if current_user():
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data.lower()).first()
            if user and user.check_password(form.password.data):
                session['user_id'] = user.id
                flash('Welcome back!', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid credentials.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been signed out.', 'info')
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        utilization = get_utilization_snapshot()
        bandwidth_form = BandwidthForm()
        bandwidth_form.auditor_id.choices = [(qa.id, qa.name) for qa in User.query.filter_by(role='QA').order_by(User.name)]
        total_audits = Audit.query.count()
        low_performers = (
            db.session.query(Agent)
            .join(Audit)
            .group_by(Agent.id)
            .having(db.func.avg(Audit.score) < 75)
            .all()
        )
        return render_template(
            'dashboard.html',
            avg_quality_score=average_quality_score(),
            total_audits=total_audits,
            avg_utilization=round(sum(item['utilization_pct'] for item in utilization) / len(utilization), 2) if utilization else 0,
            avg_variance=average_variance(),
            utilization=utilization,
            low_performers=low_performers,
            calibration_alerts=calibration_alerts(),
            feedback_alerts=repeated_feedback_alerts(),
            agent_trends=agent_score_trends(),
            qa_report=qa_performance(),
            calibration_report=calibration_variance_report(),
            bandwidth_form=bandwidth_form,
        )

    @app.route('/audits', methods=['GET', 'POST'])
    @role_required('Admin', 'QA')
    def audits():
        form = AuditForm()
        form.agent_id.choices = [(agent.id, f'{agent.name} ({agent.process})') for agent in Agent.query.order_by(Agent.name)]
        form.auditor_id.choices = [(qa.id, qa.name) for qa in User.query.filter_by(role='QA').order_by(User.name)]
        if request.method == 'GET' and not form.audit_date.data:
            form.audit_date.data = date.today()
        if form.validate_on_submit():
            raw_scores = {
                'Greeting': form.greeting.data,
                'Resolution': form.resolution.data,
                'Compliance': form.compliance.data,
                'Customer Experience': form.cx.data,
            }
            try:
                create_audit(form.agent_id.data, form.auditor_id.data, form.audit_date.data, raw_scores)
                flash('Audit created successfully.', 'success')
                return redirect(url_for('audits'))
            except CapacityError as exc:
                flash(str(exc), 'danger')
        page = request.args.get('page', 1, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        paginated_audits = get_filtered_audits(
            agent_id=request.args.get('agent_id', type=int),
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None,
            process=request.args.get('process'),
            page=page,
            per_page=app.config['ITEMS_PER_PAGE'],
        )
        return render_template('audits.html', form=form, paginated_audits=paginated_audits)

    @app.route('/agents')
    @login_required
    def agents():
        form = AgentFilterForm(request.args)
        managers = User.query.filter_by(role='Manager').order_by(User.name).all()
        form.manager_id.choices = [(0, 'All Managers')] + [(manager.id, manager.name) for manager in managers]
        query = Agent.query
        process = request.args.get('process', '').strip()
        manager_id = request.args.get('manager_id', type=int)
        if process:
            query = query.filter(Agent.process.ilike(f'%{process}%'))
        if manager_id:
            query = query.filter(Agent.manager_id == manager_id)
        page = request.args.get('page', 1, type=int)
        paginated_agents = query.order_by(Agent.name).paginate(page=page, per_page=app.config['ITEMS_PER_PAGE'], error_out=False)
        return render_template('agents.html', form=form, paginated_agents=paginated_agents)

    @app.route('/calibration', methods=['GET', 'POST'])
    @role_required('Admin', 'QA')
    def calibration():
        form = CalibrationSessionForm()
        form.auditor_id.choices = [(qa.id, qa.name) for qa in User.query.filter_by(role='QA').order_by(User.name)]
        if request.method == 'GET' and not form.session_date.data:
            form.session_date.data = date.today()
        if form.validate_on_submit():
            create_session(form.session_date.data, form.status.data, form.auditor_id.data, form.variance.data)
            flash('Calibration session recorded.', 'success')
            return redirect(url_for('calibration'))
        sessions = CalibrationSession.query.order_by(CalibrationSession.date.desc()).all()
        return render_template('calibration.html', form=form, sessions=sessions, alerts=calibration_alerts())

    @app.route('/feedback', methods=['GET', 'POST'])
    @role_required('Admin', 'QA', 'Manager')
    def feedback():
        form = FeedbackForm()
        form.agent_id.choices = [(agent.id, agent.name) for agent in Agent.query.order_by(Agent.name)]
        form.audit_id.choices = [(audit.id, f'Audit #{audit.id} - {audit.agent.name}') for audit in Audit.query.order_by(Audit.date.desc()).limit(200)]
        if request.method == 'GET' and not form.feedback_date.data:
            form.feedback_date.data = date.today()
        if form.validate_on_submit():
            create_feedback(form.agent_id.data, form.audit_id.data, form.feedback_text.data, form.severity.data, form.feedback_date.data)
            flash('Feedback logged successfully.', 'success')
            return redirect(url_for('feedback'))
        alerts = repeated_feedback_alerts()
        entries = Feedback.query.order_by(Feedback.date.desc()).limit(50).all()
        return render_template('feedback.html', form=form, entries=entries, alerts=alerts)

    @app.route('/bandwidth', methods=['POST'])
    @role_required('Admin')
    def bandwidth():
        form = BandwidthForm()
        form.auditor_id.choices = [(qa.id, qa.name) for qa in User.query.filter_by(role='QA').order_by(User.name)]
        if form.validate_on_submit():
            upsert_bandwidth(form.auditor_id.data, form.max_capacity.data, form.allocated.data)
            flash('Bandwidth updated.', 'success')
        else:
            flash('Unable to update bandwidth.', 'danger')
        return redirect(url_for('dashboard'))

    @app.route('/reports/agents.csv')
    @login_required
    def export_agents_csv():
        csv_payload = export_agent_scores_csv()
        return Response(
            csv_payload,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=agent_scores.csv'},
        )

    @app.route('/init-db')
    def init_db_route():
        initialize_database()
        flash('Database initialized.', 'success')
        return redirect(url_for('login'))

    return app


def initialize_database():
    db.create_all()
    ensure_default_parameters()
    if not User.query.filter_by(email='admin@qcc.local').first():
        admin = User(name='QCC Admin', role='Admin', email='admin@qcc.local')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()


def seed_data():
    initialize_database()
    if User.query.filter(User.role == 'QA').count() >= 5:
        return

    managers = []
    for index in range(1, 4):
        manager = User(name=f'Manager {index}', role='Manager', email=f'manager{index}@qcc.local')
        manager.set_password('password123')
        managers.append(manager)
        db.session.add(manager)

    qas = []
    for index in range(1, 6):
        qa = User(name=f'QA {index}', role='QA', email=f'qa{index}@qcc.local')
        qa.set_password('password123')
        qas.append(qa)
        db.session.add(qa)
    db.session.commit()

    processes = ['Voice', 'Chat', 'Email', 'Back Office']
    agents = []
    for index in range(1, 21):
        agent = Agent(name=f'Agent {index}', process=random.choice(processes), manager_id=random.choice(managers).id)
        agents.append(agent)
        db.session.add(agent)
    db.session.commit()

    for qa in qas:
        db.session.add(QABandwidth(auditor_id=qa.id, max_capacity=35, allocated=0))
    db.session.commit()

    for _ in range(100):
        agent = random.choice(agents)
        qa = random.choice(qas)
        bandwidth = QABandwidth.query.filter_by(auditor_id=qa.id).first()
        if bandwidth.allocated + 1 > bandwidth.max_capacity * 0.9:
            continue
        raw_scores = {
            'Greeting': random.randint(70, 100),
            'Resolution': random.randint(65, 100),
            'Compliance': random.randint(60, 100),
            'Customer Experience': random.randint(68, 100),
        }
        create_audit(
            agent.id,
            qa.id,
            date.today() - timedelta(days=random.randint(0, 60)),
            raw_scores,
        )

    audit_records = Audit.query.limit(30).all()
    for idx, audit in enumerate(audit_records, start=1):
        create_feedback(
            audit.agent_id,
            audit.id,
            f'Coaching feedback item {idx % 5}',
            random.choice(['Low', 'Medium', 'High']),
            audit.date,
        )

    for qa in qas:
        create_session(date.today() - timedelta(days=random.randint(0, 30)), 'Closed', qa.id, random.randint(4, 16))


app = create_app()

with app.app_context():
    initialize_database()
