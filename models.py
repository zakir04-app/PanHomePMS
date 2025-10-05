from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

db = SQLAlchemy()

# --- Models ---
class AppUser(db.Model, UserMixin):
    # FIX: Allows model to be redefined on app reload
    __table_args__ = {'extend_existing': True} 
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='User') # Default to capitalized 'User'
    
    # NEW: RBAC Permissions
    allowed_locations = db.Column(db.String(500), default='') 
    permissions = db.Column(db.String(500), default='') 
    
    theme = db.Column(db.String(20), default='default')
    font_style = db.Column(db.String(20), default='inter')
    font_size = db.Column(db.String(20), default='normal')

    def __init__(self, username, email, mobile, password, role):
        self.username = username
        self.email = email
        self.mobile = mobile
        self.password_hash = generate_password_hash(password)
        self.role = role

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'Admin'

    # RBAC methods
    def can_edit_location(self, location_name):
        """Checks if the user has specific edit permission for a location."""
        if self.is_admin():
            return True
        return location_name in self.allowed_locations.split(',')

    def can_access_feature(self, feature_code):
        """Checks if the user has a global feature permission (e.g., INV_EDIT)."""
        if self.is_admin():
            return True
        # All users automatically have VIEW access if they have EDIT access
        if feature_code == 'INV_VIEW' and 'INV_EDIT' in self.permissions.split(','):
            return True
        return feature_code in self.permissions.split(',')

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accommodation_name = db.Column(db.String(100))
    room = db.Column(db.String(50))
    emp_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    nationality = db.Column(db.String(100))
    mobile_number = db.Column(db.String(20))
    status = db.Column(db.String(50), default='Active')
    food_variety = db.Column(db.String(100))
    meal_time = db.Column(db.String(100))
    location = db.Column(db.String(100))
    remarks = db.Column(db.String(255))
    check_out_date = db.Column(db.String(50))
    shift_out_date = db.Column(db.String(50))

class Camp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(100))

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    quantity = db.Column(db.Integer, default=0)

class InventoryTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    item_name = db.Column(db.String(100))
    type = db.Column(db.String(20))
    quantity = db.Column(db.Integer)
    date = db.Column(db.String(50))
    emp_id = db.Column(db.String(50))
    room_number = db.Column(db.String(50))
    lpo_number = db.Column(db.String(50))
    supplier_name = db.Column(db.String(100))
    file_path = db.Column(db.String(255))
    item = db.relationship('InventoryItem')

class MaintenanceReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    block = db.Column(db.String(50))
    section = db.Column(db.String(50))
    report_date = db.Column(db.String(50))
    details = db.Column(db.String(500))
    status = db.Column(db.String(20), default='Open')
    closed_date = db.Column(db.String(50))
    concern = db.Column(db.String(100))
    risk = db.Column(db.String(20))
    remarks = db.Column(db.String(500))
    attached_file = db.Column(db.String(255))

class AMCsService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.String(50))
    date = db.Column(db.String(50))
    description = db.Column(db.String(500))
    supplier_name = db.Column(db.String(100))
    start_date = db.Column(db.String(50))
    end_date = db.Column(db.String(50))
    cost = db.Column(db.Float)
    type = db.Column(db.String(100))
    remarks = db.Column(db.String(255))
    duration = db.Column(db.String(50))
    remaining_days = db.Column(db.Integer)
    attached_file = db.Column(db.String(255))