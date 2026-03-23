from flask_wtf import FlaskForm
from wtforms import DateField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.fields import FloatField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign in')


class AuditForm(FlaskForm):
    agent_id = SelectField('Agent', coerce=int, validators=[DataRequired()])
    auditor_id = SelectField('QA Auditor', coerce=int, validators=[DataRequired()])
    audit_date = DateField('Audit Date', validators=[DataRequired()])
    process = StringField('Process filter', validators=[Optional(), Length(max=120)])
    greeting = FloatField('Greeting', validators=[DataRequired(), NumberRange(min=0, max=100)])
    resolution = FloatField('Resolution', validators=[DataRequired(), NumberRange(min=0, max=100)])
    compliance = FloatField('Compliance', validators=[DataRequired(), NumberRange(min=0, max=100)])
    cx = FloatField('Customer Experience', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Create audit')


class FeedbackForm(FlaskForm):
    agent_id = SelectField('Agent', coerce=int, validators=[DataRequired()])
    audit_id = SelectField('Audit', coerce=int, validators=[DataRequired()])
    feedback_text = TextAreaField('Feedback', validators=[DataRequired(), Length(min=5, max=500)])
    severity = SelectField(
        'Severity', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], validators=[DataRequired()]
    )
    feedback_date = DateField('Date', validators=[DataRequired()])
    submit = SubmitField('Log feedback')


class CalibrationSessionForm(FlaskForm):
    session_date = DateField('Session Date', validators=[DataRequired()])
    status = SelectField(
        'Status', choices=[('Open', 'Open'), ('Closed', 'Closed')], validators=[DataRequired()]
    )
    auditor_id = SelectField('Auditor', coerce=int, validators=[DataRequired()])
    variance = FloatField('Variance %', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Save calibration')


class AgentFilterForm(FlaskForm):
    process = StringField('Process', validators=[Optional()])
    manager_id = SelectField('Manager', coerce=int, validators=[Optional()], choices=[])
    submit = SubmitField('Filter')


class BandwidthForm(FlaskForm):
    auditor_id = SelectField('QA Auditor', coerce=int, validators=[DataRequired()])
    max_capacity = IntegerField('Max Capacity', validators=[DataRequired(), NumberRange(min=1, max=10000)])
    allocated = IntegerField('Allocated', validators=[DataRequired(), NumberRange(min=0, max=10000)])
    submit = SubmitField('Save bandwidth')
