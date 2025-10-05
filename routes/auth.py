from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from routes import auth_bp
from models import db, AppUser

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_bp.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = AppUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard_bp.dashboard'))
        else:
            flash("Invalid username or password", "danger")
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot_password')
def forgot_password():
    flash("Please contact your IT administrator to reset your password.", "info")
    return redirect(url_for('auth.login'))