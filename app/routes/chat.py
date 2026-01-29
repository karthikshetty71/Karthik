from flask import Blueprint, request, jsonify
from datetime import date, datetime
from app.models import Entry, Vendor, AuditLog
from app.extensions import db
from sqlalchemy import func
import calendar

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
def chat_response():
    try:
        user_msg = request.json.get('message', '').lower()
        today = date.today()
        month_str = today.strftime('%Y-%m')
        response_text = "I'm not sure about that. Try: 'Monthly summary', 'Top routes', or 'Compare rates'."
        action_link = None

        # --- 1. REVENUE & PERFORMANCE (Daily & Monthly) ---
        if any(x in user_msg for x in ['revenue', 'collection', 'total', 'summary']):
            if 'month' in user_msg or 'summary' in user_msg:
                # Monthly stats
                m_data = db.session.query(
                    func.sum(Entry.grand_total),
                    func.sum(Entry.parcels)
                ).filter(func.strftime('%Y-%m', Entry.date) == month_str).first()

                rev = m_data[0] or 0
                parcels = m_data[1] or 0
                response_text = f"📊 <b>{today.strftime('%B')} Summary:</b><br>• Total Revenue: <b>₹{rev:,.0f}</b><br>• Total Parcels: <b>{parcels}</b>"
            else:
                # Daily stats
                d_rev = db.session.query(func.sum(Entry.grand_total)).filter(Entry.date == today).scalar() or 0
                response_text = f"💰 Today's revenue is <b>₹{d_rev:,.0f}</b>."

        # --- 2. ROUTE ANALYTICS ---
        elif any(x in user_msg for x in ['route', 'destination', 'top']):
            top_route = db.session.query(
                Entry.ship_to, func.count(Entry.id)
            ).group_by(Entry.ship_to).order_by(func.count(Entry.id).desc()).first()

            if top_route:
                response_text = f"🚚 Your most active destination is <b>{top_route[0]}</b> with {top_route[1]} entries this month."
            else:
                response_text = "I don't have enough route data yet."

        # --- 3. SYSTEM LOGS (Matching your AuditLog Model) ---
        elif any(x in user_msg for x in ['log', 'activity', 'who', 'user']):
            last_log = AuditLog.query.order_by(AuditLog.timestamp.desc()).first()
            if last_log:
                u_name = last_log.username or "System"
                response_text = f"🕒 <b>Last Activity:</b> {last_log.action}<br><b>User:</b> {u_name}<br><b>Time:</b> {last_log.timestamp.strftime('%H:%M')} ({last_log.details})"
            else:
                response_text = "No activity logs found."

        # --- 4. VENDOR RATES & COMPARISON ---
        elif any(x in user_msg for x in ['rate', 'pending', 'compare', 'best']):
            vendors = Vendor.query.all()

            if 'compare' in user_msg or 'best' in user_msg:
                cheapest = min(vendors, key=lambda x: x.rate_per_parcel)
                response_text = f"⚖️ <b>Comparison:</b> {cheapest.name} has the best rate at <b>₹{cheapest.rate_per_parcel}</b> per parcel."
            else:
                # Specific vendor lookup
                found_v = next((v for v in vendors if v.name.lower() in user_msg), None)
                if found_v:
                    if 'pending' in user_msg or 'balance' in user_msg:
                        response_text = f"<b>{found_v.name}</b> pending balance: <b class='text-red-400'>₹{found_v.pending_balance:,.0f}</b>."
                    else:
                        response_text = f"<b>{found_v.name}</b>:<br>• Rate: ₹{found_v.rate_per_parcel}<br>• Trans: ₹{found_v.transport_rate}"
                else:
                    response_text = "Please mention a vendor name (e.g., 'Rate for Shiva')."

        # --- 5. NAVIGATION ---
        elif 'invoice' in user_msg or 'bill' in user_msg:
            response_text = "Redirecting to Invoice section..."
            action_link = "/invoices"

        return jsonify({"response": response_text, "link": action_link})

    except Exception as e:
        print(f"❌ Chatbot Error: {str(e)}")
        return jsonify({"response": "I had trouble accessing the database. Please try again.", "link": None})