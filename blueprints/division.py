from imports import *
from extensions import db
from models import LoginUser
from models.our_items import OurItems, ItemRequestTable, Strength, ScmeItems
from models.org_ladder import OrgLadder
from validation import get_parent_admin,has_special_characters

div_bp = Blueprint("div",__name__,url_prefix='/division_admin')


@div_bp.route('/')
def div_home():
    if "user_id" not in session:
        return redirect('/')

    user = LoginUser.query.get(session["user_id"])
    subordinate_units = []

    # Map unit_name to strength data from Strength table
    strength_records = Strength.query.all()
    strength_map = {
        s.unit_name: {
            "unit_strength": s.unit_strength,
            "authorized_strength": s.authorized_strength
        }
        for s in strength_records
    }

    if user and user.org:
        # Recursively collect units under current division org node
        def collect_units(node):
            res = []
            for child in node.children:
                if child.type and child.type.lower() == 'unit':
                    # Only fetch from Strength table, default to 0 if not present
                    s_data = strength_map.get(child.name, {"unit_strength": 0, "authorized_strength": 0})
                    res.append({
                        "id": child.id,
                        "name": child.name,
                        "unit_strength": s_data["unit_strength"],
                        "authorized_strength": s_data["authorized_strength"]
                    })
                else:
                    res.extend(collect_units(child))
            return res

        subordinate_units = collect_units(user.org)

    # Fetch catalog items from ScmeItems (or fallback to OurItems)
    catalog_items = ScmeItems.query.order_by(ScmeItems.item_name).all()
    if not catalog_items:
        catalog_items = OurItems.query.order_by(OurItems.item_name).all()

    username = user.username if user else session.get("username", "Division")

    return render_template(
        '/Div_Dashboard/div_dashboard.html',
        username=username,
        units=subordinate_units,
        unit_count=len(subordinate_units),
        catalog_items=catalog_items,
        total_items=len(catalog_items),
        critical_alerts_count=0
    )


@div_bp.route("/update-posted-strength", methods=["POST"])
@div_bp.route("/update-strength", methods=["POST"])
def update_strength():
    try:
        data = request.get_json() or {}
        unit_name = data.get("unit_name")
        u_strength = data.get("unit_strength")
        a_strength = data.get("authorized_strength")

        if not unit_name:
            return jsonify({"success": False, "message": "Unit name is required."}), 400

        try:
            val_u = int(u_strength) if u_strength is not None else 0
            val_a = int(a_strength) if a_strength is not None else 0
            if val_u < 0 or val_a < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Strengths must be valid non-negative integers."}), 400

        record = Strength.query.filter_by(unit_name=unit_name).first()
        if record:
            record.unit_strength = val_u
            record.authorized_strength = val_a
        else:
            record = Strength(unit_name=unit_name, unit_strength=val_u, authorized_strength=val_a)
            db.session.add(record)

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Successfully updated strength data for {unit_name}.",
            "unit_name": unit_name,
            "unit_strength": val_u,
            "authorized_strength": val_a
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500




@div_bp.route('/generate-request')
def gen_req():
    items = OurItems.query.order_by(OurItems.item_name).all()
    return render_template('/Div_Dashboard/request_item.html',items=items)



