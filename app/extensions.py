"""Shared Flask extension instances.

Kept separate from the application factory so they can be imported by
blueprints, services and tests without circular imports.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address, default_limits=[])