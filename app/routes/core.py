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
            vendor_id = request.form.get('vendor')
            if not vendor_id: raise ValueError("Vendor is required")

            parcels = safe_int(request.form.get('parcels'))
            box_rate = safe_float(request.form.get('box_rate'))
            transport_rate = safe_float(request.form.get('transport_rate'))

            # Calculation
            total_freight = parcels * box_rate
            transport_charges = parcels * transport_rate

            hamali = safe_float(request.form.get('hamali'))
            stat_charges = safe_float(request.form.get('stat_charges'))
            cr_charges = safe_float(request.form.get('cr_charges'))
            railway_charges = safe_float(request.form.get('railway_charges'))
            demurrage = safe_float(request.form.get('demurrage'))

            grand_total = (total_freight + transport_charges + hamali +
                           stat_charges + cr_charges + railway_charges + demurrage)

            new_entry = Entry(
                date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
                vendor_id=int(vendor_id),
                invoice_number=request.form.get('invoice'),
                lr_number=request.form.get('lr'),
                part=request.form.get('part'),
                parcels=parcels, box_rate=box_rate, transport_rate=transport_rate,
                total_freight=total_freight, transport_charges=transport_charges,
                hamali=hamali, stat_charges=stat_charges, cr_charges=cr_charges,
                railway_charges=railway_charges, demurrage=demurrage,
                grand_total=grand_total,
                remarks=request.form.get('remarks')
            )

            db.session.add(new_entry)
            db.session.commit()

            vendor_name = Vendor.query.get(vendor_id).name
            AuditLog.log(current_user, "ADD ENTRY", f"Added {parcels} parcels for {vendor_name}")

            flash('Entry Added Successfully!')
            return redirect(url_for('core.home'))

        except Exception as e:
            flash(f'Error: {str(e)}')

    today_entries = Entry.query.filter_by(date=today).all()
    today_rev = sum(e.grand_total for e in today_entries)
    today_parcels = sum(e.parcels for e in today_entries)
    vendors = Vendor.query.all()
    default_vendor = Vendor.query.filter_by(is_default=True).first()

    return render_template('home.html', user=current_user, date=today, vendors=vendors,
                           default_vendor=default_vendor, today_rev=today_rev,
                           today_parcels=today_parcels, entries=today_entries)

# --- 2. VIEW DATA (RECORDS TAB) ---
@core_bp.route('/view', methods=['GET'])
@login_required
def view_data():
    month = request.args.get('month', datetime.today().strftime('%Y-%m'))
    vendor_id = request.args.get('vendor')

    query = Entry.query.filter(func.strftime('%Y-%m', Entry.date) == month)

    if vendor_id and vendor_id != 'All':
        query = query.filter_by(vendor_id=int(vendor_id))

    entries = query.order_by(Entry.date.desc()).all()
    vendors = Vendor.query.all()

    return render_template('view_data.html', entries=entries, month=month,
                           vendor=vendor_id, vendors=vendors)

# --- 3. EDIT ENTRY ---
@core_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    entry = Entry.query.get_or_404(id)
    vendors = Vendor.query.all()

    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            entry.vendor_id = int(request.form['vendor'])
            entry.invoice_number = request.form.get('invoice')
            entry.lr_number = request.form.get('lr')
            entry.part = request.form.get('part')

            entry.parcels = safe_int(request.form.get('parcels'))
            entry.box_rate = safe_float(request.form.get('box_rate'))
            entry.transport_rate = safe_float(request.form.get('transport_rate'))

            entry.total_freight = entry.parcels * entry.box_rate
            entry.transport_charges = entry.parcels * entry.transport_rate

            entry.hamali = safe_float(request.form.get('hamali'))
            entry.stat_charges = safe_float(request.form.get('stat_charges'))
            entry.cr_charges = safe_float(request.form.get('cr_charges'))
            entry.railway_charges = safe_float(request.form.get('railway_charges'))
            entry.demurrage = safe_float(request.form.get('demurrage'))

            entry.grand_total = (entry.total_freight + entry.transport_charges +
                                 entry.hamali + entry.stat_charges +
                                 entry.cr_charges + entry.railway_charges + entry.demurrage)

            entry.remarks = request.form.get('remarks')

            db.session.commit()
            AuditLog.log(current_user, "UPDATE ENTRY", f"Updated Entry #{entry.id}")
            flash('Entry Updated Successfully')
            return redirect(url_for('core.view_data'))
        except Exception as e:
            flash(f"Error: {e}")

    return render_template('edit.html', entry=entry, vendors=vendors)

# --- 4. DELETE ENTRY ---
@core_bp.route('/entry/delete/<int:id>')
@core_bp.route('/delete/<int:id>') # Alias for compatibility
@login_required
def delete_entry(id):
    entry = Entry.query.get_or_404(id)
    info = f"Deleted Entry #{entry.id}"
    db.session.delete(entry)
    db.session.commit()
    AuditLog.log(current_user, "DELETE ENTRY", info)
    flash('Entry Deleted')

    # Return to previous page
    if request.referrer and 'view' in request.referrer:
        return redirect(url_for('core.view_data'))
    return redirect(url_for('core.home'))

# --- 5. ADMIN VIEW (Redirects to View Data for now) ---
@core_bp.route('/admin_view')
@login_required
def admin_view():
    if not current_user.is_admin:
        flash("Admins only.")
        return redirect(url_for('core.home'))
    return redirect(url_for('core.view_data'))