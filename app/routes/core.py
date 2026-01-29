# app/routes/core.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime
from app.models import Entry, Vendor, AuditLog
from app.extensions import db
from sqlalchemy import func

core_bp = Blueprint('core', __name__)

def safe_float(v):
    try: return float(v) if v else 0.0
    except: return 0.0

def safe_int(v):
    try: return int(v) if v else 0
    except: return 0

@core_bp.route('/', methods=['GET', 'POST'])
@core_bp.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    today = date.today()

    if request.method == 'POST':
        try:
            vendor_id = request.form.get('vendor')
            if not vendor_id: raise ValueError("Vendor Required")

            # 1. Get Inputs
            parcels = safe_int(request.form.get('parcels'))
            railway = safe_float(request.form.get('railway'))

            # 2. Get Rates from Hidden/Form fields or DB (Here we trust the form's auto-calc)
            handling = safe_float(request.form.get('handling'))
            transport = safe_float(request.form.get('transport'))

            # 3. Calculate Total
            grand_total = handling + railway + transport

            new_entry = Entry(
                date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
                vendor_id=int(vendor_id),
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
            flash('Entry Added!')
            return redirect(url_for('core.home'))

        except Exception as e:
            flash(f'Error: {str(e)}')

    today_entries = Entry.query.filter_by(date=today).all()
    today_rev = sum(e.grand_total for e in today_entries)
    today_parcels = sum(e.parcels for e in today_entries)

    return render_template('home.html',
                           user=current_user, date=today,
                           vendors=Vendor.query.all(),
                           today_rev=today_rev, today_parcels=today_parcels,
                           entries=today_entries)

@core_bp.route('/view')
@login_required
def view_data():
    month = request.args.get('month', datetime.today().strftime('%Y-%m'))
    vendor_id = request.args.get('vendor')

    query = Entry.query.filter(func.strftime('%Y-%m', Entry.date) == month)
    if vendor_id and vendor_id != 'All':
        query = query.filter_by(vendor_id=int(vendor_id))

    entries = query.order_by(Entry.date.desc()).all()
    return render_template('view_data.html', entries=entries, month=month, vendor=vendor_id, vendors=Vendor.query.all())

@core_bp.route('/entry/delete/<int:id>')
@login_required
def delete_entry(id):
    entry = Entry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    flash('Deleted')
    if request.referrer and 'view' in request.referrer:
        return redirect(url_for('core.view_data'))
    return redirect(url_for('core.home'))