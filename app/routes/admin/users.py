from flask import request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import User, AuditLog
from app.extensions import db
from . import admin_bp

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
            new_user = User(username=username, is_admin=is_admin)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            role = "ADMIN" if is_admin else "STAFF"
            AuditLog.log(current_user, "ADD USER", f"Created user: {username} ({role})")
            flash(f'User {username} added as {role}')

    return redirect(url_for('admin.settings'))

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