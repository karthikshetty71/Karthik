from app.extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    billing_name = db.Column(db.String(150))    # Name on PDF
    billing_address = db.Column(db.String(255)) # Address on PDF
    rate_per_parcel = db.Column(db.Float, default=70.0) # Handling Rate
    transport_rate = db.Column(db.Float, default=0.0)   # NEW: Transport Flat Rate
    is_default = db.Column(db.Boolean, default=False)
    show_rr = db.Column(db.Boolean, default=True)
    show_handling = db.Column(db.Boolean, default=True)
    show_railway = db.Column(db.Boolean, default=True)
    show_transport = db.Column(db.Boolean, default=True)

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