from flask import Blueprint

# 1. Create the Blueprint
admin_bp = Blueprint('admin', __name__)

# 2. Import routes from other files to register them
# (Must be at the bottom to avoid circular import errors)
from . import dashboard, vendors, users, system