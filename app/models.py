from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# --- USER MODEL ---
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

# --- VENDOR MODEL ---
class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    # Rates
    rate_per_parcel = db.Column(db.Float, default=70.0)
    transport_rate = db.Column(db.Float, default=0.0)

    # Billing Info
    billing_name = db.Column(db.String(150))
    billing_address = db.Column(db.String(255))

    # Settings
    is_default = db.Column(db.Boolean, default=False)
    pending_balance = db.Column(db.Float, default=0.0)

    # PDF Column Toggles
    show_rr = db.Column(db.Boolean, default=True)
    show_handling = db.Column(db.Boolean, default=True)
    show_railway = db.Column(db.Boolean, default=True)
    show_transport = db.Column(db.Boolean, default=True)

# --- ENTRY MODEL (Restored Old Structure) ---
class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)

    # Relationship
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    vendor = db.relationship('Vendor', backref=db.backref('entries', lazy=True))

    # Route & Reference
    ship_from = db.Column(db.String(100), default="Mumbai")
    ship_to = db.Column(db.String(100), default="Udupi")
    rr_no = db.Column(db.String(50))

    # Data
    parcels = db.Column(db.Integer, default=0)

    # Charges
    handling_chg = db.Column(db.Float, default=0.0)
    railway_chg = db.Column(db.Float, default=0.0)
    transport_chg = db.Column(db.Float, default=0.0)

    grand_total = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- AUDIT LOG (Fixed to Auto-Commit) ---
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(150))
    action = db.Column(db.String(50))
    details = db.Column(db.String(255))

    @staticmethod
    def log(user, action, details):
        """
        Logs an action to the database.
        Includes a commit to ensure the log is saved immediately.
        """
        try:
            # Handle cases where user object might be complex or None
            if hasattr(user, 'username'):
                user_name = user.username
            else:
                user_name = "System"

            new_log = AuditLog(username=user_name, action=action, details=details)
            db.session.add(new_log)
            db.session.commit() #
        except Exception as e:
            # Print error to console but don't crash the app
            print(f"⚠️ Audit Log Failed: {e}")
            pass