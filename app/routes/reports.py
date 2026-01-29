from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from app.models import Entry, Vendor, AuditLog
from app.extensions import db
from sqlalchemy import func
from num2words import num2words
import calendar

reports_bp = Blueprint('reports', __name__)

# --- INVOICES SECTION (Unchanged) ---
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
    vendor_id = request.args.get('vendor')
    include_pending = request.args.get('include_pending')

    if not month or not vendor_id:
        flash("Please select month and vendor")
        return redirect(url_for('reports.selection'))

    vendor_obj = Vendor.query.get(vendor_id)
    if not vendor_obj:
        flash("Vendor not found")
        return redirect(url_for('reports.selection'))

    display_name = vendor_obj.billing_name if vendor_obj.billing_name else vendor_obj.name
    display_address = vendor_obj.billing_address if vendor_obj.billing_address else "Manipal / Udupi"

    entries = Entry.query.filter(
        func.strftime('%Y-%m', Entry.date) == month,
        Entry.vendor_id == vendor_obj.id
    ).order_by(Entry.date).all()

    if not entries:
        flash(f"No records found for {vendor_obj.name} in {month}")
        return redirect(url_for('reports.selection'))

    total_parcels = sum(e.parcels for e in entries)
    current_bill_total = sum(e.grand_total for e in entries)

    pending_amount = 0.0
    if include_pending == 'on':
        pending_amount = vendor_obj.pending_balance

    grand_total = current_bill_total + pending_amount
    invoice_no = f"INV-{month.replace('-','')}-{datetime.now().strftime('%d%H')}"
    display_month = datetime.strptime(month, '%Y-%m').strftime('%B %Y')

    try:
        total_words = num2words(grand_total, lang='en_IN') + " Rupees Only"
    except:
        total_words = f"{grand_total} Rupees Only"

    AuditLog.log(current_user, "INVOICE", f"Generated invoice for {vendor_obj.name} ({month})")

    return render_template('invoice_print.html',
                           vendor=display_name,
                           address=display_address,
                           vendor_settings=vendor_obj,
                           entries=entries,
                           month=display_month,
                           invoice_no=invoice_no,
                           total_parcels=total_parcels,
                           current_bill_total=current_bill_total,
                           pending_amount=pending_amount,
                           grand_total=grand_total,
                           total_words=total_words)

# --- ANALYTICS DASHBOARD (Updated with Filters) ---
@reports_bp.route('/analytics')
@login_required
def analytics():
    today = date.today()
    current_month_str = today.strftime('%Y-%m')

    # 1. GET FILTER
    vendor_id = request.args.get('vendor')

    # 2. PREPARE BASE QUERIES
    # Current Month Query (For Cards)
    current_month_query = Entry.query.filter(func.strftime('%Y-%m', Entry.date) == current_month_str)

    # Trend Query (For Line Chart)
    trend_query = db.session.query(
        func.strftime('%Y-%m', Entry.date).label('month'),
        func.sum(Entry.grand_total).label('revenue')
    )

    # Routes Query
    route_query = db.session.query(
        Entry.ship_to,
        func.count(Entry.id).label('count')
    )

    # Daily Query
    daily_query = db.session.query(
        func.strftime('%d', Entry.date).label('day'),
        func.sum(Entry.parcels).label('parcels')
    ).filter(func.strftime('%Y-%m', Entry.date) == current_month_str)

    # 3. APPLY VENDOR FILTER
    if vendor_id and vendor_id != 'All':
        v_id = int(vendor_id)
        current_month_query = current_month_query.filter(Entry.vendor_id == v_id)
        trend_query = trend_query.filter(Entry.vendor_id == v_id)
        route_query = route_query.filter(Entry.vendor_id == v_id)
        daily_query = daily_query.filter(Entry.vendor_id == v_id)

    # 4. EXECUTE QUERIES
    # KPI Cards
    current_month_entries = current_month_query.all()
    kpi_revenue = sum(e.grand_total for e in current_month_entries)
    kpi_parcels = sum(e.parcels for e in current_month_entries)
    kpi_avg_price = (kpi_revenue / kpi_parcels) if kpi_parcels > 0 else 0
    kpi_vendors_active = len(set(e.vendor_id for e in current_month_entries))

    # Revenue Trend
    monthly_data = trend_query.group_by('month').order_by('month').limit(6).all()
    trend_labels = []
    trend_data = []
    for d in monthly_data:
        if d.month:
            trend_labels.append(datetime.strptime(d.month, '%Y-%m').strftime('%b'))
            trend_data.append(d.revenue)

    # Vendor Share (Pie Chart)
    vendor_share_query = db.session.query(
        Vendor.name,
        func.sum(Entry.grand_total).label('total_rev')
    ).join(Vendor, Entry.vendor_id == Vendor.id)

    if vendor_id and vendor_id != 'All':
         vendor_share_query = vendor_share_query.filter(Entry.vendor_id == int(vendor_id))

    vendor_share_results = vendor_share_query.group_by(Vendor.name).order_by(func.sum(Entry.grand_total).desc()).limit(5).all()

    pie_labels = [row[0] for row in vendor_share_results]
    pie_data = [row[1] for row in vendor_share_results]

    # Top Routes
    top_routes = route_query.group_by(Entry.ship_to).order_by(func.count(Entry.id).desc()).limit(5).all()

    # Daily Activity
    daily_data = daily_query.group_by('day').all()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    daily_map = {int(d.day): d.parcels for d in daily_data}

    bar_labels = [str(i) for i in range(1, days_in_month + 1)]
    bar_data = [daily_map.get(i, 0) for i in range(1, days_in_month + 1)]

    # 5. RENDER
    return render_template('analytics.html',
                           vendors=Vendor.query.all(), # Passed for dropdown
                           selected_vendor=vendor_id,  # To maintain selection state
                           kpi_revenue=kpi_revenue, kpi_parcels=kpi_parcels,
                           kpi_avg_price=round(kpi_avg_price, 2), kpi_vendors=kpi_vendors_active,
                           current_month_name=today.strftime('%B'),
                           trend_labels=trend_labels, trend_data=trend_data,
                           pie_labels=pie_labels, pie_data=pie_data,
                           bar_labels=bar_labels, bar_data=bar_data,
                           top_routes=top_routes)