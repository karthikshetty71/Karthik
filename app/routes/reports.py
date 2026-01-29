from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime, date
from app.models import Entry, Vendor
from app.extensions import db
from sqlalchemy import func
from num2words import num2words

reports_bp = Blueprint('reports', __name__)

# --- INVOICES ---
@reports_bp.route('/invoices')
@login_required
def selection():
    today = datetime.today().strftime('%Y-%m')
    vendors = Vendor.query.all()
    return render_template('invoices_select.html', today=today, vendors=vendors)

@reports_bp.route('/generate_bill')
@login_required
def generate_bill():
    month = request.args.get('month')
    vendor_name = request.args.get('vendor')

    if not month or not vendor_name:
        flash("Please select month and vendor")
        return redirect(url_for('reports.selection'))

    # 1. Fetch Vendor (Safe Check)
    vendor_obj = Vendor.query.filter_by(name=vendor_name).first()

    if not vendor_obj:
        # Fallback if vendor was deleted from DB but selected manually
        display_name = vendor_name
        display_address = "Manipal / Udupi"
    else:
        display_name = vendor_obj.billing_name if vendor_obj.billing_name else vendor_name
        display_address = vendor_obj.billing_address if vendor_obj.billing_address else "Manipal / Udupi"

    # 2. Fetch Entries
    entries = Entry.query.filter(
        func.strftime('%Y-%m', Entry.date) == month,
        Entry.vendor == vendor_name
    ).order_by(Entry.date).all()

    if not entries:
        flash(f"No records found for {vendor_name} in {month}")
        return redirect(url_for('reports.selection'))

    # Totals
    total_parcels = sum(e.parcels for e in entries)
    grand_total = sum(e.total for e in entries)

    invoice_no = f"INV-{month.replace('-','')}-{datetime.now().strftime('%d%H')}"
    display_month = datetime.strptime(month, '%Y-%m').strftime('%B %Y')

    try:
        total_words = num2words(grand_total, lang='en_IN') + " Rupees Only"
    except:
        total_words = f"{grand_total} Rupees Only"

    return render_template('invoice_print.html',
                           vendor=display_name,
                           address=display_address,
                           vendor_settings=vendor_obj, # Passes object or None
                           entries=entries,
                           month=display_month,
                           invoice_no=invoice_no,
                           total_parcels=total_parcels,
                           grand_total=grand_total,
                           total_words=total_words)

# --- ANALYTICS ---
@reports_bp.route('/analytics')
@login_required
def analytics():
    # 1. Monthly Revenue (Safe Query)
    monthly_data = db.session.query(
        func.strftime('%Y-%m', Entry.date).label('month'),
        func.sum(Entry.total).label('revenue')
    ).group_by('month').order_by('month').limit(6).all()

    # Safety: Filter out None values in case of bad data
    labels = []
    data = []

    for d in monthly_data:
        if d.month: # Check if month is not None
            try:
                lbl = datetime.strptime(d.month, '%Y-%m').strftime('%b')
                labels.append(lbl)
                data.append(d.revenue)
            except:
                continue

    # 2. Top Vendors
    vendor_stats = db.session.query(
        Entry.vendor,
        func.sum(Entry.parcels).label('total_parcels')
    ).group_by(Entry.vendor).order_by(func.sum(Entry.parcels).desc()).limit(5).all()

    return render_template('analytics.html',
                           labels=labels,
                           data=data,
                           vendor_stats=vendor_stats)