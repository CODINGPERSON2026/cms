from imports import *
from models import LoginUser


unit_bp = Blueprint("unit",__name__,url_prefix='/unit')


@unit_bp.route('/')
def unit_dashboard():
        if "user_id" not in session:
            return "Unauthorized - Please login first", 401
        
        return render_template('/Unit_Dashboard/unit_dashboard.html')