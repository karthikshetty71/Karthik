from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from flask_login import login_required, current_user
from app.models import Vendor, User
from app.extensions import db
import os

admin_bp = Blueprint('admin', __name__)

# --- SETTINGS & VENDOR MANAGEMENT ---
@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    # Security Check
    if not current_user.is_admin:
        flash("Access Denied: Admin only.")
        return redirect(url_for('core.home'))

    if request.method == 'POST':
        # Add New Vendor
        name = request.form.get('vendor_name')
        rate = float(request.form.get('rate', 70.0))       # Default Handling Rate
        transport = float(request.form.get('transport', 0.0)) # Default Transport Rate

        if name:
            # Check if exists first
            existing = Vendor.query.filter_by(name=name).first()
            if existing:
                flash(f"Vendor '{name}' already exists.")
            else:
                # Add with both rates
                db.session.add(Vendor(name=name, rate_per_parcel=rate, transport_rate=transport))
                db.session.commit()
                flash(f"Vendor '{name}' added successfully.")
        return redirect(url_for('admin.settings'))

    vendors = Vendor.query.all()
    return render_template('settings.html', vendors=vendors)

@admin_bp.route('/update_vendor_rate/<int:id>', methods=['POST'])
@login_required
def update_vendor_rate(id):
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

    vendor = Vendor.query.get_or_404(id)
    try:
        # Update both rates from the table inputs
        vendor.rate_per_parcel = float(request.form.get('rate'))
        vendor.transport_rate = float(request.form.get('transport'))
        db.session.commit()
        flash(f"Updated rates for {vendor.name}")
    except:
        flash("Error updating rates. Please enter valid numbers.")
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

# --- DATABASE BACKUP ---
@admin_bp.route('/backup')
@login_required
def backup():
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

    # Robust path finding to download the DB file
    db_filename = 'logistics.db'

    # 1. Try Root Folder
    db_path_root = os.path.join(os.getcwd(), db_filename)

    # 2. Try Instance Folder (Standard Flask location)
    db_path_instance = os.path.join(os.getcwd(), 'instance', db_filename)

    # 3. Try relative (Fallback)
    db_path_relative = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance', db_filename)

    if os.path.exists(db_path_root):
        return send_file(db_path_root, as_attachment=True)
    elif os.path.exists(db_path_instance):
        return send_file(db_path_instance, as_attachment=True)
    elif os.path.exists(db_path_relative):
         return send_file(db_path_relative, as_attachment=True)
    else:
        return f"Error: Database not found.<br>Checked:<br>{db_path_root}<br>{db_path_instance}", 404