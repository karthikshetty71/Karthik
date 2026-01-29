from flask import request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import User, AuditLog
from app.extensions import db
from . import admin_bp

# --- ADD NEW USER ---
@admin_bp.route('/settings/user/add', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        return redirect(url_for('admin.settings'))

    username = request.form.get('username')
    password = request.form.get('password')
    # Checkbox returns 'on' if checked, None if not
    is_admin = True if request.form.get('is_admin') == 'on' else False

    if username and password:
        if User.query.filter_by(username=username).first():
            flash('User already exists')
        else:
            # New users are Active by default (is_active=True)
            new_user = User(username=username, is_admin=is_admin, is_active=True)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            role = "ADMIN" if is_admin else "STAFF"
            AuditLog.log(current_user, "ADD USER", f"Created user: {username} ({role})")
            flash(f'User {username} added as {role}')

    return redirect(url_for('admin.settings'))

# --- TOGGLE ADMIN ROLE ---
@admin_bp.route('/settings/user/toggle_admin/<int:id>')
@login_required
def toggle_admin(id):
    if not current_user.is_admin:
        return redirect(url_for('admin.settings'))

    if current_user.id == id:
        flash("You cannot demote yourself!")
        return redirect(url_for('admin.settings'))

    user = User.query.get_or_404(id)

    # Flip the status
    user.is_admin = not user.is_admin
    db.session.commit()

    new_role = "ADMIN" if user.is_admin else "STAFF"
    AuditLog.log(current_user, "UPDATE USER", f"Changed {user.username} role to {new_role}")
    flash(f"{user.username} is now {new_role}")

    return redirect(url_for('admin.settings'))

# --- TOGGLE ACTIVE STATUS (ENABLE/DISABLE) ---
@admin_bp.route('/settings/user/toggle_active/<int:id>')
@login_required
def toggle_active(id):
    if not current_user.is_admin:
        return redirect(url_for('admin.settings'))

    if current_user.id == id:
        flash("You cannot disable yourself!")
        return redirect(url_for('admin.settings'))

    user = User.query.get_or_404(id)

    # Flip the Active status
    user.is_active = not user.is_active
    db.session.commit()

    status = "ENABLED" if user.is_active else "DISABLED"

    # Log it
    AuditLog.log(current_user, "UPDATE USER", f"{status} user access for {user.username}")
    flash(f"User {user.username} is now {status}")

    return redirect(url_for('admin.settings'))

# --- DELETE USER ---
@admin_bp.route('/settings/user/delete/<int:id>')
@login_required
def delete_user(id):
    if not current_user.is_admin:
        return redirect(url_for('admin.settings'))

    if current_user.id == id:
        flash("Cannot delete yourself!")
        return redirect(url_for('admin.settings'))

    user = User.query.get_or_404(id)
    username = user.username
    db.session.delete(user)
    db.session.commit()

    AuditLog.log(current_user, "DELETE USER", f"Deleted user: {username}")
    flash(f'Deleted user {username}')

    return redirect(url_for('admin.settings'))