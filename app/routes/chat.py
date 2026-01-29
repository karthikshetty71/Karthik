from flask import Blueprint, request, jsonify
from datetime import date, datetime
from app.models import Entry, Vendor, AuditLog, User
from app.extensions import db
from sqlalchemy import func

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
def chat_response():
    try:
        user_msg = request.json.get('message', '').lower()
        today = date.today()
        response_text = "I'm not sure about that. Try asking for 'Today's revenue' or 'Vendor rates'."
        action_link = None

        # --- 1. REVENUE & PERFORMANCE ---
        if any(x in user_msg for x in ['revenue', 'collection', 'total']):
            if 'month' in user_msg:
                month_str = today.strftime('%Y-%m')
                m_rev = db.session.query(func.sum(Entry.grand_total)).filter(func.strftime('%Y-%m', Entry.date) == month_str).scalar() or 0
                response_text = f"Total revenue for <b>{today.strftime('%B')}</b> is <b class='text-green-400'>₹{m_rev:,.0f}</b>."
            else:
                d_rev = db.session.query(func.sum(Entry.grand_total)).filter(Entry.date == today).scalar() or 0
                response_text = f"Today's revenue is <b class='text-green-400'>₹{d_rev:,.0f}</b>."

        # --- 2. VENDOR COMPARISON ---
        elif 'compare' in user_msg and 'rate' in user_msg:
            vendors = Vendor.query.all()
            if vendors:
                cheapest = min(vendors, key=lambda x: x.rate_per_parcel)
                response_text = f"Comparison: <b>{cheapest.name}</b> has the lowest rate at <b class='text-blue-400'>₹{cheapest.rate_per_parcel}</b> per parcel."
            else:
                response_text = "No vendors found to compare."

        # --- 3. SYSTEM AUDIT / LOGS (FIXED LOGIC) ---
        elif any(x in user_msg for x in ['log', 'activity', 'who', 'user']):
            # Join with User to ensure we can get the username
            last_log = db.session.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()

            if last_log:
                # Get username safely
                u_name = "System"
                if last_log.user_id:
                    u = User.query.get(last_log.user_id)
                    u_name = u.username if u else "Unknown"

                response_text = f"🕒 Last activity: <b>{last_log.action}</b><br>User: <b>{u_name}</b><br>Time: {last_log.timestamp.strftime('%d %b, %H:%M')}."
            else:
                response_text = "The activity log is currently empty."

        # --- 4. VENDOR DEEP DIVE ---
        elif any(x in user_msg for x in ['rate', 'pending', 'balance']):
            vendors = Vendor.query.all()
            found_vendor = next((v for v in vendors if v.name.lower() in user_msg), None)

            if found_vendor:
                if any(x in user_msg for x in ['pending', 'balance']):
                    response_text = f"<b>{found_vendor.name}</b> has a pending balance of <b class='text-red-400'>₹{found_vendor.pending_balance:,.0f}</b>."
                    action_link = f"/view?vendor={found_vendor.id}&mode=admin"
                else:
                    response_text = f"<b>{found_vendor.name}</b>:<br>• Parcel Rate: ₹{found_vendor.rate_per_parcel}<br>• Transport: ₹{found_vendor.transport_rate}"
            else:
                response_text = "Which vendor? (e.g., 'What is the rate for Shiva?')"

        # --- 5. NAVIGATION ---
        elif 'invoice' in user_msg:
            response_text = "Opening Invoice Generator..."
            action_link = "/invoices"

        return jsonify({"response": response_text, "link": action_link})

    except Exception as e:
        # This catches the error and tells you exactly what went wrong in the console
        print(f"Chat Error: {str(e)}")
        return jsonify({"response": "I had trouble accessing the database. Please try again in a moment.", "link": None})