from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask import request

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    # Active Status (Default is True/Active)
        is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    billing_name = db.Column(db.String(150))
    billing_address = db.Column(db.String(255))

    rate_per_parcel = db.Column(db.Float, default=70.0)
    transport_rate = db.Column(db.Float, default=0.0)
    is_default = db.Column(db.Boolean, default=False)

    # PDF Settings (Column Visibility)
    show_rr = db.Column(db.Boolean, default=True)
    show_handling = db.Column(db.Boolean, default=True)
    show_railway = db.Column(db.Boolean, default=True)
    show_transport = db.Column(db.Boolean, default=True)

    # Financials
    pending_balance = db.Column(db.Float, default=0.0)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    bill_no = db.Column(db.String(50))
    rr_no = db.Column(db.String(50))
    vendor = db.Column(db.String(100))
    ship_from = db.Column(db.String(100))
    ship_to = db.Column(db.String(100))
    parcels = db.Column(db.Integer)
    handling_chg = db.Column(db.Float)
    railway_chg = db.Column(db.Float)
    transport_chg = db.Column(db.Float)
    total = db.Column(db.Float)

class AuditLog(db.Model):
    """
    Tracks critical system actions for security and accountability.
    Includes auto-cleanup to prevent database bloat.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    username = db.Column(db.String(100)) # Store string in case User is deleted
    action = db.Column(db.String(50))    # e.g., "DELETE", "UPDATE", "LOGIN"
    details = db.Column(db.String(255))  # e.g., "Deleted Entry #505"
    ip_address = db.Column(db.String(50))

    @staticmethod
    def log(user, action, details):
        """
        Creates a log entry and automatically cleans logs older than 180 days.
        """
        try:
            # 1. AUTO-CLEANUP: Delete logs older than 180 days to save space
            cutoff_date = datetime.now() - timedelta(days=180)
            AuditLog.query.filter(AuditLog.timestamp < cutoff_date).delete()

            # 2. CREATE NEW LOG
            # Handle IP address (safe for local or proxy)
            ip = request.remote_addr if request else 'Unknown'

            # Handle Username (safe if user is None or not authenticated)
            user_name = "System/Guest"
            if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
                user_name = user.username

            new_log = AuditLog(
                username=user_name,
                action=action,
                details=details,
                ip_address=ip
            )
            db.session.add(new_log)
            db.session.commit()
        except Exception as e:
            # Fail silently so the main application flow doesn't crash if logging fails
            print(f"Audit Log Error: {e}")