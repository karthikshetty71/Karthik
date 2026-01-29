from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    # New Field: Active Status
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

    # PDF Column Toggles
    show_rr = db.Column(db.Boolean, default=True)
    show_handling = db.Column(db.Boolean, default=True)
    show_railway = db.Column(db.Boolean, default=True)
    show_transport = db.Column(db.Boolean, default=True)

    # New: Default Vendor & Pending Balance
    is_default = db.Column(db.Boolean, default=False)
    pending_balance = db.Column(db.Float, default=0.0)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    vendor = db.relationship('Vendor', backref=db.backref('entries', lazy=True))

    invoice_number = db.Column(db.String(50))
    lr_number = db.Column(db.String(50))
    part = db.Column(db.String(10))  # A, B, C etc

    parcels = db.Column(db.Integer, default=0)
    box_rate = db.Column(db.Float, default=0.0)
    transport_rate = db.Column(db.Float, default=0.0)

    total_freight = db.Column(db.Float, default=0.0)
    hamali = db.Column(db.Float, default=0.0)
    stat_charges = db.Column(db.Float, default=0.0)
    cr_charges = db.Column(db.Float, default=0.0)
    railway_charges = db.Column(db.Float, default=0.0)
    transport_charges = db.Column(db.Float, default=0.0)
    demurrage = db.Column(db.Float, default=0.0)

    grand_total = db.Column(db.Float, default=0.0)
    remarks = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(150))
    action = db.Column(db.String(50))  # e.g., 'LOGIN', 'DELETE_ENTRY'
    details = db.Column(db.String(255))

    @staticmethod
    def log(user, action, details):
        try:
            new_log = AuditLog(username=user.username, action=action, details=details)
            db.session.add(new_log)
            # Note: We don't commit here to avoid interrupting the main transaction
            # The main route function will commit everything together.
            # If used outside a route, ensure db.session.commit() is called.
        except Exception:
            pass