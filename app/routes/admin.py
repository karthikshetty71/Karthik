from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from flask_login import login_required, current_user
from app.models import Vendor, User
from app.extensions import db
import os

# --- THIS LINE WAS MISSING OR BROKEN ---
admin_bp = Blueprint('admin', __name__)
# ---------------------------------------

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    # Allow non-admins to VIEW, but not POST
    if request.method == 'POST' and not current_user.is_admin:
        flash("Access Denied: Admins only.")
        return redirect(url_for('admin.settings'))

    if request.method == 'POST':
        # Add New Vendor Logic
        name = request.form.get('vendor_name')
        rate = float(request.form.get('rate', 70.0))
        transport = float(request.form.get('transport', 0.0))

        # New Fields
        bill_name = request.form.get('billing_name')
        bill_addr = request.form.get('billing_address')

        if name:
            if Vendor.query.filter_by(name=name).first():
                flash(f"Vendor '{name}' already exists.")
            else:
                db.session.add(Vendor(
                    name=name,
                    rate_per_parcel=rate,
                    transport_rate=transport,
                    billing_name=bill_name,     # Save
                    billing_address=bill_addr   # Save
                ))
                db.session.commit()
                flash(f"Vendor '{name}' added successfully.")
        return redirect(url_for('admin.settings'))

    vendors = Vendor.query.all()
    return render_template('settings.html', vendors=vendors)

@admin_bp.route('/update_vendor_rate/<int:id>', methods=['POST'])
@login_required
def update_vendor_rate(id):
    if not current_user.is_admin:
        flash("Admins only.")
        return redirect(url_for('admin.settings'))

    vendor = Vendor.query.get_or_404(id)
    try:
        vendor.rate_per_parcel = float(request.form.get('rate'))
        vendor.transport_rate = float(request.form.get('transport'))

        # Update Billing Details
        vendor.billing_name = request.form.get('billing_name')
        vendor.billing_address = request.form.get('billing_address')

        db.session.commit()
        flash(f"Updated details for {vendor.name}")
    except:
        flash("Error updating. Please check inputs.")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/set_default_vendor/<int:id>')
@login_required
def set_default_vendor(id):
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

    # 1. Reset all vendors to False
    Vendor.query.update({Vendor.is_default: False})

    # 2. Set selected vendor to True
    vendor = Vendor.query.get_or_404(id)
    vendor.is_default = True

    db.session.commit()
    flash(f"Default vendor set to: {vendor.name}")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/delete_vendor/<int:id>')
@login_required
def delete_vendor(id):
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

    v = Vendor.query.get_or_404(id)
    db.session.delete(v)
    db.session.commit()
    flash(f"Deleted vendor: {v.name}")
    return redirect(url_for('admin.settings'))

# --- USER MANAGEMENT ---
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
                new_user = User(username=username, is_admin=False) # Default to non-admin
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash(f'User {username} added successfully')
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

# --- BACKUP ---
@admin_bp.route('/backup')
@login_required
def backup():
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

    db_filename = 'logistics.db'
    db_path_root = os.path.join(os.getcwd(), db_filename)
    db_path_instance = os.path.join(os.getcwd(), 'instance', db_filename)

    if os.path.exists(db_path_root):
        return send_file(db_path_root, as_attachment=True)
    elif os.path.exists(db_path_instance):
        return send_file(db_path_instance, as_attachment=True)
    else:
        return "Database file not found", 404