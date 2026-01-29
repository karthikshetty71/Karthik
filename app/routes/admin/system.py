from flask import redirect, url_for, send_file, flash
from flask_login import login_required, current_user
from app.models import AuditLog
from app.extensions import db
from sqlalchemy import text
from . import admin_bp
import os
from datetime import datetime, timedelta

@admin_bp.route('/settings/optimize_db')
@login_required
def optimize_db():
    if not current_user.is_admin: return redirect(url_for('admin.settings'))
    try:
        db.session.execute(text("VACUUM"))
        db.session.commit()
        AuditLog.log(current_user, "SYSTEM", "Ran Database Optimization (VACUUM)")
        flash("Database optimized successfully!")
    except Exception as e:
        flash(f"Error optimizing: {e}")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/settings/clear_logs')
@login_required
def clear_logs():
    if not current_user.is_admin: return redirect(url_for('admin.settings'))
    try:
        cutoff_date = datetime.now() - timedelta(days=7)
        deleted_count = AuditLog.query.filter(AuditLog.timestamp < cutoff_date).delete()
        db.session.commit()
        AuditLog.log(current_user, "SYSTEM", f"Manually cleared {deleted_count} logs older than 7 days")
        flash(f"Success! Cleared {deleted_count} old log entries.")
    except Exception as e:
        flash(f"Error clearing logs: {e}")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/settings/backup')
@login_required
def backup():
    if not current_user.is_admin: return redirect(url_for('core.home'))
    AuditLog.log(current_user, "SYSTEM", "Downloaded Database Backup")
    db_filename = 'logistics.db'
    paths = [os.path.join(os.getcwd(), db_filename), os.path.join(os.getcwd(), 'instance', db_filename)]
    for path in paths:
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
    return "Database file not found", 404