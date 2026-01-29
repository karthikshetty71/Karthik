from flask import Blueprint, request, jsonify
from datetime import date, datetime, timedelta
from app.models import Entry, Vendor, AuditLog
from app.extensions import db
from sqlalchemy import func

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
def chat_response():
    try:
        user_msg = request.json.get('message', '').lower().strip()
        today = date.today()
        month_str = today.strftime('%Y-%m')

        # Default response
        response_text = "I'm here to help! You can ask about revenue, check vendor balances, or find the best rates. Try: 'Who logged in last?'"
        action_link = None

        # --- 1. SMART GREETINGS ---
        if any(x in user_msg for x in ['hi', 'hello', 'hey', 'good morning', 'good evening']):
            hour = datetime.now().hour
            greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
            response_text = f"👋 {greeting}! I'm your KPS Assistant. I can summarize your <b>Monthly Revenue</b>, find <b>Top Routes</b>, or check <b>Vendor Rates</b>. What's on your mind?"

        # --- 2. PROACTIVE DATA AUDIT (Smart Check) ---
        elif any(x in user_msg for x in ['check', 'missing', 'audit', 'error', 'issue']):
            # Check for entries in the last 7 days missing RR numbers
            last_week = today - timedelta(days=7)
            missing_rr = Entry.query.filter(Entry.date >= last_week, (Entry.rr_no == '') | (Entry.rr_no == None)).count()

            if missing_rr > 0:
                response_text = f"⚠️ <b>Audit Alert:</b> I found <b>{missing_rr} entries</b> from the last 7 days missing an RR number. You might want to update them."
                action_link = "/view"
            else:
                response_text = "✅ <b>System Check:</b> All entries from the last week look perfect! No missing RR numbers found."

        # --- 3. REVENUE & PERFORMANCE ---
        elif any(x in user_msg for x in ['revenue', 'collection', 'total', 'money', 'sales']):
            if 'month' in user_msg or 'summary' in user_msg:
                m_data = db.session.query(
                    func.sum(Entry.grand_total),
                    func.sum(Entry.parcels)
                ).filter(func.strftime('%Y-%m', Entry.date) == month_str).first()

                rev = m_data[0] or 0
                parcels = m_data[1] or 0
                response_text = f"📊 <b>{today.strftime('%B')} at a glance:</b><br>• Total Revenue: <b>₹{rev:,.0f}</b><br>• Total Parcels: <b>{parcels}</b><br>Great progress so far!"
            else:
                d_rev = db.session.query(func.sum(Entry.grand_total)).filter(Entry.date == today).scalar() or 0
                response_text = f"💰 Today's collection is <b>₹{d_rev:,.0f}</b>. Need a monthly breakdown?"

        # --- 4. TOP DESTINATIONS ---
        elif any(x in user_msg for x in ['route', 'destination', 'place', 'going']):
            top_route = db.session.query(
                Entry.ship_to, func.count(Entry.id)
            ).filter(func.strftime('%Y-%m', Entry.date) == month_str)\
             .group_by(Entry.ship_to).order_by(func.count(Entry.id).desc()).first()

            if top_route:
                response_text = f"🚚 <b>Top Destination:</b> Most of your parcels are currently heading to <b>{top_route[0]}</b> ({top_route[1]} shipments this month)."
            else:
                response_text = "I don't have enough shipping data to calculate routes yet."

        # --- 5. LOGS & SECURITY (Using your username field) ---
        elif any(x in user_msg for x in ['who', 'user', 'activity', 'log', 'last action']):
            last_log = AuditLog.query.order_by(AuditLog.timestamp.desc()).first()
            if last_log:
                u_name = last_log.username or "System"
                # Formatting time to be more human-readable
                time_str = last_log.timestamp.strftime('%I:%M %p')
                response_text = f"🕒 <b>Recent Activity:</b><br>User <b>{u_name}</b> performed: <i>{last_log.action}</i> at {time_str}.<br>Details: {last_log.details}"
            else:
                response_text = "The activity logs are currently clear."

        # --- 6. VENDOR MANAGEMENT ---
        elif any(x in user_msg for x in ['vendor', 'rate', 'pending', 'balance', 'owe']):
            vendors = Vendor.query.all()
            found_v = next((v for v in vendors if v.name.lower() in user_msg), None)

            if found_v:
                if any(x in user_msg for x in ['pending', 'balance', 'owe']):
                    response_text = f"💳 <b>{found_v.name}</b> has a pending balance of <b class='text-red-400'>₹{found_v.pending_balance:,.0f}</b>."
                    action_link = f"/view?vendor={found_v.id}&mode=admin"
                else:
                    response_text = f"📋 <b>{found_v.name} Rates:</b><br>• Per Parcel: ₹{found_v.rate_per_parcel}<br>• Flat Transport: ₹{found_v.transport_rate}"
            elif 'compare' in user_msg or 'best' in user_msg or 'lowest' in user_msg:
                cheapest = min(vendors, key=lambda x: x.rate_per_parcel)
                response_text = f"⚖️ <b>Rate Comparison:</b> <b>{cheapest.name}</b> offers the best deal at <b>₹{cheapest.rate_per_parcel}</b> per parcel."
            else:
                response_text = "I know all your vendors! Which one are you asking about? (e.g., 'What is Shiva's balance?')"

        # --- 7. HELP / SYSTEM INFO ---
        elif any(x in user_msg for x in ['help', 'what can you do', 'options']):
            response_text = "I can help with:<br>• <b>Revenue</b> (Today or Monthly)<br>• <b>Route Tracking</b> (Top destinations)<br>• <b>Vendor Info</b> (Rates & Balances)<br>• <b>Audits</b> (Check for missing RR numbers)"

        return jsonify({"response": response_text, "link": action_link})

    except Exception as e:
        print(f"❌ Chatbot Error: {str(e)}")
        return jsonify({"response": "I encountered a technical glitch while checking the records.", "link": None})