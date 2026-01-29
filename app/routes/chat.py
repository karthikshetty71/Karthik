from flask import Blueprint, request, jsonify, url_for
from datetime import date
from app.models import Entry, Vendor
from sqlalchemy import func

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
def chat_response():
    user_msg = request.json.get('message', '').lower()
    today = date.today()
    response_text = "I didn't understand that. Try asking about 'Revenue', 'Pending Balance', or 'Vendor Rates'."
    action_link = None

    # --- LOGIC ENGINE ---

    # 1. REVENUE / COLLECTIONS
    if 'revenue' in user_msg or 'collection' in user_msg or 'total' in user_msg:
        entries = Entry.query.filter_by(date=today).all()
        total = sum(e.grand_total for e in entries)
        parcels = sum(e.parcels for e in entries)
        response_text = f"Today's Total Revenue is <b class='text-green-400'>₹{total:,.0f}</b> from {parcels} parcels."

    # 2. VENDOR SPECIFIC QUERIES (Rate, Pending, History)
    elif any(x in user_msg for x in ['rate', 'pending', 'balance', 'due']):
        # Find which vendor is mentioned
        vendors = Vendor.query.all()
        found_vendor = None
        for v in vendors:
            if v.name.lower() in user_msg:
                found_vendor = v
                break

        if found_vendor:
            if 'pending' in user_msg or 'balance' in user_msg or 'due' in user_msg:
                response_text = f"The pending balance for <b>{found_vendor.name}</b> is <b class='text-red-400'>₹{found_vendor.pending_balance:,.0f}</b>."
            elif 'rate' in user_msg:
                response_text = f"<b>{found_vendor.name}</b> rates:<br>Per Parcel: ₹{found_vendor.rate_per_parcel}<br>Transport: ₹{found_vendor.transport_rate}"
        else:
            response_text = "Which vendor are you asking about? Please type the vendor name."

    # 3. NAVIGATION TASKS
    elif 'invoice' in user_msg or 'bill' in user_msg:
        response_text = "Click below to generate an invoice."
        action_link = "/invoices"

    elif 'analytics' in user_msg or 'graph' in user_msg:
        response_text = "Opening Analytics Dashboard..."
        action_link = "/analytics"

    elif 'add' in user_msg or 'entry' in user_msg:
        response_text = "Go to Home to add a new entry."
        action_link = "/home"

    # 4. GREETINGS / HELP
    elif 'hello' in user_msg or 'hi' in user_msg:
        response_text = "Hello! I am KPS Bot. Ask me about:<br>• Today's Revenue<br>• Vendor Pending Balances<br>• Vendor Rates"

    return jsonify({"response": response_text, "link": action_link})