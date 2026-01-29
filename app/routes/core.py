from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import date, datetime
from app.models import Entry, Vendor
from app.extensions import db
from sqlalchemy import func

core_bp = Blueprint('core', __name__)

@core_bp.route('/', methods=['GET', 'POST'])
@login_required
def home():
    today = date.today()

    if request.method == 'POST':
        try:
            new_entry = Entry(
                date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
                bill_no=f"B-{datetime.now().strftime('%d%H%M')}", # Simple Auto-Bill No
                rr_no=request.form['rr_no'],
                vendor=request.form['vendor'],
                ship_from=request.form['from'],
                ship_to=request.form['to'],
                parcels=int(request.form['parcels']),
                handling_chg=float(request.form['handling']),
                railway_chg=float(request.form['railway']),
                transport_chg=float(request.form['transport']),
                total=float(request.form['handling']) + float(request.form['railway']) + float(request.form['transport'])
            )
            db.session.add(new_entry)
            db.session.commit()
            flash('Entry Added Successfully')
            return redirect(url_for('core.home'))
        except Exception as e:
            flash(f'Error: {str(e)}')

    # Stats for today
    today_entries = Entry.query.filter_by(date=today).all()
    today_rev = sum(e.total for e in today_entries)
    today_parcels = sum(e.parcels for e in today_entries)

    return render_template('home.html',
                           today=today,
                           vendors=Vendor.query.all(), # Sends vendors to dropdown
                           today_rev=today_rev,
                           today_parcels=today_parcels)

@core_bp.route('/view', methods=['GET'])
@login_required
def view_data():
    month = request.args.get('month', datetime.today().strftime('%Y-%m'))
    vendor_filter = request.args.get('vendor') # Removed 'All' default here
    search_q = request.args.get('q')

    query = Entry.query.filter(func.strftime('%Y-%m', Entry.date) == month)

    # Logic: If user selects a vendor, filter by it.
    # If they don't (first load), we might want to show EVERYTHING or just the first vendor.
    # Since you removed "All", usually we just filter if a specific one is picked.
    if vendor_filter and vendor_filter != 'All':
        query = query.filter_by(vendor=vendor_filter)

    if search_q:
        query = query.filter(
            (Entry.bill_no.contains(search_q)) |
            (Entry.rr_no.contains(search_q)) |
            (Entry.ship_to.contains(search_q))
        )

    entries = query.order_by(Entry.date.desc()).all()

    # CRITICAL: Sending vendors to the template so the dropdown works
    return render_template('view_data.html',
                           entries=entries,
                           month=month,
                           vendor=vendor_filter,
                           search_query=search_q,
                           vendors=Vendor.query.all())

@core_bp.route('/delete/<int:id>')
@login_required
def delete_entry(id):
    entry = Entry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    flash('Entry Deleted')
    return redirect(url_for('core.view_data'))

@core_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    entry = Entry.query.get_or_404(id)
    if request.method == 'POST':
        entry.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        entry.vendor = request.form['vendor']
        entry.rr_no = request.form['rr_no']
        entry.ship_from = request.form['from']
        entry.ship_to = request.form['to']
        entry.parcels = int(request.form['parcels'])
        entry.handling_chg = float(request.form['handling'])
        entry.railway_chg = float(request.form['railway'])
        entry.transport_chg = float(request.form['transport'])
        entry.total = entry.handling_chg + entry.railway_chg + entry.transport_chg

        db.session.commit()
        flash('Entry Updated')
        return redirect(url_for('core.view_data'))

    return render_template('edit.html', entry=entry, vendors=Vendor.query.all())