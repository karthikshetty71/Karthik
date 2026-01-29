from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from app.models import User
from app.extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('core.home'))
        flash('Invalid Credentials')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if not current_user.is_admin:
        return redirect(url_for('core.home'))
        
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first():
            flash('User exists')
        else:
            new_user = User(username=username, is_admin='is_admin' in request.form)
            new_user.set_password(request.form['password'])
            db.session.add(new_user)
            db.session.commit()
            
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@auth_bp.route('/admin/delete_user/<int:id>')
@login_required
def delete_user(id):
    if not current_user.is_admin or current_user.id == id:
        return redirect(url_for('auth.admin_users'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('auth.admin_users'))