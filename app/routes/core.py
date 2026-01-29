from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import date, datetime
from app.models import Entry, Vendor
from app.extensions import db
from sqlalchemy import func

core_bp = Blueprint('core', __name__)

# --- HELPER FUNCTIONS ---
# These prevent the "could not convert string to float" error
def safe_float(value):
    try:
        if not value or value.strip() == '': return 0.0
        return float(value)
    except: return 0.0

def safe_int(value):
    try:
        if not value or value.strip() == '': return 0
        return int(value)
    except: return 0

# --- HOME (QUICK ENTRY) ---
@core_bp.route('/', methods=['GET', 'POST'])
@login_required
def home():
    today = date.today()

    if request.method == 'POST':
        try:
            # 1. Get numeric values safely
            handling = safe_float(request.form.get('handling'))
            railway = safe_float(request.form.get('railway'))
            transport = safe_float(request.form.get('transport'))
            parcels = safe_int(request.form.get('parcels'))

            # 2. Create the entry
            new_entry = Entry(
                date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
                bill_no=f"B-{datetime.now().strftime('%d%H%M')}",
                rr_no=request.form['rr_no'],
                vendor=request.form['vendor'],
                ship_from=request.form['from'],
                ship_to=request.form['to'],
                parcels=parcels,
                handling_chg=handling,
                railway_chg=railway,
                transport_chg=transport,
                total=handling + railway + transport
            )
            db.session.add(new_entry)
            db.session.commit()
            flash('Entry Added Successfully')
            return redirect(url_for('core.home'))
        except Exception as e:
            flash(f'Error: {str(e)}')

    # Stats for the top cards
    today_entries = Entry.query.filter_by(date=today).all()
    today_rev = sum(e.total for e in today_entries)
    today_parcels = sum(e.parcels for e in today_entries)

    return render_template('home.html',
                           today=today,
                           vendors=Vendor.query.all(),
                           today_rev=today_rev,
                           today_parcels=today_parcels)

# --- VIEW DATA (RECORDS) ---
@core_bp.route('/view', methods=['GET'])
@login_required
def view_data():
    month = request.args.get('month', datetime.today().strftime('%Y-%m'))

    # --- LOGIC: Find the Default Vendor ---
    # 1. Check if user selected one in the filter
    vendor_filter = request.args.get('vendor')

    # 2. If not, look up the "Starred" vendor in database
    if not vendor_filter:
        default_vendor = Vendor.query.filter_by(is_default=True).first()
        if default_vendor:
            vendor_filter = default_vendor.name
        else:
            vendor_filter = 'All' # Fallback if no default set

    search_q = request.args.get('q')

    # Build Query
    query = Entry.query.filter(func.strftime('%Y-%m', Entry.date) == month)

    # Apply Filter (unless "All")
    if vendor_filter and vendor_filter != 'All':
        query = query.filter_by(vendor=vendor_filter)

    # Apply Search
    if search_q:
        query = query.filter(
            (Entry.bill_no.contains(search_q)) |
            (Entry.rr_no.contains(search_q)) |
            (Entry.ship_to.contains(search_q))
        )

    entries = query.order_by(Entry.date.desc()).all()

    return render_template('view_data.html',
                           entries=entries,
                           month=month,
                           vendor=vendor_filter,
                           search_query=search_q,
                           vendors=Vendor.query.all())

# --- ADMIN MASTER VIEW ---
@core_bp.route('/admin_view', methods=['GET'])
@login_required
def admin_view():
    if not current_user.is_admin:
        flash("Admins only.")
        return redirect(url_for('core.view_data'))

    month = request.args.get('month', datetime.today().strftime('%Y-%m'))
    vendor_filter = request.args.get('vendor', 'All') # Default to All for Admin View

    query = Entry.query.filter(func.strftime('%Y-%m', Entry.date) == month)

    if vendor_filter and vendor_filter != 'All':
        query = query.filter_by(vendor=vendor_filter)

    entries = query.order_by(Entry.date.desc()).all()

    return render_template('admin_view.html',
                           entries=entries,
                           month=month,
                           selected_vendor=vendor_filter,
                           vendors=Vendor.query.all())

# --- DELETE ENTRY ---
@core_bp.route('/delete/<int:id>')
@login_required
def delete_entry(id):
    entry = Entry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    flash('Entry Deleted')

    # Redirect back to whichever page you came from
    if request.referrer and 'admin_view' in request.referrer:
        return redirect(url_for('core.admin_view'))
    return redirect(url_for('core.view_data'))

# --- EDIT ENTRY ---
@core_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    entry = Entry.query.get_or_404(id)
    if request.method == 'POST':
        try:
            entry.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            entry.vendor = request.form['vendor']
            entry.rr_no = request.form['rr_no']
            entry.ship_from = request.form['from']
            entry.ship_to = request.form['to']

            # Use safe converters
            entry.parcels = safe_int(request.form.get('parcels'))
            entry.handling_chg = safe_float(request.form.get('handling'))
            entry.railway_chg = safe_float(request.form.get('railway'))
            entry.transport_chg = safe_float(request.form.get('transport'))

            # Recalculate Total
            entry.total = entry.handling_chg + entry.railway_chg + entry.transport_chg

            db.session.commit()
            flash('Entry Updated')

            if request.referrer and 'admin_view' in request.referrer:
                return redirect(url_for('core.admin_view'))
            return redirect(url_for('core.view_data'))

        except Exception as e:
            flash(f"Error: {str(e)}")

    return render_template('edit.html', entry=entry, vendors=Vendor.query.all())