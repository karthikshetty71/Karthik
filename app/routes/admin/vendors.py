from flask import request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Vendor, AuditLog
from app.extensions import db
from . import admin_bp

# --- ADD NEW VENDOR ---
@admin_bp.route('/settings/vendor/add', methods=['POST'])
@login_required
def add_vendor():
    if not current_user.is_admin:
        flash("Read Only Mode.")
        return redirect(url_for('admin.settings', tab='vendors'))

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

            AuditLog.log(current_user, "ADD VENDOR", f"Added new vendor: {name}")
            flash(f"Vendor '{name}' added.")

    return redirect(url_for('admin.settings', tab='vendors'))

# --- UPDATE VENDOR ---
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

            if old_rate != new_rate:
                AuditLog.log(current_user, "UPDATE RATE", f"{vendor.name}: Rate changed {old_rate} -> {new_rate}")
            else:
                AuditLog.log(current_user, "UPDATE VENDOR", f"Updated details for {vendor.name}")

        db.session.commit()
        flash(f"Updated {vendor.name}")

    except Exception as e:
        flash(f"Error: {str(e)}")

    return redirect(url_for('admin.settings', tab='vendors'))

# --- DELETE VENDOR ---
@admin_bp.route('/settings/vendor/delete/<int:id>')
@login_required
def delete_vendor(id):
    if not current_user.is_admin:
        return redirect(url_for('admin.settings', tab='vendors'))

    v = Vendor.query.get_or_404(id)
    name = v.name # Capture name before delete
    db.session.delete(v)
    db.session.commit()

    AuditLog.log(current_user, "DELETE VENDOR", f"Deleted vendor: {name}")
    flash(f"Deleted vendor: {name}")

    return redirect(url_for('admin.settings', tab='vendors'))

# --- SET DEFAULT VENDOR ---
@admin_bp.route('/settings/vendor/default/<int:id>')
@login_required
def set_default_vendor(id):
    if not current_user.is_admin:
        return redirect(url_for('admin.settings', tab='vendors'))

    Vendor.query.update({Vendor.is_default: False})
    v = Vendor.query.get_or_404(id)
    v.is_default = True
    db.session.commit()

    AuditLog.log(current_user, "UPDATE VENDOR", f"Set {v.name} as default")
    return redirect(url_for('admin.settings', tab='vendors'))