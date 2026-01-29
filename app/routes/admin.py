from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from flask_login import login_required, current_user
from app.models import Vendor, User, Entry, AuditLog
from app.extensions import db
from sqlalchemy import text
import os
import psutil
import platform
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# --- HELPER: CALCULATE SYSTEM UPTIME ---
def get_uptime():
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        now = datetime.now()
        delta = now - boot_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m"
    except:
        return "Unknown"

# --- MAIN SETTINGS PAGE ---
@admin_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    """
    Renders the dashboard with System Metrics, Vendor Master, and Logs.
    """
    # 1. Vendor Data (Visible to All)
    vendors = Vendor.query.all()

    # 2. Admin Data Containers
    users = []
    audit_logs = []

    # 3. System Metrics Defaults
    system_stats = {
        'cpu_percent': 0,
        'cpu_cores': 0,
        'cpu_freq': "0 GHz",
        'ram_percent': 0,
        'ram_used': "0",
        'ram_total': "0",
        'disk_percent': 0,
        'disk_free': "0",
        'os_info': "Unknown",
        'uptime': "0m",
        'python_ver': platform.python_version(),
        'app_memory': "0 MB" # RAM used specifically by KPS App
    }

    db_size = "Unknown"
    total_entries = 0

    if current_user.is_admin:
        users = User.query.all()
        # Fetch last 100 logs
        audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
        total_entries = Entry.query.count()

        # --- FETCH REAL-TIME METRICS ---
        try:
            # CPU
            system_stats['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            system_stats['cpu_cores'] = psutil.cpu_count(logical=True)
            try:
                # Some environments (like AWS EC2 t2/t3) don't report frequency
                freq = psutil.cpu_freq()
                system_stats['cpu_freq'] = f"{freq.current / 1000:.1f} GHz" if freq else "N/A"
            except:
                system_stats['cpu_freq'] = "N/A"

            # RAM (System)
            ram = psutil.virtual_memory()
            system_stats['ram_percent'] = ram.percent
            system_stats['ram_used'] = f"{ram.used / (1024**3):.1f} GB"
            system_stats['ram_total'] = f"{ram.total / (1024**3):.1f} GB"

            # RAM (App Specific)
            process = psutil.Process(os.getpid())
            app_mem = process.memory_info().rss / (1024 * 1024) # Convert to MB
            system_stats['app_memory'] = f"{app_mem:.0f} MB"

            # DISK
            disk = psutil.disk_usage('/')
            system_stats['disk_percent'] = disk.percent
            system_stats['disk_free'] = f"{disk.free / (1024**3):.1f} GB"

            # OS & Uptime
            system_stats['os_info'] = f"{platform.system()} {platform.release()}"
            system_stats['uptime'] = get_uptime()

            # Database File Size
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
        except Exception as e:
            print(f"Metrics Error: {e}")

    return render_template('settings.html',
                           vendors=vendors,
                           users=users,
                           system_stats=system_stats,
                           db_size=db_size,
                           total_entries=total_entries,
                           audit_logs=audit_logs)

# --- NEW: OPTIMIZE DATABASE (VACUUM) ---
@admin_bp.route('/settings/optimize_db')
@login_required
def optimize_db():
    if not current_user.is_admin:
        return redirect(url_for('admin.settings'))

    try:
        # SQLite command to clean up unused space and defrag
        db.session.execute(text("VACUUM"))
        db.session.commit()

        AuditLog.log(current_user, "SYSTEM", "Ran Database Optimization (VACUUM)")
        flash("Database optimized successfully! (VACUUM completed)")
    except Exception as e:
        flash(f"Error optimizing: {e}")

    return redirect(url_for('admin.settings'))

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

            # Enhanced Log
            AuditLog.log(current_user, "ADD VENDOR", f"Added new vendor: {name}")
            flash(f"Vendor '{name}' added.")

    return redirect(url_for('admin.settings'))

@admin_bp.route('/settings/vendor/update/<int:id>', methods=['POST'])
@login_required
def update_vendor(id):
    vendor = Vendor.query.get_or_404(id)

    try:
        # 1. Update Pending Balance (Allowed for ANY user)
        new_pending = request.form.get('pending_balance')
        if new_pending is not None:
            old_balance = vendor.pending_balance
            vendor.pending_balance = float(new_pending)

            # Log significant balance changes
            if old_balance != vendor.pending_balance:
                AuditLog.log(current_user, "UPDATE BALANCE", f"{vendor.name}: {old_balance} -> {vendor.pending_balance}")

        # 2. Update Critical Info (Admin Only)
        if current_user.is_admin:
            # Capture old rate for comparison logging
            old_rate = vendor.rate_per_parcel
            new_rate = float(request.form.get('rate'))

            vendor.rate_per_parcel = new_rate
            vendor.transport_rate = float(request.form.get('transport'))
            vendor.billing_name = request.form.get('billing_name')
            vendor.billing_address = request.form.get('billing_address')
            vendor.show_rr = bool(request.form.get('show_rr'))
            vendor.show_handling = bool(request.form.get('show_handling'))
            vendor.show_railway = bool(request.form.get('show_railway'))
            vendor.show_transport = bool(request.form.get('show_transport'))

            # Smart Logging: Check if rate changed
            if old_rate != new_rate:
                AuditLog.log(current_user, "UPDATE RATE", f"{vendor.name}: Rate changed {old_rate} -> {new_rate}")
            else:
                AuditLog.log(current_user, "UPDATE VENDOR", f"Updated details for {vendor.name}")

        db.session.commit()
        flash(f"Updated {vendor.name}")

    except Exception as e:
        flash(f"Error: {str(e)}")

    return redirect(url_for('admin.settings'))

@admin_bp.route('/settings/vendor/delete/<int:id>')
@login_required
def delete_vendor(id):
    if not current_user.is_admin:
        return redirect(url_for('admin.settings'))

    v = Vendor.query.get_or_404(id)
    name = v.name # Capture name before delete
    db.session.delete(v)
    db.session.commit()

    # Log Deletion
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

    AuditLog.log(current_user, "UPDATE VENDOR", f"Set {v.name} as default")
    return redirect(url_for('admin.settings'))

# --- USER ACTIONS ---
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
    username = user.username
    db.session.delete(user)
    db.session.commit()

    AuditLog.log(current_user, "DELETE USER", f"Deleted user: {username}")
    flash(f'Deleted user {username}')

    return redirect(url_for('admin.settings'))

# --- BACKUP ---
@admin_bp.route('/settings/backup')
@login_required
def backup():
    if not current_user.is_admin:
        return redirect(url_for('core.home'))

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