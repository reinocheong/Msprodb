from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.String(80), primary_key=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(80), nullable=False, default='owner')
    allowed_units = db.Column(db.JSON, nullable=True, default=[])
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_id(self):
        return self.id

class Booking(db.Model):
    id = db.Column(db.String(80), primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_name = db.Column(db.String(120))
    checkin = db.Column(db.Date)
    checkout = db.Column(db.Date)
    channel = db.Column(db.String(80))
    on_offline = db.Column(db.String(80))
    booking_number = db.Column(db.String(100), nullable=True) # Keep this from our previous step
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