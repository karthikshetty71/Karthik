from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash, current_app
from flask_login import login_required, current_user
from app.models import Vendor
from app.extensions import db
import os

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Add New Vendor with Rate
        name = request.form.get('vendor_name')
        rate = float(request.form.get('rate', 70.0))
        
        if name:
            db.session.add(Vendor(name=name, rate_per_parcel=rate))
            db.session.commit()
        return redirect(url_for('admin.settings'))
        
    vendors = Vendor.query.all()
    return render_template('settings.html', vendors=vendors)

@admin_bp.route('/update_vendor_rate/<int:id>', methods=['POST'])
@login_required
def update_vendor_rate(id):
    vendor = Vendor.query.get_or_404(id)
    try:
        new_rate = float(request.form.get('rate'))
        vendor.rate_per_parcel = new_rate
        db.session.commit()
        flash(f"Updated rate for {vendor.name}")
    except:
        flash("Error updating rate")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/delete_vendor/<int:id>')
@login_required
def delete_vendor(id):
    v = Vendor.query.get_or_404(id)
    db.session.delete(v)
    db.session.commit()
    return redirect(url_for('admin.settings'))

@admin_bp.route('/backup')
@login_required
def backup():
    if not current_user.is_admin:
        return redirect(url_for('core.home'))
    
    # 1. Try finding in the current root folder
    db_path_root = os.path.join(os.getcwd(), 'logistics.db')
    
    # 2. Try finding in the 'instance' folder (Flask often puts it here)
    db_path_instance = os.path.join(os.getcwd(), 'instance', 'logistics.db')
    
    if os.path.exists(db_path_root):
        return send_file(db_path_root, as_attachment=True)
    
    elif os.path.exists(db_path_instance):
        return send_file(db_path_instance, as_attachment=True)
        
    else:
        # Debugging: Tell the user where we looked
        return f"Error: Database file not found.<br>Checked in:<br>1. {db_path_root}<br>2. {db_path_instance}", 404