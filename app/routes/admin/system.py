from flask import redirect, url_for, send_file, flash
from flask_login import login_required, current_user
from app.models import AuditLog
from app.extensions import db
from sqlalchemy import text
from . import admin_bp
import os
from datetime import datetime, timedelta

# --- OPTIMIZE DATABASE (VACUUM) ---
@admin_bp.route('/settings/optimize_db')
@login_required
def optimize_db():
    if not current_user.is_admin:
        return redirect(url_for('admin.settings', tab='system'))

    try:
        # VACUUM rebuilds the DB file, reclaiming free space
        db.session.execute(text("VACUUM"))
        db.session.commit()

        AuditLog.log(current_user, "SYSTEM", "Ran Database Optimization (VACUUM)")
        flash("Database optimized successfully!")
    except Exception as e:
        flash(f"Error optimizing: {e}")

    # Redirect back to the System tab
    return redirect(url_for('admin.settings', tab='system'))

# --- CLEAR OLD LOGS ---
@admin_bp.route('/settings/clear_logs')
@login_required
def clear_logs():
    if not current_user.is_admin:
        return redirect(url_for('admin.settings', tab='system'))

    try:
        # Delete logs older than 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        deleted_count = AuditLog.query.filter(AuditLog.timestamp < cutoff_date).delete()
        db.session.commit()

        AuditLog.log(current_user, "SYSTEM", f"Manually cleared {deleted_count} logs older than 7 days")
        flash(f"Success! Cleared {deleted_count} old log entries.")
    except Exception as e:
        flash(f"Error clearing logs: {e}")

    # Redirect back to the System tab (where the button is)
    return redirect(url_for('admin.settings', tab='system'))

# --- DOWNLOAD BACKUP ---
@admin_bp.route('/settings/backup')
@login_required
def backup():
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

    AuditLog.log(current_user, "SYSTEM", "Downloaded Database Backup")

    # Point explicitly to the 'instance' folder
    db_path = os.path.join(os.getcwd(), 'instance', 'logistics.db')

    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True)

    return "Database file not found in instance folder.", 404