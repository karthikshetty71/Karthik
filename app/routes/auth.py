from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from app.models import User
from app.extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, send to home
    if current_user.is_authenticated:
        return redirect(url_for('core.home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # --- SECURITY CHECK: IS ACCOUNT ACTIVE? ---
            if not user.is_active:
                flash('Your account has been disabled. Please contact the Admin.')
                return redirect(url_for('auth.login'))
            # ------------------------------------------

            login_user(user)
            return redirect(url_for('core.home'))

        flash('Invalid Credentials')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))