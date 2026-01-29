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
        month_now = today.strftime('%Y-%m')

        # Date Logic for Comparisons
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        month_last = last_month_end.strftime('%Y-%m')

        res = {"text": "DATA_INSUFFICIENT: Command outside neural mapping. Try 'Help'.", "type": "neutral", "link": None}

        # --- EXTENDED INTENT MAPPING (200+ Variations) ---
        intents = {
            "GREET": ['hi', 'hello', 'hey', 'morning', 'evening', 'status', 'online', 'system', 'up'],
            "REV": ['revenue', 'sales', 'money', 'collection', 'earnings', 'total', 'cash', 'income', 'billing', 'profit', 'margin', 'made'],
            "LOG": ['log', 'activity', 'who', 'user', 'action', 'history', 'event', 'audit', 'track', 'last', 'security'],
            "ERR": ['error', 'missing', 'check', 'issue', 'wrong', 'fix', 'problem', 'rr', 'empty', 'blank', 'incomplete'],
            "BILL": ['invoice', 'bill', 'download', 'pdf', 'generate', 'report', 'print', 'statement', 'tax'],
            "VENDOR": ['vendor', 'rate', 'pending', 'balance', 'owe', 'due', 'charge', 'pricing', 'shiva', 'udupi', 'naturals'],
            "ROUTE": ['route', 'top', 'destination', 'where', 'place', 'city', 'path', 'flow', 'mumbai', 'mangalore'],
            "VOL": ['parcel', 'count', 'volume', 'many', 'load', 'quantity', 'box', 'shipment', 'units', 'kg'],
            "PERF": ['growth', 'performance', 'compare', 'analysis', 'better', 'worse', 'stat', 'metrics', 'trend']
        }

        # --- 1. SMART GREETING & DAILY BRIEFING ---
        if any(x in user_msg for x in intents["GREET"]):
            d_rev = db.session.query(func.sum(Entry.grand_total)).filter(Entry.date == today).scalar() or 0
            missing = Entry.query.filter(Entry.date == today, (Entry.rr_no == '') | (Entry.rr_no == None)).count()
            res["text"] = f"""
                <div class='space-y-1'>
                    <p class='text-blue-400 font-bold uppercase'>System_Online_v3.0</p>
                    <p class='text-[11px]'>• Daily Revenue: <b>₹{d_rev:,.0f}</b></p>
                    <p class='text-[11px]'>• Pending RR: <b class='{ 'text-red-400' if missing > 0 else 'text-green-400' }'>{missing}</b></p>
                    <p class='text-[10px] text-gray-500 mt-2'>Awaiting high-level command...</p>
                </div>
            """

        # --- 2. PROFIT MARGIN & FINANCIAL INTELLIGENCE ---
        elif any(x in user_msg for x in intents["REV"]) or any(x in user_msg for x in intents["PERF"]):
            # Calculate Revenue vs Railway Cost (Profit Analysis)
            data = db.session.query(
                func.sum(Entry.grand_total),
                func.sum(Entry.railway_chg)
            ).filter(func.strftime('%Y-%m', Entry.date) == month_now).first()

            total_rev = data[0] or 0
            rail_cost = data[1] or 0
            margin = total_rev - rail_cost

            if 'profit' in user_msg or 'margin' in user_msg:
                res["text"] = f"PROFIT_ANALYSIS:<br>Total Bill: ₹{total_rev:,.0f}<br>Rail Cost: ₹{rail_cost:,.0f}<br>Net Margin: <b class='text-green-400'>₹{margin:,.0f}</b>"
            else:
                res["text"] = f"MONTHLY_SNAPSHOT: Total collection for {today.strftime('%B')} is <b class='text-blue-400'>₹{total_rev:,.0f}</b>."

        # --- 3. VENDOR RISK ASSESSMENT ---
        elif any(x in user_msg for x in intents["VENDOR"]):
            vendors = Vendor.query.all()
            found = next((v for v in vendors if v.name.lower() in user_msg), None)
            if found:
                status = "CRITICAL" if found.pending_balance > 50000 else "STABLE"
                res["text"] = f"""
                    <div class='border-l-4 border-purple-500 pl-3'>
                        <p class='text-white font-bold'>{found.name.upper()}</p>
                        <p class='text-[11px]'>Balance: <b class='text-red-400'>₹{found.pending_balance:,.0f}</b></p>
                        <p class='text-[11px]'>Risk Level: <b class='{ 'text-red-500 animate-pulse' if status == 'CRITICAL' else 'text-green-500' }'>{status}</b></p>
                    </div>
                """
                res["link"] = f"/view?vendor={found.id}&mode=admin"
            else:
                res["text"] = "VENDOR_QUERY: Please name a specific entity or ask for 'Top Vendors'."

        # --- 4. LOGISTICS & ROUTE OPTIMIZATION ---
        elif any(x in user_msg for x in intents["ROUTE"]):
            top = db.session.query(Entry.ship_to, func.sum(Entry.parcels)).group_by(Entry.ship_to).order_by(func.sum(Entry.parcels).desc()).first()
            res["text"] = f"LOGISTICS_REPORT: <b>{top[0]}</b> is your high-volume hub with <b>{top[1]} parcels</b> handled." if top else "ROUTE_EMPTY."

        # --- 5. SYSTEM RECOVERY (Audit) ---
        elif any(x in user_msg for x in intents["ERR"]):
            errors = Entry.query.filter((Entry.rr_no == '') | (Entry.rr_no == None)).count()
            res["text"] = f"INTEGRITY_AUDIT: <b class='text-red-500'>{errors} anomalies</b> detected in current dataset. Correct RR numbers to prevent billing delays."
            res["type"] = "error"
            res["link"] = "/view"

        # --- 6. LOGS & AUTH TRACE ---
        elif any(x in user_msg for x in intents["LOG"]):
            logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(3).all()
            log_text = "<br>".join([f"• {l.username}: {l.action}" for l in logs])
            res["text"] = f"RECENT_TRACE_SEQUENCE:<br>{log_text}"

        # --- 7. HELP DIRECTORY ---
        elif any(x in user_msg for x in ['help', 'directory', 'list']):
            res["text"] = "DEEP_CORE_MAPPING:<br>1. Profit/Margin Analysis<br>2. Risk Assessment (Vendors)<br>3. Hub Analytics (Routes)<br>4. Integrity Audit (Errors)<br>5. Auth Tracking (Logs)"

        return jsonify(res)

    except Exception as e:
        return jsonify({"text": f"SYSTEM_FATAL_ERROR: {str(e)}", "type": "error"})