from imports import *
from extensions import db
from models import LoginUser
from models.our_items import OurItems, ItemRequestTable, Units
from models.org_ladder import OrgLadder


ord_bp = Blueprint("ord",__name__,url_prefix='/super_admin')


@ord_bp.route('/')
def ord_home():
    if "user_id" not in session:
        return redirect('/')

    user = LoginUser.query.get(session["user_id"])
    username = user.username if user else session.get("username", "ORD")

    # Fetch all records from units table
    db_units = Units.query.order_by(Units.id).all()

    return render_template(
        '/ord_dashboard/ord.html',
        username=username,
        units=db_units,
        div_count=len(db_units)
    )


@ord_bp.route("/update-units-strength", methods=["POST"])
def update_units_strength():
    try:
        data = request.get_json() or {}
        unit_id = data.get("unit_id")
        auth_strength = data.get("authorized_strength")
        posted_strength = data.get("posted_strength")

        if not unit_id:
            return jsonify({"success": False, "message": "Unit ID is required."}), 400

        try:
            val_a = int(auth_strength) if auth_strength is not None else 0
            val_p = int(posted_strength) if posted_strength is not None else 0
            if val_a < 0 or val_p < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Strengths must be valid non-negative integers."}), 400

        unit_rec = Units.query.get(unit_id)
        if not unit_rec:
            return jsonify({"success": False, "message": "Unit record not found."}), 404

        unit_rec.authorized_strength = val_a
        unit_rec.posted_strength = val_p

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Successfully updated strength data for {unit_rec.name}.",
            "unit_id": unit_rec.id,
            "unit_name": unit_rec.name,
            "authorized_strength": val_a,
            "posted_strength": val_p
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500