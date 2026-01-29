from flask import Blueprint, render_template, request, Response
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime
from num2words import num2words
from app.models import Entry, Vendor
from app.extensions import db
import csv
import io

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/analytics')
@login_required
def analytics():
    monthly_data = db.session.query(
        func.strftime('%Y-%m', Entry.date).label('month'),
        func.sum(Entry.total).label('total')
    ).group_by('month').order_by('month').all()
    labels = [d.month for d in monthly_data]
    values = [d.total for d in monthly_data]
    return render_template('analytics.html', labels=labels, values=values)

@reports_bp.route('/invoices')
@login_required
def invoices():
    return render_template('invoices_select.html', today=datetime.today().strftime('%Y-%m'), vendors=Vendor.query.all())

@reports_bp.route('/generate_bill')
@login_required
def generate_bill():
    month = request.args.get('month')
    vendor = request.args.get('vendor')
    
    entries = Entry.query.filter(db.cast(Entry.date, db.String).like(f'{month}%'))
    if vendor != 'All':
        entries = entries.filter_by(vendor=vendor)
    entries = entries.order_by(Entry.date).all()
    
    grand_total = sum(e.total for e in entries)
    total_parcels = sum(e.parcels for e in entries)
    total_words = num2words(grand_total, lang='en_IN').title().replace("-", " ") + " Only"
    
    # --- NEW: Generate Single Invoice Number for Header ---
    # Format: INV-YYYYMM-VENDOR (e.g. INV-202409-MAN)
    clean_month = month.replace('-', '')
    clean_vendor = vendor[:3].upper() if vendor != 'All' else 'ALL'
    invoice_no = f"INV-{clean_month}-{clean_vendor}"
    
    return render_template('invoice_print.html', 
                           entries=entries, 
                           month=month, 
                           vendor=vendor, 
                           grand_total=grand_total, 
                           total_parcels=total_parcels, 
                           total_words=total_words,
                           invoice_no=invoice_no) # Passing the new ID

@reports_bp.route('/export_csv')
@login_required
def export_csv():
    month = request.args.get('month', datetime.today().strftime('%Y-%m'))
    entries = Entry.query.filter(db.cast(Entry.date, db.String).like(f'{month}%')).order_by(Entry.date).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Bill No', 'RR No', 'Vendor', 'From', 'To', 'Parcels', 'Handling', 'Railway', 'Transport', 'Total'])
    for e in entries:
        writer.writerow([e.date, e.bill_no, e.rr_no, e.vendor, e.ship_from, e.ship_to, e.parcels, e.handling_chg, e.railway_chg, e.transport_chg, e.total])
        
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": f"attachment; filename=kps_export_{month}.csv"})