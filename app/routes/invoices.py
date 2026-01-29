from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime
from app.models import Entry, Vendor
from sqlalchemy import func
from num2words import num2words

# Define the Blueprint
invoice_bp = Blueprint('invoices', __name__)

@invoice_bp.route('/invoices')
@login_required
def selection():
    """
    Renders the page to select Month and Vendor for generating the bill.
    """
    today = datetime.today().strftime('%Y-%m')
    vendors = Vendor.query.all()
    return render_template('invoices_select.html', today=today, vendors=vendors)

@invoice_bp.route('/generate_bill')
@login_required
def generate_bill():
    """
    Generates the PDF-friendly invoice page.
    """
    month = request.args.get('month')
    vendor_name = request.args.get('vendor')

    # Validation: Ensure parameters exist
    if not month or not vendor_name:
        flash("Please select month and vendor")
        return redirect(url_for('invoices.selection'))

    # 1. Fetch Vendor Details & Settings
    # We retrieve the full object to access settings like .show_rr, .billing_name, etc.
    vendor_obj = Vendor.query.filter_by(name=vendor_name).first()

    # 2. Determine Display Name & Address
    # Logic: Use the Billing Name if set in Admin, otherwise fallback to the simple Name.
    display_name = vendor_obj.billing_name if (vendor_obj and vendor_obj.billing_name) else vendor_name
    display_address = vendor_obj.billing_address if (vendor_obj and vendor_obj.billing_address) else "Manipal / Udupi"

    # 3. Fetch Entries for this Month & Vendor
    entries = Entry.query.filter(
        func.strftime('%Y-%m', Entry.date) == month,
        Entry.vendor == vendor_name
    ).order_by(Entry.date).all()

    # Check if entries exist
    if not entries:
        flash(f"No records found for {vendor_name} in {month}")
        return redirect(url_for('invoices.selection'))

    # 4. Calculate Totals
    total_parcels = sum(e.parcels for e in entries)
    grand_total = sum(e.total for e in entries)

    # 5. Format Data for Display
    # Invoice format: INV-YYYYMM-DDHH (e.g., INV-202310-2914)
    invoice_no = f"INV-{month.replace('-','')}-{datetime.now().strftime('%d%H')}"
    display_month = datetime.strptime(month, '%Y-%m').strftime('%B %Y')

    # 6. Convert Total to Words (Indian Format approximation)
    try:
        total_words = num2words(grand_total, lang='en_IN') + " Rupees Only"
    except:
        # Fallback if en_IN is not available or error occurs
        total_words = f"{grand_total} Rupees Only"

    # 7. Render the Print Template
    # CRITICAL: We pass 'vendor_settings' so the HTML knows which columns to hide/show
    return render_template('invoice_print.html',
                           vendor=display_name,         # Formal Name for Header
                           address=display_address,     # Address for Header
                           vendor_settings=vendor_obj,  # Object containing checkbox settings (show_rr, etc.)
                           entries=entries,
                           month=display_month,
                           invoice_no=invoice_no,
                           total_parcels=total_parcels,
                           grand_total=grand_total,
                           total_words=total_words)