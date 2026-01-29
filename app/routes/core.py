from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime, date
from app.models import Entry, Vendor
from app.extensions import db
from sqlalchemy import or_

core_bp = Blueprint('core', __name__)

@core_bp.route('/', methods=['GET', 'POST'])
@login_required
def home():
    vendors = Vendor.query.all()
    today_entries = Entry.query.filter_by(date=date.today()).all()
    today_rev = sum(e.total for e in today_entries)
    today_parcels = sum(e.parcels for e in today_entries)
    
    if request.method == 'POST':
        try:
            date_obj = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            handling = float(request.form['handling'] or 0)
            railway = float(request.form['railway'] or 0)
            transport = float(request.form['transport'] or 0)
            
            # --- AUTO-GENERATE BILL NUMBER ---
            # Format: YYYYMM-001 (e.g., 202409-005)
            # 1. Find entries for this specific month
            month_str = date_obj.strftime('%Y-%m')
            existing_count = Entry.query.filter(db.cast(Entry.date, db.String).like(f'{month_str}%')).count()
            
            # 2. Generate next number
            next_num = existing_count + 1
            bill_number = f"{date_obj.strftime('%Y%m')}-{next_num:03d}"
            # ----------------------------------

            new_entry = Entry(
                date=date_obj,
                bill_no=bill_number, # SAVE GENERATED ID
                rr_no=request.form.get('rr_no', '-'),
                vendor=request.form['vendor'],
                ship_from=request.form['from'],
                ship_to=request.form['to'],
                parcels=int(request.form['parcels'] or 0),
                handling_chg=handling,
                railway_chg=railway,
                transport_chg=transport,
                total=handling + railway + transport
            )
            db.session.add(new_entry)
            db.session.commit()
            flash(f"Entry Added! Bill No: {bill_number}")
            return redirect(url_for('core.home'))
        except Exception as e:
            print(f"Error: {e}")

    return render_template('home.html', today=datetime.today().strftime('%Y-%m-%d'), 
                           vendors=vendors, today_rev=today_rev, today_parcels=today_parcels)

@core_bp.route('/view')
@login_required
def view_data():
    month = request.args.get('month', datetime.today().strftime('%Y-%m'))
    vendor = request.args.get('vendor', 'All')
    search_query = request.args.get('q', '')
    
    query = Entry.query
    if search_query:
        query = query.filter(or_(
            Entry.vendor.contains(search_query),
            Entry.rr_no.contains(search_query),
            Entry.bill_no.contains(search_query) # Allow searching by Bill No
        ))
    else:
        query = query.filter(db.cast(Entry.date, db.String).like(f'{month}%'))
    
    if vendor != 'All':
        query = query.filter_by(vendor=vendor)
    
    entries = query.order_by(Entry.date.desc()).all()
    grand_total = sum(e.total for e in entries)
    return render_template('view_data.html', entries=entries, month=month, vendor=vendor, 
                           grand_total=grand_total, search_query=search_query)

@core_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    entry = Entry.query.get_or_404(id)
    vendors = Vendor.query.all()
    if request.method == 'POST':
        entry.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        entry.rr_no = request.form.get('rr_no', '-')
        # Bill No is usually not editable to keep sequence integrity
        entry.vendor = request.form['vendor']
        entry.ship_from = request.form['from']
        entry.ship_to = request.form['to']
        entry.parcels = int(request.form['parcels'] or 0)
        entry.handling_chg = float(request.form['handling'] or 0)
        entry.railway_chg = float(request.form['railway'] or 0)
        entry.transport_chg = float(request.form['transport'] or 0)
        entry.total = entry.handling_chg + entry.railway_chg + entry.transport_chg
        db.session.commit()
        return redirect(url_for('core.view_data'))
    return render_template('edit.html', entry=entry, vendors=vendors)

@core_bp.route('/delete/<int:id>')
@login_required
def delete(id):
    entry = Entry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(request.referrer)