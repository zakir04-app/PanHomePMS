from flask import Blueprint

# Initialize Blueprints here
auth_bp = Blueprint('auth', __name__)
dashboard_bp = Blueprint('dashboard_bp', __name__)
staff_mgmt_bp = Blueprint('staff_mgmt', __name__)
inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')
maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/maintenance')
amcs_bp = Blueprint('amcs', __name__, url_prefix='/amcs')
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# Import the routes to link them to the Blueprints
from . import auth, dashboard, staff_mgmt, inventory, maintenance, amcs, settings