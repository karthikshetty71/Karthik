# app/models.py

from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rate_per_parcel = db.Column(db.Float, default=70.0)
    transport_rate = db.Column(db.Float, default=0.0)

    # Billing Details
    billing_name = db.Column(db.String(150))
    billing_address = db.Column(db.String(255))

    # Toggles (You can keep these or ignore them)
    show_rr = db.Column(db.Boolean, default=True)
    show_handling = db.Column(db.Boolean, default=True)
    show_railway = db.Column(db.Boolean, default=True)
    show_transport = db.Column(db.Boolean, default=True)

    is_default = db.Column(db.Boolean, default=False)
    pending_balance = db.Column(db.Float, default=0.0)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    vendor = db.relationship('Vendor', backref=db.backref('entries', lazy=True))

    # --- RESTORED FIELDS ---
    ship_from = db.Column(db.String(100), default="Mumbai")
    ship_to = db.Column(db.String(100), default="Udupi")
    rr_no = db.Column(db.String(50))

    parcels = db.Column(db.Integer, default=0)

    # --- SIMPLIFIED CHARGES ---
    handling_chg = db.Column(db.Float, default=0.0)
    railway_chg = db.Column(db.Float, default=0.0)
    transport_chg = db.Column(db.Float, default=0.0)

    grand_total = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(150))
    action = db.Column(db.String(50))
    details = db.Column(db.String(255))

    @staticmethod
    def log(user, action, details):
        try:
            new_log = AuditLog(username=user.username, action=action, details=details)
            db.session.add(new_log)
        except Exception:
            pass