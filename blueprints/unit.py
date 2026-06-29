from imports import *
from extensions import db
from models import LoginUser
from models.our_items import OurItems
from models.our_items import ItemRequestTable
from models.org_ladder import OrgLadder


unit_bp = Blueprint("unit",__name__,url_prefix='/unit')


@unit_bp.route('/')
def unit_dashboard():
        if "user_id" not in session:
            return "Unauthorized - Please login first", 401
        
        return render_template('/Unit_Dashboard/unit_dashboard.html')




@unit_bp.route("/request-item")
def request_item():
    if "user_id" not in session:
            return "Unauthorized - Please login first", 401

    items = OurItems.query.order_by(OurItems.item_name).all()

    return render_template(
        "/Unit_Dashboard/request_item.html",
        items=items
    )


@unit_bp.route("/api/submit-request", methods=["POST"])
def api_request_item():
    try:
        current_user = session['user_id']
        data = request.get_json()
        print(data)
        
        item_id = data.get("item_id")
        quantity = data.get("quantity")
        reason = data.get("reason")
        priority = data.get("priority")
        remarks = data.get("remarks")

        # Validation
        if not item_id:
            return jsonify({
                "success": False,
                "message": "Please select an item."
            }), 400

        if not quantity or int(quantity) <= 0:
            return jsonify({
                "success": False,
                "message": "Invalid quantity."
            }), 400
        user_id = (session["user_id"])
        org_id = LoginUser.query.get(user_id).org_id
        admin_id = get_admin_from_org_ladder(org_id)
        print(admin_id)
        
        new_request = ItemRequestTable(
            item_id=item_id,
            requested_by=current_user,
            admin_id=admin_id,
            quantity=quantity,
            reason=reason,
            priority=priority,
            remarks=remarks
        )
        

        db.session.add(new_request)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Request submitted successfully."
        }), 201

    except Exception as e:
        print(e)
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
def get_admin_from_org_ladder(org_id):
    current_org = OrgLadder.query.get(org_id)
    print(current_org.name,"this is current login org")

    while current_org:
        admin = LoginUser.query.filter(
            LoginUser.org_id == current_org.id,
            LoginUser.role.in_(["brigade_admin", "division_admin"])
        ).first()

        if admin:
            print('got the')
            return admin.id

        current_org = OrgLadder.query.get(current_org.parent_id)

    return None
