from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from flask_login import login_required, current_user
from app.models import Vendor, User, Entry, AuditLog
from app.extensions import db
import os

admin_bp = Blueprint('admin', __name__)

# --- MAIN SETTINGS PAGE (GET ONLY) ---
@admin_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    """
    Renders the main settings dashboard with Tabs.
    Gathers data for Vendors, Users, System Stats, and Audit Logs.
    """
    # 1. Fetch Vendor Data (Visible to all)
    vendors = Vendor.query.all()

    # 2. Admin-Only Data (Users, Stats, Logs)
    users = []
    audit_logs = []
    db_size = "Unknown"
    total_entries = 0

    if current_user.is_admin:
        # Fetch Users
        users = User.query.all()

        # Fetch Audit Logs (Last 50 events)
        audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()

        # System Stats
        total_entries = Entry.query.count()
        try:
            db_filename = 'logistics.db'
            paths = [
                os.path.join(os.getcwd(), db_filename),
                os.path.join(os.getcwd(), 'instance', db_filename)
            ]
            for path in paths:
                if os.path.exists(path):
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                    db_size = f"{size_mb:.2f} MB"
                    break
        except:
            pass

    return render_template('settings.html',
                           vendors=vendors,
                           users=users,
                           db_size=db_size,
                           total_entries=total_entries,
                           audit_logs=audit_logs)

# --- VENDOR ACTIONS ---

@admin_bp.route('/settings/vendor/add', methods=['POST'])
@login_required
def add_vendor():
    if not current_user.is_admin:
        flash("Read Only Mode.")
        return redirect(url_for('admin.settings'))

    name = request.form.get('vendor_name')
    if name:
        if Vendor.query.filter_by(name=name).first():
            flash(f"Vendor '{name}' already exists.")
        else:
            db.session.add(Vendor(
                name=name,
                rate_per_parcel=float(request.form.get('rate', 70.0)),
                transport_rate=float(request.form.get('transport', 0.0)),
                billing_name=request.form.get('billing_name'),
                billing_address=request.form.get('billing_address'),
                show_rr=True, show_handling=True, show_railway=True, show_transport=True
            ))
            db.session.commit()

            # LOGGING
            AuditLog.log(current_user, "ADD VENDOR", f"Added new vendor: {name}")
            flash(f"Vendor '{name}' added.")

    return redirect(url_for('admin.settings'))

@admin_bp.route('/settings/vendor/update/<int:id>', methods=['POST'])
@login_required
def update_vendor(id):
    vendor = Vendor.query.get_or_404(id)

    try:
        # 1. Allow ANY user to update Pending Balance
        new_pending = request.form.get('pending_balance')
        if new_pending is not None:
            old_balance = vendor.pending_balance
            vendor.pending_balance = float(new_pending)

            # Log specific balance change if that's the only thing happening (Standard User)
            if not current_user.is_admin and old_balance != vendor.pending_balance:
                AuditLog.log(current_user, "UPDATE BALANCE", f"Updated {vendor.name} balance to {vendor.pending_balance}")

        # 2. Only ADMINS can update critical fields
        if current_user.is_admin:
            vendor.rate_per_parcel = float(request.form.get('rate'))
            vendor.transport_rate = float(request.form.get('transport'))
            vendor.billing_name = request.form.get('billing_name')
            vendor.billing_address = request.form.get('billing_address')

            vendor.show_rr = bool(request.form.get('show_rr'))
            vendor.show_handling = bool(request.form.get('show_handling'))
            vendor.show_railway = bool(request.form.get('show_railway'))
            vendor.show_transport = bool(request.form.get('show_transport'))

            # Log full update
            AuditLog.log(current_user, "UPDATE VENDOR", f"Updated details for {vendor.name}")

        db.session.commit()
        flash(f"Updated {vendor.name}")

    except Exception as e:
        flash(f"Error: {str(e)}")

    return redirect(url_for('admin.settings'))

@admin_bp.route('/settings/vendor/delete/<int:id>', methods=['GET'])
@login_required
def delete_vendor(id):
    if not current_user.is_admin:
        flash("Access Denied.")
        return redirect(url_for('admin.settings'))

    v = Vendor.query.get_or_404(id)
    name = v.name # Capture name before delete
    db.session.delete(v)
    db.session.commit()

    # LOGGING
    AuditLog.log(current_user, "DELETE VENDOR", f"Deleted vendor: {name}")
    flash(f"Deleted vendor: {name}")

    return redirect(url_for('admin.settings'))

@admin_bp.route('/settings/vendor/default/<int:id>')
@login_required
def set_default_vendor(id):
    if not current_user.is_admin:
        return redirect(url_for('admin.settings'))

    Vendor.query.update({Vendor.is_default: False})
    v = Vendor.query.get_or_404(id)
    v.is_default = True
    db.session.commit()

    # LOGGING
    AuditLog.log(current_user, "UPDATE VENDOR", f"Set {v.name} as default vendor")

    return redirect(url_for('admin.settings'))

# --- USER ACTIONS (ADMIN ONLY) ---

@admin_bp.route('/settings/user/add', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        return redirect(url_for('admin.settings'))

    username = request.form.get('username')
    password = request.form.get('password')

    if username and password:
        if User.query.filter_by(username=username).first():
            flash('User already exists')
        else:
            new_user = User(username=username, is_admin=False)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            # LOGGING
            AuditLog.log(current_user, "ADD USER", f"Created user: {username}")
            flash(f'User {username} added')

    return redirect(url_for('admin.settings'))

@admin_bp.route('/settings/user/delete/<int:id>')
@login_required
def delete_user(id):
    if not current_user.is_admin:
        return redirect(url_for('admin.settings'))

    if current_user.id == id:
        flash("Cannot delete yourself!")
        return redirect(url_for('admin.settings'))

    user = User.query.get_or_404(id)
    username = user.username # Capture before delete
    db.session.delete(user)
    db.session.commit()

    # LOGGING
    AuditLog.log(current_user, "DELETE USER", f"Deleted user: {username}")
    flash(f'Deleted user {username}')

    return redirect(url_for('admin.settings'))

# --- SYSTEM ACTIONS (ADMIN ONLY) ---

@admin_bp.route('/settings/backup')
@login_required
def backup():
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

    # Optional: Log backup creation
    AuditLog.log(current_user, "SYSTEM", "Downloaded Database Backup")

    db_filename = 'logistics.db'
    paths = [
        os.path.join(os.getcwd(), db_filename),
        os.path.join(os.getcwd(), 'instance', db_filename)
    ]

    for path in paths:
        if os.path.exists(path):
            return send_file(path, as_attachment=True)

    return "Database file not found", 404