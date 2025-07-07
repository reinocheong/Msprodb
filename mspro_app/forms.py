from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateField, SelectField, FloatField, IntegerField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from .models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(id=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

class BookingForm(FlaskForm):
    unit_name = SelectField('房型', validators=[DataRequired()])
    checkin = DateField('入住日期', validators=[DataRequired()], format='%Y-%m-%d')
    checkout = DateField('退房日��', validators=[DataRequired()], format='%Y-%m-%d')
    channel = StringField('渠道')
    on_offline = SelectField('在线/离线', choices=[('Online', 'Online'), ('Offline', 'Offline')])
    pax = IntegerField('人数', validators=[DataRequired()])
    duration = IntegerField('天数', validators=[DataRequired()])
    price = FloatField('价格', validators=[DataRequired()])
    cleaning_fee = FloatField('打扫费', default=0.0)
    platform_charge = FloatField('平台费', default=0.0)
    total = FloatField('总收入', validators=[DataRequired()])
    submit = SubmitField('提交')

class ExpenseForm(FlaskForm):
    date = DateField('日期', validators=[DataRequired()], format='%Y-%m-%d')
    unit_name = SelectField('房型', validators=[DataRequired()])
    particulars = StringField('描述', validators=[DataRequired()])
    debit = FloatField('金额', validators=[DataRequired()])
    submit = SubmitField('提交')

class PasswordResetForm(FlaskForm):
    password = PasswordField('新密码', validators=[DataRequired()])
    password2 = PasswordField(
        '确认新密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('重置密码')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('当前密码', validators=[DataRequired()])
    new_password = PasswordField('新密码', validators=[DataRequired()])
    new_password2 = PasswordField(
        '确认新密码', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('修改密码')
