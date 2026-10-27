from imports import *
from extensions import db
from models import LoginUser
from models.our_items import OurItems
from models.our_items import ItemRequestTable
from models.org_ladder import OrgLadder
from validation import get_parent_admin,has_special_characters

bde_bp = Blueprint("bde",__name__,url_prefix='/brigade_admin')


@bde_bp.route('/')
def bde_home():
    return render_template('/Brigade_Dashboard/bde_dashboard.html')


@bde_bp.route('/generate-request')
def gen_req():
    items = OurItems.query.order_by(OurItems.item_name).all()
    return render_template('/Brigade_dashboard/request_item.html',items=items)

@bde_bp.route("/submit-request", methods=["POST"])
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

        # Special character validation
        if has_special_characters(reason):
            return jsonify({
                "success": False,
                "message": "Reason contains invalid characters."
            }), 400

        if has_special_characters(priority):
            return jsonify({
                "success": False,
                "message": "Priority contains invalid characters."
            }), 400

        if has_special_characters(remarks):
            return jsonify({
                "success": False,
                "message": "Remarks contains invalid characters."
            }), 400

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

        user_id = session["user_id"]
        org_id = LoginUser.query.get(user_id).org_id
        print(user_id)
        admin_id = get_parent_admin(org_id)
        print(org_id)
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
        }), 200

    except Exception as e:
        print(e)
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@bde_bp.route("/notification-count")
def notification_count():
    current_user = session["org_id"]
    print(current_user)


    count = ItemRequestTable.query.filter_by(
        admin_id=current_user
    ).count()

    return jsonify({
        "count": count
    })