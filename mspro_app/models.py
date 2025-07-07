from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer
import time

class User(UserMixin, db.Model):
    id = db.Column(db.String(80), primary_key=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(80), nullable=False, default='owner')
    allowed_units = db.Column(db.JSON, nullable=True, default=[])
    management_fee_percentage = db.Column(db.Float, nullable=False, default=30.0)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_id(self):
        return self.id

    def get_reset_password_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_password_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_sec)
            user_id = data.get('user_id')
        except Exception:
            return None
        return User.query.get(user_id)


class Booking(db.Model):
    id = db.Column(db.String(80), primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_name = db.Column(db.String(120))
    checkin = db.Column(db.Date)
    checkout = db.Column(db.Date)
    channel = db.Column(db.String(80))
    on_offline = db.Column(db.String(80))
    booking_number = db.Column(db.String(100), nullable=True)
    pax = db.Column(db.Integer)
    duration = db.Column(db.Integer)
    price = db.Column(db.Float)
    cleaning_fee = db.Column(db.Float)
    platform_charge = db.Column(db.Float)
    total = db.Column(db.Float)

class Expense(db.Model):
    id = db.Column(db.String(80), primary_key=True, default=lambda: str(uuid.uuid4()))
    date = db.Column(db.Date)
    unit_name = db.Column(db.String(120))
    particulars = db.Column(db.String(200))
    debit = db.Column(db.Float)