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

            # 3. Get Raw Charges
            raw_handling = safe_float(request.form.get('handling'))
            raw_railway = safe_float(request.form.get('railway'))
            raw_transport = safe_float(request.form.get('transport'))

            # 4. ENFORCE VENDOR SETTINGS (If column disabled -> Charge is 0)
            handling = raw_handling if vendor_obj.show_handling else 0.0
            railway = raw_railway if vendor_obj.show_railway else 0.0
            transport = raw_transport if vendor_obj.show_transport else 0.0

            # 5. Calculate Total
            grand_total = handling + railway + transport

            # 6. Create Entry
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

# --- 2. VIEW DATA ---
@core_bp.route('/view', methods=['GET'])
@login_required
def view_data():
    month = request.args.get('month', datetime.today().strftime('%Y-%m'))
    vendor_id = request.args.get('vendor')
    mode = request.args.get('mode', 'normal')

    admin_mode = (mode == 'admin' and current_user.is_admin)

    if not vendor_id:
        if admin_mode:
            vendor_id = 'All'
        else:
            default_vendor = Vendor.query.filter_by(is_default=True).first()
            vendor_id = str(default_vendor.id) if default_vendor else 'All'

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
        return redirect(request.referrer)
    return redirect(url_for('core.home'))

# --- 4. ADMIN VIEW REDIRECT ---
@core_bp.route('/admin_view')
@login_required
def admin_view():
    if not current_user.is_admin:
        return redirect(url_for('core.home'))
    today = datetime.today().strftime('%Y-%m')
    return redirect(url_for('core.view_data', month=today, mode='admin', vendor='All'))

# --- 5. EDIT ENTRY (Enforce Logic Here Too) ---
@core_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    entry = Entry.query.get_or_404(id)
    vendors = Vendor.query.all()

    if request.method == 'POST':
        try:
             # Get Vendor Object to check flags
             v_id = int(request.form['vendor'])
             vendor_obj = Vendor.query.get(v_id)

             entry.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
             entry.vendor_id = v_id
             entry.rr_no = request.form.get('rr_no')
             entry.ship_from = request.form.get('from')
             entry.ship_to = request.form.get('to')
             entry.parcels = safe_int(request.form.get('parcels'))

             # --- ENFORCE FLAGS ---
             raw_handling = safe_float(request.form.get('handling'))
             raw_railway = safe_float(request.form.get('railway'))
             raw_transport = safe_float(request.form.get('transport'))

             entry.handling_chg = raw_handling if vendor_obj.show_handling else 0.0
             entry.railway_chg = raw_railway if vendor_obj.show_railway else 0.0
             entry.transport_chg = raw_transport if vendor_obj.show_transport else 0.0

             # Recalculate Total
             entry.grand_total = entry.handling_chg + entry.railway_chg + entry.transport_chg

             db.session.commit()
             AuditLog.log(current_user, "EDIT ENTRY", f"Updated Entry #{entry.id}")

             flash("Entry Updated Successfully")
             return redirect(url_for('core.view_data'))

        except Exception as e:
            flash(f"Error: {e}")

    return render_template('edit.html', entry=entry, vendors=vendors)