from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime
from app.models import Entry, Vendor
from sqlalchemy import func
from num2words import num2words

# Define Blueprint
reports_bp = Blueprint('reports', __name__)

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

    # 1. Fetch Vendor Details & Settings
    # We need the full object to access .show_rr, .show_handling, etc.
    vendor_obj = Vendor.query.filter_by(name=vendor_name).first()

    # Determine Display Name & Address (Fallback if empty)
    # If billing_name is set in Admin, use it. Otherwise use internal name.
    display_name = vendor_obj.billing_name if (vendor_obj and vendor_obj.billing_name) else vendor_name
    display_address = vendor_obj.billing_address if (vendor_obj and vendor_obj.billing_address) else "Manipal / Udupi"

    # 2. Fetch Entries for this Month & Vendor
    entries = Entry.query.filter(
        func.strftime('%Y-%m', Entry.date) == month,
        Entry.vendor == vendor_name
    ).order_by(Entry.date).all()

    if not entries:
        flash(f"No records found for {vendor_name} in {month}")
        return redirect(url_for('reports.selection'))

    # 3. Calculate Totals
    total_parcels = sum(e.parcels for e in entries)
    grand_total = sum(e.total for e in entries)

    # 4. Format Data for Display
    invoice_no = f"INV-{month.replace('-','')}-{datetime.now().strftime('%d%H')}"
    display_month = datetime.strptime(month, '%Y-%m').strftime('%B %Y')

    # 5. Convert Total to Words (Indian Format)
    try:
        total_words = num2words(grand_total, lang='en_IN') + " Rupees Only"
    except:
        total_words = f"{grand_total} Rupees Only"

    # 6. Render the PDF Template
    return render_template('invoice_print.html',
                           vendor=display_name,       # Name on Bill
                           address=display_address,   # Address on Bill
                           vendor_settings=vendor_obj, # <--- THIS FIXES THE ERROR (Passes checkboxes)
                           entries=entries,
                           month=display_month,
                           invoice_no=invoice_no,
                           total_parcels=total_parcels,
                           grand_total=grand_total,
                           total_words=total_words)