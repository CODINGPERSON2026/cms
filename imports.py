from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    Blueprint
)


from config import Config
from blueprints.login import login_bp
from blueprints.unit import unit_bp
from blueprints.division import div_bp
from blueprints.ord import ord_bp
from blueprints.brigade import bde_bp
from blueprints.management import mgt_bp

from extensions import db
from flask_wtf.csrf import CSRFError
from flask_migrate import Migrate
from models import LoginUser, OrgLadder


