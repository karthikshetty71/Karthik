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

        # Calculate Last Month for Comparison
        first_day_this_month = today.replace(day=1)
        last_month_date = first_day_this_month - timedelta(days=1)
        month_last = last_month_date.strftime('%Y-%m')

        # Advanced Response Object
        res = {
            "text": "SYSTEM_UNKNOWN_COMMAND: Type 'help' for directory.",
            "type": "neutral",
            "link": None
        }

        # --- A. ANALYTICS & GROWTH (Smart Comparison) ---
        if any(x in user_msg for x in ['growth', 'performance', 'compare', 'analysis', 'revenue', 'sales']):
            curr_rev = db.session.query(func.sum(Entry.grand_total)).filter(func.strftime('%Y-%m', Entry.date) == month_now).scalar() or 0
            prev_rev = db.session.query(func.sum(Entry.grand_total)).filter(func.strftime('%Y-%m', Entry.date) == month_last).scalar() or 0

            diff = curr_rev - prev_rev
            pct = (diff / prev_rev * 100) if prev_rev > 0 else 100
            trend = "📈 UP" if diff >= 0 else "📉 DOWN"

            res["text"] = f"""
                <div class='border-l-4 border-blue-500 pl-3'>
                    <p class='text-[10px] text-blue-400 font-mono'>FINANCIAL_PERFORMANCE</p>
                    <p class='text-sm text-white'>Current Month: <b>₹{curr_rev:,.0f}</b></p>
                    <p class='text-xs { 'text-green-400' if diff >= 0 else 'text-red-400' }'>
                        {trend} by {abs(pct):.1f}% vs last month.
                    </p>
                </div>
            """
            res["type"] = "success"

        # --- B. PROACTIVE AUDIT (Finding Errors) ---
        elif any(x in user_msg for x in ['check', 'audit', 'error', 'health', 'issue']):
            missing_rr = Entry.query.filter((Entry.rr_no == '') | (Entry.rr_no == None)).count()
            unassigned_rates = Vendor.query.filter(Vendor.rate_per_parcel == 0).count()

            res["text"] = f"""
                <div class='bg-red-900/10 border border-red-500/20 p-2 rounded'>
                    <p class='text-xs text-red-400 font-bold'>INTEGRITY_SCAN_RESULTS</p>
                    <p class='text-[11px] text-gray-300'>• Missing RR entries: {missing_rr}</p>
                    <p class='text-[11px] text-gray-300'>• Zero-rate Vendors: {unassigned_rates}</p>
                    <p class='text-[11px] font-bold mt-1'>Action Required: {'Review Data' if missing_rr > 0 else 'None'}</p>
                </div>
            """
            res["link"] = "/view" if missing_rr > 0 else None
            res["type"] = "warning"

        # --- C. VENDOR DEEP SEARCH ---
        elif any(x in user_msg for x in ['vendor', 'rate', 'pending', 'balance']):
            vendors = Vendor.query.all()
            found_v = next((v for v in vendors if v.name.lower() in user_msg), None)

            if found_v:
                res["text"] = f"""
                    <div class='border-l-4 border-purple-500 pl-3'>
                        <p class='text-white font-bold'>{found_v.name.upper()}</p>
                        <p class='text-[11px] text-gray-400'>Rate: ₹{found_v.rate_per_parcel} | Bal: ₹{found_v.pending_balance:,.0f}</p>
                    </div>
                """
                res["link"] = f"/view?vendor={found_v.id}&mode=admin"
            else:
                res["text"] = "VENDOR_NOT_FOUND. Please specify valid name (e.g. Shiva, Udupi)."

        # --- D. SYSTEM LOGS ---
        elif any(x in user_msg for x in ['who', 'user', 'activity', 'log']):
            last_log = AuditLog.query.order_by(AuditLog.timestamp.desc()).first()
            if last_log:
                res["text"] = f"AUTH_LOG: <b>{last_log.username}</b> accessed <i>{last_log.action}</i> at {last_log.timestamp.strftime('%H:%M')}."
            else:
                res["text"] = "LOG_BUFFER_EMPTY."

        # --- E. GREETINGS & HELP ---
        elif any(x in user_msg for x in ['hi', 'hello', 'help']):
            res["text"] = "KPS_CORE_v2.1 Online. Available Modules: PERFORMANCE, AUDIT, VENDOR_CHECK, LOGS."

        return jsonify(res)

    except Exception as e:
        print(f"❌ Core Error: {str(e)}")
        return jsonify({"text": "CORE_EXCEPTION_TRIGGERED. Check server logs.", "type": "error"})