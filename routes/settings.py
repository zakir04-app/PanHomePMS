from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from routes import settings_bp
from models import db, AppUser, Camp 
from config import Config
from sqlalchemy import func

# --- Settings & User Management Routes ---
@settings_bp.route('/', methods=['GET'])
@login_required
def settings_dashboard():
    # Admin must hit this route to see the full panel
    if not current_user.is_admin():
        return redirect(url_for('settings.change_appearance_view'))

    users = AppUser.query.all()
    
    # FIX: is_appearance_only=False ensures the template renders the User Management table.
    return render_template('settings.html', 
                           users=users, 
                           roles=Config.USER_ROLES, 
                           is_appearance_only=False)

@settings_bp.route('/appearance', methods=['GET', 'POST'])
@login_required
def change_appearance_view():
    """Handles theme settings (accessible by all users)."""
    if request.method == 'POST':
        theme = request.form.get('theme')
        font_style = request.form.get('font_style')
        font_size = request.form.get('font_size')
        user = db.session.get(AppUser, current_user.id)
        if theme in ['default', 'dark', 'light', 'blue', 'ocean', 'skyblue', 'darkgreen', 'darkgold']:
            user.theme = theme
        if font_style in ['inter', 'poppins', 'roboto-slab']:
            user.font_style = font_style
        if font_size in ['small', 'normal', 'large']:
            user.font_size = font_size
        db.session.commit()
        flash('Appearance settings updated successfully!', 'success')
        return redirect(url_for('settings.change_appearance_view'))
    
    # Renders the appearance section for all users.
    return render_template('settings.html', 
                           is_appearance_only=True, 
                           roles=Config.USER_ROLES,
                           users=None) 

@settings_bp.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin():
        flash("Permission denied.", 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        if AppUser.query.filter_by(username=username).first():
            flash("Username already exists.", 'danger')
        else:
            new_user = AppUser(
                username=username, email=request.form.get('email'),
                mobile=request.form.get('mobile'), password=request.form.get('password'),
                role=request.form.get('role')
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f"User {username} added successfully! Now set their permissions.", 'success')
            return redirect(url_for('settings.edit_user_permissions', user_id=new_user.id))
            
    return render_template('add_user.html', roles=Config.USER_ROLES)

@settings_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin():
        flash("Permission denied.", 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))
        
    user_to_edit = db.session.get(AppUser, user_id)
    if not user_to_edit:
        flash("User not found.", "danger")
        return redirect(url_for('settings.settings_dashboard'))
    
    if request.method == 'POST':
        user_to_edit.username = request.form.get('username')
        user_to_edit.email = request.form.get('email')
        user_to_edit.mobile = request.form.get('mobile')
        user_to_edit.role = request.form.get('role')
        new_password = request.form.get('password')
        if new_password:
            user_to_edit.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash("User updated successfully! Now manage their permissions.", 'success')
        return redirect(url_for('settings.edit_user_permissions', user_id=user_id))
        
    return render_template('edit_user.html', user=user_to_edit, roles=Config.USER_ROLES)

@settings_bp.route('/permissions/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user_permissions(user_id):
    if not current_user.is_admin():
        flash("Permission denied.", 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))
        
    user_to_edit = db.session.get(AppUser, user_id)
    if not user_to_edit:
        flash("User not found.", "danger")
        return redirect(url_for('settings.settings_dashboard'))
    
    all_locations_query = Camp.query.filter(Camp.location.isnot(None)).with_entities(Camp.location).distinct().order_by(Camp.location).all()
    all_locations = [loc[0] for loc in all_locations_query if loc[0]]

    if request.method == 'POST':
        allowed_locations = request.form.getlist('allowed_locations')
        user_to_edit.allowed_locations = ','.join(allowed_locations)
        
        feature_permissions = request.form.getlist('feature_permissions')
        user_to_edit.permissions = ','.join(feature_permissions)
        
        db.session.commit()
        flash(f"Permissions for {user_to_edit.username} updated successfully!", 'success')
        return redirect(url_for('settings.settings_dashboard'))

    user_allowed_locations = user_to_edit.allowed_locations.split(',')
    user_permissions = user_to_edit.permissions.split(',')
    
    return render_template('edit_user_permissions.html', 
                           user=user_to_edit,
                           all_locations=all_locations,
                           feature_permissions=Config.FEATURE_PERMISSIONS,
                           user_allowed_locations=user_allowed_locations,
                           user_permissions=user_permissions)

@settings_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin():
        flash("Permission denied.", 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))
        
    if user_id == current_user.id:
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('settings.settings_dashboard'))
        
    user_to_delete = db.session.get(AppUser, user_id)
    if user_to_delete:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("User deleted successfully!", 'success')
    else:
        flash("User not found.", "danger")
    return redirect(url_for('settings.settings_dashboard'))