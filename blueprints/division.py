from imports import *
from extensions import db
from models import LoginUser
from models.our_items import OurItems
from models.our_items import ItemRequestTable
from models.org_ladder import OrgLadder


div_bp = Blueprint("div",__name__,url_prefix='/division_admin')


@div_bp.route('/')
def div_home():
    return render_template('/Div_Dashboard/div_dashboard.html')