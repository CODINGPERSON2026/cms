from datetime import datetime, timezone, timedelta
from imports import *
from extensions import db
from validation import has_special_characters
from models import LoginUser
from models.our_items import OurItems, ItemRequestTable, Units, Strength, TrackUnitItems
from models.org_ladder import OrgLadder


unit_bp = Blueprint("unit",__name__,url_prefix='/unit')

@unit_bp.route('/')
def unit_dashboard():
    if "user_id" not in session:
        return redirect('/')

    user = LoginUser.query.get(session["user_id"])
    username = user.username if user else session.get("username", "Unit")

    unit_names = set()
    if user:
        if user.username:
            unit_names.add(user.username.strip())
            unit_names.add(user.username.replace('_', ' ').strip())
            unit_names.add(user.username.replace(' ', '_').strip())
        if user.org and user.org.name:
            unit_names.add(user.org.name.strip())
            unit_names.add(user.org.name.replace('_', ' ').strip())
            unit_names.add(user.org.name.replace(' ', '_').strip())

    unit_records = []
    records = []
    if unit_names:
        records = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_([name.lower() for name in unit_names])
        ).all()

        for rec in records:
            item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
            auth = rec.auth or 0
            held_qty = rec.held or 0
            ser_qty = getattr(rec, 'ser', 0) or 0
            pws_qty = getattr(rec, 'pws', 0) or 0
            defi = max(0, auth - held_qty)
            unit_records.append({
                "id": rec.id,
                "item_id": rec.item_id,
                "item_name": item_name,
                "authorized": auth,
                "held": held_qty,
                "ser": ser_qty,
                "pws": pws_qty,
                "deficiency": defi,
                "issued_at": rec.issued_at
            })

    # Build Day-Wise Received Equipment Data for Unit Dashboard
    daily_issue_totals = {}
    daily_item_issue_map = {}

    if unit_names and records:
        for rec in records:
            if rec.issued_at and (rec.held or 0) > 0:
                dt_str = rec.issued_at.strftime("%Y-%m-%d")
                item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
                held_qty = rec.held or 0

                daily_issue_totals[dt_str] = daily_issue_totals.get(dt_str, 0) + held_qty

                if item_name not in daily_item_issue_map:
                    daily_item_issue_map[item_name] = {}
                daily_item_issue_map[item_name][dt_str] = daily_item_issue_map[item_name].get(dt_str, 0) + held_qty

    sorted_dates = sorted(daily_issue_totals.keys())

    if not sorted_dates:
        today = datetime.now()
        sorted_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    daily_trend_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%d %b") for d in sorted_dates]
    daily_trend_data = [daily_issue_totals.get(d, 0) for d in sorted_dates]

    daily_item_trend_map = {}
    for item_name, d_map in daily_item_issue_map.items():
        daily_item_trend_map[item_name] = [d_map.get(d, 0) for d in sorted_dates]

    return render_template(
        '/Unit_Dashboard/unit_dashboard.html',
        username=username,
        unit_records=unit_records,
        daily_trend_labels=daily_trend_labels,
        daily_trend_data=daily_trend_data,
        daily_item_trend_map=daily_item_trend_map
    )


@unit_bp.route('/api/update-auth', methods=['POST'])
def api_update_auth():
    try:
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Not authenticated."}), 401

        data = request.get_json() or {}
        rec_id = data.get("rec_id")
        new_auth = data.get("authorized_strength")

        if rec_id is None or new_auth is None:
            return jsonify({"success": False, "message": "Record ID and authorized value are required."}), 400

        try:
            rec_id = int(rec_id)
            new_auth = int(new_auth)
            if new_auth < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Authorized value must be a non-negative integer."}), 400

        rec = TrackUnitItems.query.get(rec_id)
        if not rec:
            return jsonify({"success": False, "message": "Record not found."}), 404

        rec.auth = new_auth
        db.session.commit()

        return jsonify({"success": True, "message": f"AUTH updated to {new_auth} successfully.", "authorized_strength": new_auth}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


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
        admin_id = get_admin_from_org_ladder(org_id)

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

@unit_bp.route("/request-item")
def request_item():
    if "user_id" not in session:
            return "Unauthorized - Please login first", 401

    items = OurItems.query.order_by(OurItems.item_name).all()

    return render_template(
        "/Unit_Dashboard/request_item.html",
        items=items
    )


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



# THIS BELOW FUNCTIONALITY IS ONLY FOR ADD UNIT AND MANAGING DATA BY SUPER_ADMIN (ORD)
@unit_bp.route("/org")
def manage_org():
    if "user_id" not in session or session.get("role") != "super_admin":
        return redirect("/")

    orgs = OrgLadder.query.order_by(
        OrgLadder.name
    ).all()

    return render_template(
        "create_user/create_user.html",
        orgs=orgs
    )
@unit_bp.route("/api/create-org", methods=["POST"])
def create_org():

    try:
        data = request.get_json()

        name = data.get("name")
        org_type = data.get("type")
        parent_id = data.get("parent_id")

        if not name:
            return jsonify({
                "success": False,
                "message": "Organization name required"
            }), 400

        new_org = OrgLadder(
            name=name,
            type=org_type,
            parent_id=parent_id if parent_id else None
        )

        db.session.add(new_org)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Organization created successfully"
        })

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
@unit_bp.route("/api/create-user", methods=["POST"])
def create_user():
    try:
        # ---------------- SESSION USER CHECK ----------------
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Unauthorized."}), 401

        current_user = LoginUser.query.get(session["user_id"])

        if not current_user or current_user.role != "super_admin":
            return jsonify({"success": False, "message": "Only ORD (super_admin) is authorized to create users."}), 403

        data = request.get_json() or {}

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        role = data.get("role", "").strip()
        parent_id = data.get("parent_id")

        # ---------------- VALIDATION ----------------
        if not username:
            return jsonify({"success": False, "message": "Username is required."}), 400

        if not password:
            return jsonify({"success": False, "message": "Password is required."}), 400

        if not role:
            return jsonify({"success": False, "message": "Role is required."}), 400

        # ---------------- CHECK USER EXISTS ----------------
        existing_user = LoginUser.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({"success": False, "message": "Username already exists."}), 400

        # ---------------- ROLE → ORG TYPE MAP ----------------
        org_type_map = {
            "division_admin": "division",
            "brigade_admin": "brigade",
            "unit": "unit"
        }

        if role not in org_type_map:
            return jsonify({"success": False, "message": "Invalid role type."}), 400

        org_type = org_type_map[role]

        target_parent_id = parent_id if parent_id else current_user.org_id

        # ---------------- VALIDATION: UNIT CAN ONLY HAVE DIVISION OR ORD AS PARENT ----------------
        if role == "unit" and parent_id:
            parent_org = OrgLadder.query.get(parent_id)
            if parent_org:
                parent_type = (parent_org.type or "").lower()
                if parent_type not in ["division", "ord", "super_admin", "root"]:
                    return jsonify({
                        "success": False,
                        "message": f"When role 'unit' is selected, parent organization must be Division or ORD (selected parent '{parent_org.name}' is {parent_org.type})."
                    }), 400

        # ---------------- CREATE ORG ----------------
        new_org = OrgLadder(
            name=username,
            type=org_type,
            parent_id=target_parent_id
        )

        db.session.add(new_org)
        db.session.flush()   # gets new_org.id before commit

        # ---------------- CREATE USER ----------------
        new_user = LoginUser(
            username=username,
            password=password,
            role=role,
            org_id=new_org.id
        )

        db.session.add(new_user)

        # ---------------- INSERT INTO UNITS TABLE IF ROLE IS UNIT ----------------
        if role == "unit":
            existing_unit_rec = Units.query.filter_by(name=username).first()
            if not existing_unit_rec:
                new_unit_rec = Units(
                    name=username,
                    authorized_strength=0,
                    posted_strength=0
                )
                db.session.add(new_unit_rec)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"{role} user and organization created successfully."
        }), 201

    except Exception as e:
        db.session.rollback()
        print(e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500