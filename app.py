import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user, login_required
from sqlalchemy import func
from flask import send_from_directory # Import for the download_file utility

# Local imports
from config import Config
from models import db, AppUser
from routes import auth_bp, dashboard_bp, staff_mgmt_bp, inventory_bp, maintenance_bp, amcs_bp, settings_bp

# Utility functions (kept here for global access)
@dashboard_bp.route('/uploads/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    
    # Setup Upload Folder
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Login Manager Setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login' 

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(AppUser, int(user_id))
    
    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(staff_mgmt_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(amcs_bp)
    app.register_blueprint(settings_bp)

    # Global Index Route
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Temporary Database Setup Route
    @app.route('/create-tables/<string:secret_key>')
    def create_tables(secret_key):
        from werkzeug.security import generate_password_hash 
        if secret_key != 'SETUP-DATABASE-NOW':
            return "Invalid secret key.", 403
        try:
            with app.app_context():
                db.create_all()
                if not AppUser.query.filter_by(username='admin').first():
                    new_admin = AppUser(
                        username='admin', 
                        email='admin@example.com', 
                        mobile='N/A', 
                        password='admin123', 
                        role='Admin' # Use capitalized 'Admin'
                    )
                    db.session.add(new_admin)
                    db.session.commit()
                    return "Tables created successfully and admin user added!"
                else:
                    return "Tables already exist, and admin user is already present."
        except Exception as e:
            return f"An error occurred: {e}"
            
    return app
# Global application instance defined by calling the factory function.
# Gunicorn executes this line and finds the 'app' variable it needs.
app = create_app() 
if __name__ == '__main__':
    # When running locally (python app.py), run initial setup and start server
    with app.app_context():
        db.create_all()
        if not AppUser.query.filter_by(username='admin').first():
            new_admin = AppUser(username='admin', email='admin@panhome.com', mobile='N/A', password='admin123', role='Admin')
            db.session.add(new_admin)
            db.session.commit()
    app.run(debug=True)