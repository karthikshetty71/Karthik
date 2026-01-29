from flask import render_template
from flask_login import login_required, current_user
from app.models import Vendor, User, Entry, AuditLog
from . import admin_bp
import psutil
import platform
import os
from datetime import datetime

# --- HELPER ---
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

# --- ROUTE ---
@admin_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    # 1. Vendor Data
    vendors = Vendor.query.all()

    # 2. Defaults
    users = []
    audit_logs = []
    system_stats = {
        'cpu_percent': 0, 'cpu_cores': 0, 'cpu_freq': "N/A",
        'ram_percent': 0, 'ram_used': "0", 'ram_total': "0",
        'disk_percent': 0, 'disk_free': "0",
        'os_info': "Unknown", 'uptime': "0m",
        'python_ver': platform.python_version(), 'app_memory': "0 MB"
    }
    db_size = "Unknown"
    total_entries = 0

    if current_user.is_admin:
        users = User.query.all()
        audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
        total_entries = Entry.query.count()

        try:
            # CPU & RAM
            system_stats['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            system_stats['cpu_cores'] = psutil.cpu_count(logical=True)
            ram = psutil.virtual_memory()
            system_stats['ram_percent'] = ram.percent
            system_stats['ram_used'] = f"{ram.used / (1024**3):.1f} GB"
            system_stats['ram_total'] = f"{ram.total / (1024**3):.1f} GB"

            # App Memory
            process = psutil.Process(os.getpid())
            app_mem = process.memory_info().rss / (1024 * 1024)
            system_stats['app_memory'] = f"{app_mem:.0f} MB"

            # Disk & OS
            disk = psutil.disk_usage('/')
            system_stats['disk_percent'] = disk.percent
            system_stats['disk_free'] = f"{disk.free / (1024**3):.1f} GB"
            system_stats['os_info'] = f"{platform.system()} {platform.release()}"
            system_stats['uptime'] = get_uptime()

            # DB Size
            db_filename = 'logistics.db'
            paths = [os.path.join(os.getcwd(), db_filename), os.path.join(os.getcwd(), 'instance', db_filename)]
            for path in paths:
                if os.path.exists(path):
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                    db_size = f"{size_mb:.2f} MB"
                    break
        except Exception as e:
            print(f"Metrics Error: {e}")

    return render_template('settings.html',
                           vendors=vendors, users=users,
                           system_stats=system_stats, db_size=db_size,
                           total_entries=total_entries, audit_logs=audit_logs)