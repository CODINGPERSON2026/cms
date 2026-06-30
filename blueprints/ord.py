from imports import *
from extensions import db
from models import LoginUser
from models.our_items import OurItems
from models.our_items import ItemRequestTable
from models.org_ladder import OrgLadder


ord_bp = Blueprint("ord",__name__,url_prefix='/super_admin')


@ord_bp.route('/')
def ord_home():
    return render_template('/ord_dashboard/ord.html')