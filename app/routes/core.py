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

# --- HOME (DASHBOARD & ENTRY FORM) ---
@core_bp.route('/', methods=['GET', 'POST'])
@core_bp.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    today = date.today()

    if request.method == 'POST':
        try:
            # 1. Get Vendor ID
            vendor_id = request.form.get('vendor')
            if not vendor_id:
                raise ValueError("Vendor is required")

            # 2. Get Numeric Values
            parcels = safe_int(request.form.get('parcels'))
            box_rate = safe_float(request.form.get('box_rate'))
            transport_rate = safe_float(request.form.get('transport_rate'))

            # 3. Calculate Charges
            # Logic: Total Freight = Parcels * Box Rate
            total_freight = parcels * box_rate

            # Logic: Transport Charges = Parcels * Transport Rate
            transport_charges = parcels * transport_rate

            # Other optional charges
            hamali = safe_float(request.form.get('hamali'))
            stat_charges = safe_float(request.form.get('stat_charges'))
            cr_charges = safe_float(request.form.get('cr_charges'))
            railway_charges = safe_float(request.form.get('railway_charges'))
            demurrage = safe_float(request.form.get('demurrage'))

            # 4. Calculate Grand Total
            grand_total = (total_freight + transport_charges + hamali +
                           stat_charges + cr_charges + railway_charges + demurrage)

            # 5. Create Entry Object
            new_entry = Entry(
                date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
                vendor_id=int(vendor_id),
                invoice_number=request.form.get('invoice'),
                lr_number=request.form.get('lr'),
                part=request.form.get('part'),

                parcels=parcels,
                box_rate=box_rate,
                transport_rate=transport_rate,

                total_freight=total_freight,
                transport_charges=transport_charges,
                hamali=hamali,
                stat_charges=stat_charges,
                cr_charges=cr_charges,
                railway_charges=railway_charges,
                demurrage=demurrage,

                grand_total=grand_total,
                remarks=request.form.get('remarks')
            )

            db.session.add(new_entry)
            db.session.commit()

            # Log Action
            vendor_name = Vendor.query.get(vendor_id).name
            AuditLog.log(current_user, "ADD ENTRY", f"Added {parcels} parcels for {vendor_name}")

            flash('Entry Added Successfully!')
            return redirect(url_for('core.home'))

        except Exception as e:
            flash(f'Error: {str(e)}')

    # --- GET REQUEST (Load Dashboard) ---
    today_entries = Entry.query.filter_by(date=today).all()

    # Calculate Stats
    today_rev = sum(e.grand_total for e in today_entries)
    today_parcels = sum(e.parcels for e in today_entries)

    # Get Vendors for Dropdown
    vendors = Vendor.query.all()

    # Find Default Vendor (if exists)
    default_vendor = Vendor.query.filter_by(is_default=True).first()

    return render_template('home.html',
                           user=current_user,
                           date=today,
                           vendors=vendors,
                           default_vendor=default_vendor,
                           today_rev=today_rev,
                           today_parcels=today_parcels,
                           entries=today_entries)

# --- DELETE ENTRY ---
@core_bp.route('/entry/delete/<int:id>')
@login_required
def delete_entry(id):
    entry = Entry.query.get_or_404(id)

    # Capture info for log
    info = f"Deleted Entry #{entry.id} - {entry.invoice_number}"

    db.session.delete(entry)
    db.session.commit()

    AuditLog.log(current_user, "DELETE ENTRY", info)
    flash('Entry Deleted')

    return redirect(url_for('core.home'))