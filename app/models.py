from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # NEW: Dynamic Rate Card (Default is 70 if not specified)
    rate_per_parcel = db.Column(db.Float, default=70.0) 

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    bill_no = db.Column(db.String(50), default='-')
    rr_no = db.Column(db.String(50), default='-')
    vendor = db.Column(db.String(100), nullable=False)
    ship_from = db.Column(db.String(50), default='Udupi')
    ship_to = db.Column(db.String(50), default='Mumbai')
    parcels = db.Column(db.Integer, default=0)
    handling_chg = db.Column(db.Float, default=0.0)
    railway_chg = db.Column(db.Float, default=0.0)
    transport_chg = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)