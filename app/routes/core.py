from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime
from app.models import Entry, Vendor, AuditLog
from app.extensions import db
from sqlalchemy import func

core_bp = Blueprint('core', __name__)

# --- HELPER FUNCTIONS ---
def safe_float(value):
    try:
        if not value or str(value).strip() == '': return 0.0
        return float(value)
    except: return 0.0

def safe_int(value):
    try:
        if not value or str(value).strip() == '': return 0
        return int(value)
    except: return 0

# --- 1. HOME (DASHBOARD) ---
@core_bp.route('/', methods=['GET', 'POST'])
@core_bp.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    today = date.today()

    if request.method == 'POST':
        try:
            # 1. Get Vendor
            vendor_name = request.form.get('vendor')
            vendor_obj = Vendor.query.filter_by(name=vendor_name).first()
            if not vendor_obj:
                raise ValueError("Vendor not found")

            # 2. Get Inputs
            parcels = safe_int(request.form.get('parcels'))
            handling = safe_float(request.form.get('handling'))
            railway = safe_float(request.form.get('railway'))
            transport = safe_float(request.form.get('transport'))

            # 3. Calculate Total
            grand_total = handling + railway + transport

            # 4. Create Entry
            new_entry = Entry(
                date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
                vendor_id=vendor_obj.id,
                ship_from=request.form.get('from'),
                ship_to=request.form.get('to'),
                rr_no=request.form.get('rr_no'),
                parcels=parcels,
                handling_chg=handling,
                railway_chg=railway,
                transport_chg=transport,
                grand_total=grand_total
            )

            db.session.add(new_entry)
            db.session.commit()

            AuditLog.log(current_user, "ADD ENTRY", f"Added {parcels} parcels for {vendor_name}")
            flash('Entry Added Successfully!')
            return redirect(url_for('core.home'))

        except Exception as e:
            flash(f'Error: {str(e)}')

    # Stats
    today_entries = Entry.query.filter_by(date=today).all()
    today_rev = sum(e.grand_total for e in today_entries)
    today_parcels = sum(e.parcels for e in today_entries)
    vendors = Vendor.query.all()

    return render_template('home.html',
                           today=today,
                           vendors=vendors,
                           today_rev=today_rev,
                           today_parcels=today_parcels)

# --- 2. VIEW DATA (Modified for Modes) ---
@core_bp.route('/view', methods=['GET'])
@login_required
def view_data():
    month = request.args.get('month', datetime.today().strftime('%Y-%m'))
    vendor_id = request.args.get('vendor')
    mode = request.args.get('mode', 'normal') # Default to normal

    # Determine if Admin Mode is active
    admin_mode = (mode == 'admin' and current_user.is_admin)

    # --- DEFAULT SELECTION LOGIC ---
    if not vendor_id:
        if admin_mode:
            # In Admin Mode, default to 'All'
            vendor_id = 'All'
        else:
            # In Normal Mode, find the Default Vendor
            default_vendor = Vendor.query.filter_by(is_default=True).first()
            if default_vendor:
                vendor_id = str(default_vendor.id)
            else:
                vendor_id = 'All' # Fallback

    # Build Query
    query = Entry.query.filter(func.strftime('%Y-%m', Entry.date) == month)

    if vendor_id and vendor_id != 'All':
        query = query.filter_by(vendor_id=int(vendor_id))

    entries = query.order_by(Entry.date.desc()).all()
    vendors = Vendor.query.all()

    return render_template('view_data.html',
                           entries=entries,
                           month=month,
                           vendor=vendor_id,
                           vendors=vendors,
                           admin_mode=admin_mode)

# --- 3. DELETE ENTRY ---
@core_bp.route('/entry/delete/<int:id>')
@login_required
def delete_entry(id):
    entry = Entry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    flash('Entry Deleted')

    if request.referrer and 'view' in request.referrer:
        # Preserve the mode if possible, but simplest is to go back to view
        return redirect(request.referrer)
    return redirect(url_for('core.home'))

# --- 4. ADMIN VIEW REDIRECT ---
@core_bp.route('/admin_view')
@login_required
def admin_view():
    if not current_user.is_admin:
        flash("Admins only.")
        return redirect(url_for('core.home'))

    # Redirect to view with mode=admin
    today = datetime.today().strftime('%Y-%m')
    return redirect(url_for('core.view_data', month=today, mode='admin', vendor='All'))

# --- 5. EDIT ENTRY ROUTE (FIXED) ---
@core_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    entry = Entry.query.get_or_404(id)
    vendors = Vendor.query.all()

    if request.method == 'POST':
        try:
             # 1. Update Basic Info
             entry.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
             entry.vendor_id = int(request.form['vendor'])
             entry.rr_no = request.form.get('rr_no')
             entry.ship_from = request.form.get('from')
             entry.ship_to = request.form.get('to')

             # 2. Update Parcels
             entry.parcels = safe_int(request.form.get('parcels'))

             # 3. Update Charges (THIS WAS MISSING BEFORE)
             entry.handling_chg = safe_float(request.form.get('handling'))
             entry.railway_chg = safe_float(request.form.get('railway'))
             entry.transport_chg = safe_float(request.form.get('transport'))

             # 4. Recalculate Grand Total
             entry.grand_total = entry.handling_chg + entry.railway_chg + entry.transport_chg

             db.session.commit()
             AuditLog.log(current_user, "EDIT ENTRY", f"Updated Entry #{entry.id}")

             flash("Entry Updated Successfully")
             return redirect(url_for('core.view_data'))

        except Exception as e:
            flash(f"Error: {e}")

    return render_template('edit.html', entry=entry, vendors=vendors)