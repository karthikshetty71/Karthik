from flask import Flask
from app.extensions import db, login_manager
from app.models import User, Vendor

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'kps-secret-key-9988'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///logistics.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints (Routes)
    from app.routes.auth import auth_bp
    from app.routes.core import core_bp
    from app.routes.admin import admin_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)

    # Initialize DB Content
    with app.app_context():
        db.create_all()
        # Create Default Admin
        if not User.query.first():
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(" System: Default Admin Created (admin/admin123)")
        
        # Create Default Vendors
        if not Vendor.query.first():
            db.session.add(Vendor(name="M/S Best Sellers"))
            db.session.add(Vendor(name="M/S Shiva Express"))
            db.session.add(Vendor(name="Manipal Technologies"))
            db.session.commit()

    from flask_login import user_logged_in, user_logged_out
        from app.models import AuditLog

        @user_logged_in.connect_via(app)
        def log_login(sender, user, **extra):
            AuditLog.log(user, "LOGIN", "User logged in successfully")

        @user_logged_out.connect_via(app)
        def log_logout(sender, user, **extra):
            AuditLog.log(user, "LOGOUT", "User logged out")

    return app