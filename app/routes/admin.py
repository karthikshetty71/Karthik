from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from flask_login import login_required, current_user
from app.models import Vendor, User
from app.extensions import db
import os

admin_bp = Blueprint('admin', __name__)

# --- SETTINGS (Viewable by All, Editable by Admin) ---
@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    # 1. SECURITY: Block non-admins from saving data (POST)
    # They can still view the page (GET)
    if request.method == 'POST' and not current_user.is_admin:
        flash("Read Only Mode: You cannot edit vendor details.")
        return redirect(url_for('admin.settings'))

    if request.method == 'POST':
        # Add New Vendor Logic
        name = request.form.get('vendor_name')

        if name:
            if Vendor.query.filter_by(name=name).first():
                flash(f"Vendor '{name}' already exists.")
            else:
                # Create Vendor with all fields
                # Default visibility is set to True for new vendors
                db.session.add(Vendor(
                    name=name,
                    rate_per_parcel=float(request.form.get('rate', 70.0)),
                    transport_rate=float(request.form.get('transport', 0.0)),
                    billing_name=request.form.get('billing_name'),
                    billing_address=request.form.get('billing_address'),
                    show_rr=True,
                    show_handling=True,
                    show_railway=True,
                    show_transport=True
                ))
                db.session.commit()
                flash(f"Vendor '{name}' added successfully.")
        return redirect(url_for('admin.settings'))

    vendors = Vendor.query.all()
    return render_template('settings.html', vendors=vendors)

@admin_bp.route('/update_vendor_rate/<int:id>', methods=['POST'])
@login_required
def update_vendor_rate(id):
    # Strict Admin Check
    if not current_user.is_admin:
        flash("Access Denied.")
        return redirect(url_for('admin.settings'))

    vendor = Vendor.query.get_or_404(id)
    try:
        # Standard Fields
        vendor.rate_per_parcel = float(request.form.get('rate'))
        vendor.transport_rate = float(request.form.get('transport'))
        vendor.billing_name = request.form.get('billing_name')
        vendor.billing_address = request.form.get('billing_address')

        # Checkbox Logic:
        # HTML checkboxes send 'on' if checked, and nothing (None) if unchecked.
        vendor.show_rr = True if request.form.get('show_rr') else False
        vendor.show_handling = True if request.form.get('show_handling') else False
        vendor.show_railway = True if request.form.get('show_railway') else False
        vendor.show_transport = True if request.form.get('show_transport') else False

        db.session.commit()
        flash(f"Updated details for {vendor.name}")
    except Exception as e:
        flash(f"Error updating: {str(e)}")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/set_default_vendor/<int:id>')
@login_required
def set_default_vendor(id):
    # Strict Admin Check
    if not current_user.is_admin:
        flash("Access Denied.")
        return redirect(url_for('admin.settings'))

    # 1. Reset all to False
    Vendor.query.update({Vendor.is_default: False})

    # 2. Set new default
    vendor = Vendor.query.get_or_404(id)
    vendor.is_default = True

    db.session.commit()
    flash(f"Default vendor set to: {vendor.name}")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/delete_vendor/<int:id>')
@login_required
def delete_vendor(id):
    # Strict Admin Check
    if not current_user.is_admin:
        flash("Access Denied.")
        return redirect(url_for('admin.settings'))

    v = Vendor.query.get_or_404(id)
    db.session.delete(v)
    db.session.commit()
    flash(f"Deleted vendor: {v.name}")
    return redirect(url_for('admin.settings'))

# --- USER MANAGEMENT (ADMINS ONLY) ---
@admin_bp.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    if not current_user.is_admin:
        flash("Access Denied")
        return redirect(url_for('core.home'))

    if request.method == 'POST':
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
                flash(f'User {username} added')
        return redirect(url_for('admin.users'))

    users = User.query.all()
    return render_template('users.html', users=users)

@admin_bp.route('/delete_user/<int:id>')
@login_required
def delete_user(id):
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

    if current_user.id == id:
        flash("Cannot delete yourself!")
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} deleted')
    return redirect(url_for('admin.users'))

# --- BACKUP (ADMINS ONLY) ---
@admin_bp.route('/backup')
@login_required
def backup():
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

    db_filename = 'logistics.db'

    # Try multiple locations to find the DB
    paths = [
        os.path.join(os.getcwd(), db_filename),
        os.path.join(os.getcwd(), 'instance', db_filename)
    ]

    for path in paths:
        if os.path.exists(path):
            return send_file(path, as_attachment=True)

    return "Database file not found", 404