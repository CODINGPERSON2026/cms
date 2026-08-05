from datetime import datetime, timezone, timedelta
from imports import *
from extensions import db
from validation import has_special_characters
from models import LoginUser
from models.our_items import OurItems, ItemRequestTable, Units, Strength, TrackUnitItems, ArmyPersonnel, UnitTpsStock, Transactions
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

        # Query aggregated TPS stock per item for this unit
        tps_stock_map = {}
        tps_records = db.session.query(
            UnitTpsStock.item_id,
            db.func.sum(UnitTpsStock.tps_ser).label("total_ser"),
            db.func.sum(UnitTpsStock.tps_pws).label("total_pws")
        ).filter(
            db.func.lower(UnitTpsStock.unit_name).in_([name.lower() for name in unit_names])
        ).group_by(UnitTpsStock.item_id).all()

        for t in tps_records:
            tps_stock_map[t.item_id] = {
                "ser": int(t.total_ser or 0),
                "pws": int(t.total_pws or 0)
            }

        unit_item_map = {}
        for rec in records:
            iid = rec.item_id
            if iid not in unit_item_map:
                item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
                auth = rec.auth or 0
                scale_val = (rec.scale or "").strip()
                if not scale_val:
                    issued_rec = ScmeIssuedItems.query.filter(
                        db.func.lower(db.func.trim(ScmeIssuedItems.unit_name)).in_([n.lower().strip() for n in possible_names if n]),
                        ScmeIssuedItems.item_id == iid
                    ).first()
                    if issued_rec and issued_rec.scale:
                        scale_val = issued_rec.scale.strip()

                unit_item_map[iid] = {
                    "id": rec.id,
                    "item_id": iid,
                    "item_name": item_name,
                    "scale": scale_val,
                    "authorized": auth,
                    "held": 0,
                    "ser": 0,
                    "pws": 0,
                    "available_res": 0,
                    "available_ser": 0,
                    "available_pws": 0,
                    "issued_at": rec.issued_at
                }
            
            avail_ser = getattr(rec, 'available_ser', 0) or 0
            avail_pws = getattr(rec, 'available_pws', 0) or 0
            avail_res = avail_ser + avail_pws

            unit_item_map[iid]["held"] += (rec.held or 0)
            unit_item_map[iid]["ser"] += (getattr(rec, 'ser', 0) or 0)
            unit_item_map[iid]["pws"] += (getattr(rec, 'pws', 0) or 0)
            unit_item_map[iid]["available_res"] += avail_res
            unit_item_map[iid]["available_ser"] += avail_ser
            unit_item_map[iid]["available_pws"] += avail_pws

        for iid, u_rec in unit_item_map.items():
            tps_data = tps_stock_map.get(iid, {"ser": 0, "pws": 0})
            u_rec["tps_ser"] = tps_data["ser"]
            u_rec["tps_pws"] = tps_data["pws"]
            u_rec["deficiency"] = max(0, u_rec["authorized"] - (u_rec["available_ser"] + u_rec["available_pws"] + u_rec["ser"] + u_rec["pws"] + u_rec["tps_ser"] + u_rec["tps_pws"]))
            unit_records.append(u_rec)

    # Fetch Army Personnel list for unit
    personnel_list = []
    if unit_names:
        personnel_records = ArmyPersonnel.query.filter(
            db.func.lower(ArmyPersonnel.unit_name).in_([name.lower() for name in unit_names])
        ).order_by(ArmyPersonnel.id.desc()).all()
        for p in personnel_records:
            personnel_list.append({
                "id": p.id,
                "army_number": p.army_number,
                "name": p.name,
                "rank": p.rank,
                "company": p.company or "",
                "created_at": p.created_at.strftime("%d-%m-%Y") if p.created_at else ""
            })

    # Build Day-Wise Received Equipment Data for Unit Dashboard
    daily_issue_totals = {}
    daily_item_issue_map = {}

    if unit_names and records:
        for rec in records:
            item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
            held_qty = rec.held or 0
            dt = rec.issued_at
            if dt:
                dt_str = dt.strftime("%Y-%m-%d")
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

    unit_tps_chart_data = {}
    if unit_records:
        for rec in unit_records:
            item_name = rec["item_name"]
            unit_tps_chart_data[item_name] = {
                "ser": rec.get("tps_ser", 0),
                "pws": rec.get("tps_pws", 0)
            }

    # Build Company-Based TPS chart data — group UnitTpsStock by company via ArmyPersonnel
    company_tps_data = {}
    if unit_names:
        company_tps_records = db.session.query(
            ArmyPersonnel.company,
            db.func.sum(UnitTpsStock.tps_ser).label("total_ser"),
            db.func.sum(UnitTpsStock.tps_pws).label("total_pws")
        ).join(
            UnitTpsStock, UnitTpsStock.army_number == ArmyPersonnel.army_number
        ).filter(
            db.func.lower(UnitTpsStock.unit_name).in_([n.lower() for n in unit_names])
        ).group_by(ArmyPersonnel.company).all()

        for row in company_tps_records:
            coy = row.company or "Unknown"
            company_tps_data[coy] = {
                "ser": int(row.total_ser or 0),
                "pws": int(row.total_pws or 0)
            }

    # Top 5 recent issue logs for this unit
    recent_issues = []
    if unit_names:
        recent_txns = Transactions.query.filter(
            db.func.lower(Transactions.issued_by).in_([n.lower() for n in unit_names])
        ).order_by(Transactions.timestamp.desc()).limit(5).all()

        for t in recent_txns:
            item_name = t.item.item_name if t.item else f"Item #{t.item_id}"
            recent_issues.append({
                "item_name": item_name,
                "received_by": t.received_by,
                "ser": t.ser or 0,
                "pws": t.pws or 0,
                "timestamp": t.timestamp.strftime("%d %b %Y, %H:%M") if t.timestamp else "—"
            })

    return render_template(
        '/Unit_Dashboard/unit_dashboard.html',
        username=username,
        unit_records=unit_records,
        personnel_list=personnel_list,
        daily_trend_labels=daily_trend_labels,
        daily_trend_data=daily_trend_data,
        daily_item_trend_map=daily_item_trend_map,
        unit_tps_chart_data=unit_tps_chart_data,
        company_tps_data=company_tps_data,
        recent_issues=recent_issues
    )


@unit_bp.route('/add_personnel', methods=['POST'])
def add_personnel():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        user = LoginUser.query.get(session["user_id"])
        unit_name = user.username if user else session.get("username", "Unit")
        
        data = request.get_json() or {}
        army_number = (data.get("army_number") or request.form.get("army_number") or "").strip()
        name = (data.get("name") or request.form.get("name") or "").strip()
        rank = (data.get("rank") or request.form.get("rank") or "").strip()
        company = (data.get("company") or request.form.get("company") or "").strip()

        if not army_number or not name or not rank:
            return jsonify({"success": False, "message": "Army Number, Name and Rank are required."}), 400

        # Input Sanitization & Special Character Validation
        if has_special_characters(army_number) or has_special_characters(name) or has_special_characters(rank) or has_special_characters(company):
            return jsonify({"success": False, "message": "Inputs contain invalid special characters."}), 400

        existing = ArmyPersonnel.query.filter_by(army_number=army_number).first()
        if existing:
            return jsonify({"success": False, "message": f"Personnel with Army Number '{army_number}' already exists."}), 400

        new_personnel = ArmyPersonnel(
            army_number=army_number,
            name=name,
            rank=rank,
            company=company,
            unit_name=unit_name
        )
        db.session.add(new_personnel)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Personnel added successfully!",
            "personnel": {
                "id": new_personnel.id,
                "army_number": new_personnel.army_number,
                "name": new_personnel.name,
                "rank": new_personnel.rank,
                "company": new_personnel.company or ""
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to add personnel."}), 500


@unit_bp.route('/delete_personnel/<int:personnel_id>', methods=['POST'])
def delete_personnel(personnel_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        user = LoginUser.query.get(session["user_id"])
        unit_name = user.username if user else session.get("username", "Unit")

        personnel = ArmyPersonnel.query.get(personnel_id)
        if not personnel:
            return jsonify({"success": False, "message": "Personnel not found."}), 404

        # IDOR Protection: Verify personnel belongs to logged in unit
        if personnel.unit_name and personnel.unit_name.lower().strip() != unit_name.lower().strip():
            return jsonify({"success": False, "message": "Unauthorized: Cannot delete personnel from another unit."}), 403

        db.session.delete(personnel)
        db.session.commit()
        return jsonify({"success": True, "message": "Personnel deleted."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to delete personnel."}), 500


@unit_bp.route('/api/update-auth', methods=['POST'])
def api_update_auth():
    try:
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Not authenticated."}), 401

        user = LoginUser.query.get(session["user_id"])
        unit_name = user.username if user else session.get("username", "Unit")

        data = request.get_json() or {}
        rec_id = data.get("rec_id")
        new_auth = data.get("authorized_strength")

        if rec_id is None or new_auth is None:
            return jsonify({"success": False, "message": "Record ID and authorized value are required."}), 400

        try:
            rec_id = int(rec_id)
            new_auth = int(new_auth)
            if new_auth < 0 or new_auth > 100000:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Authorized value must be a valid non-negative integer."}), 400

        rec = TrackUnitItems.query.get(rec_id)
        if not rec:
            return jsonify({"success": False, "message": "Record not found."}), 404

        # IDOR Protection: Verify record belongs to logged in unit
        if rec.unit_name and rec.unit_name.lower().strip() != unit_name.lower().strip():
            return jsonify({"success": False, "message": "Unauthorized access: Record does not belong to your unit."}), 403

        rec.auth = new_auth
        db.session.commit()

        return jsonify({"success": True, "message": f"AUTH updated to {new_auth} successfully.", "authorized_strength": new_auth}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to update AUTH value."}), 500


@unit_bp.route("/api/submit-request", methods=["POST"])
def api_request_item():
    try:
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        current_user = session['user_id']
        data = request.get_json() or {}

        item_id = data.get("item_id")
        quantity = data.get("quantity")
        reason = (data.get("reason") or "").strip()
        priority = (data.get("priority") or "").strip()
        remarks = (data.get("remarks") or "").strip()

        # Special character validation
        if has_special_characters(reason) or has_special_characters(priority) or has_special_characters(remarks):
            return jsonify({
                "success": False,
                "message": "Form inputs contain invalid special characters."
            }), 400

        if not item_id:
            return jsonify({
                "success": False,
                "message": "Please select an item."
            }), 400

        try:
            quantity = int(quantity)
            if quantity <= 0 or quantity > 100000:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Requested quantity must be a positive integer."
            }), 400

        user_id = session["user_id"]
        user_rec = LoginUser.query.get(user_id)
        org_id = user_rec.org_id if user_rec else None
        admin_id = get_admin_from_org_ladder(org_id) if org_id else None

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
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to submit request."
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

        # ---------------- INSERT INTO UNITS TABLE ONLY IF ROLE IS DIVISION_ADMIN ----------------
        if role == "division_admin":
            existing_unit_rec = Units.query.filter_by(name=username).first()
            if not existing_unit_rec:
                new_unit_rec = Units(
                    name=username,
                    authorized_strength=0,
                    posted_strength=0
                )
                db.session.add(new_unit_rec)

        # ---------------- INSERT INTO UNIT_STRENGTH TABLE ONLY IF ROLE IS UNIT ----------------
        if role == "unit":
            existing_strength_rec = Strength.query.filter_by(unit_name=username).first()
            if not existing_strength_rec:
                new_strength_rec = Strength(
                    unit_name=username,
                    posted_strength=0,
                    authorized_strength=0
                )
                db.session.add(new_strength_rec)

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


@unit_bp.route('/search_personnel', methods=['GET'])
def search_personnel():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    user = LoginUser.query.get(session["user_id"])
    username = user.username if user else session.get("username", "Unit")
    
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"success": True, "results": []})

    if has_special_characters(query):
        return jsonify({"success": False, "message": "Search query contains invalid special characters."}), 400

    search_pattern = f"%{query.lower()}%"
    results = ArmyPersonnel.query.filter(
        db.func.lower(ArmyPersonnel.unit_name) == username.lower(),
        db.or_(
            db.func.lower(ArmyPersonnel.name).like(search_pattern),
            db.func.lower(ArmyPersonnel.army_number).like(search_pattern),
            db.func.lower(ArmyPersonnel.rank).like(search_pattern)
        )
    ).limit(10).all()

    items = []
    for p in results:
        items.append({
            "id": p.id,
            "army_number": p.army_number,
            "name": p.name,
            "rank": p.rank,
            "company": p.company or ""
        })

    return jsonify({"success": True, "results": items})


@unit_bp.route('/issue_to_personnel', methods=['POST'])
def issue_to_personnel():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        user = LoginUser.query.get(session["user_id"])
        unit_name = user.username if user else session.get("username", "Unit")
        
        data = request.get_json() or {}
        rec_id = data.get("rec_id")
        army_number = (data.get("army_number") or "").strip()
        name = (data.get("name") or "").strip()
        rank = (data.get("rank") or "").strip()
        company = (data.get("company") or "").strip()
        
        try:
            ser_qty = int(data.get("ser_qty") or 0)
            pws_qty = int(data.get("pws_qty") or 0)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Quantity values must be valid integers."}), 400

        remarks = (data.get("remarks") or "").strip()

        if not rec_id or not army_number:
            return jsonify({"success": False, "message": "Item record and Army Number are required."}), 400

        # 1. Input Sanitization & Special Character Check (Prevent XSS & Script Injection)
        if has_special_characters(army_number) or has_special_characters(name) or has_special_characters(rank) or has_special_characters(company):
            return jsonify({"success": False, "message": "Inputs contain invalid special characters."}), 400

        # 2. Strict Integer Boundary & Negative Value Prevention
        if ser_qty < 0 or pws_qty < 0:
            return jsonify({"success": False, "message": "Issued quantities cannot be negative."}), 400

        if ser_qty == 0 and pws_qty == 0:
            return jsonify({"success": False, "message": "Specify at least 1 SER or PWS quantity to issue."}), 400

        # 3. IDOR / Authorization Check: Verify TrackUnitItems belongs to user's unit
        unit_item = TrackUnitItems.query.get(rec_id)
        if not unit_item:
            return jsonify({"success": False, "message": "Item record not found."}), 404

        if unit_item.unit_name and unit_item.unit_name.lower().strip() != unit_name.lower().strip():
            return jsonify({"success": False, "message": "Unauthorized access: Item does not belong to your unit."}), 403

        # Find or create ArmyPersonnel record
        personnel = ArmyPersonnel.query.filter_by(army_number=army_number).first()
        if not personnel:
            if not name or not rank:
                return jsonify({"success": False, "message": "Rank and Personnel Name are required for new Army Number."}), 400
            personnel = ArmyPersonnel(
                army_number=army_number,
                name=name,
                rank=rank,
                company=company or None,
                unit_name=unit_name
            )
            db.session.add(personnel)
            db.session.flush()
        else:
            if name: personnel.name = name
            if rank: personnel.rank = rank
            if company: personnel.company = company
            if not personnel.unit_name: personnel.unit_name = unit_name

        # Fetch ALL entries for this unit & item to calculate cumulative available stock
        all_unit_items = TrackUnitItems.query.filter(
            db.func.lower(db.func.trim(TrackUnitItems.unit_name)) == (unit_item.unit_name or '').lower().strip(),
            TrackUnitItems.item_id == unit_item.item_id
        ).order_by(TrackUnitItems.issued_at.desc(), TrackUnitItems.id.desc()).all()

        current_res_ser = sum((getattr(r, 'available_ser', 0) or 0) for r in all_unit_items)
        current_res_pws = sum((getattr(r, 'available_pws', 0) or 0) for r in all_unit_items)
        current_held_ser = sum((getattr(r, 'ser', 0) or 0) for r in all_unit_items)
        current_held_pws = sum((getattr(r, 'pws', 0) or 0) for r in all_unit_items)

        # Total available for issue
        total_ser_avail = current_res_ser + current_held_ser
        total_pws_avail = current_res_pws + current_held_pws

        if ser_qty > total_ser_avail:
            return jsonify({"success": False, "message": f"Cannot issue {ser_qty} SER. Available SER stock is {total_ser_avail}."}), 400

        if pws_qty > total_pws_avail:
            return jsonify({"success": False, "message": f"Cannot issue {pws_qty} PWS. Available PWS stock is {total_pws_avail}."}), 400

        # Deduct from TrackUnitItems (res first, then held) across all records
        rem_ser = ser_qty
        for r in all_unit_items:
            r_avail_ser = getattr(r, 'available_ser', 0) or 0
            if rem_ser > 0 and r_avail_ser > 0:
                ded = min(r_avail_ser, rem_ser)
                r.available_ser = r_avail_ser - ded
                rem_ser -= ded
            r_held_ser = getattr(r, 'ser', 0) or 0
            if rem_ser > 0 and r_held_ser > 0:
                ded = min(r_held_ser, rem_ser)
                r.ser = r_held_ser - ded
                rem_ser -= ded
            if rem_ser <= 0:
                break

        rem_pws = pws_qty
        for r in all_unit_items:
            r_avail_pws = getattr(r, 'available_pws', 0) or 0
            if rem_pws > 0 and r_avail_pws > 0:
                ded = min(r_avail_pws, rem_pws)
                r.available_pws = r_avail_pws - ded
                rem_pws -= ded
            r_held_pws = getattr(r, 'pws', 0) or 0
            if rem_pws > 0 and r_held_pws > 0:
                ded = min(r_held_pws, rem_pws)
                r.pws = r_held_pws - ded
                rem_pws -= ded
            if rem_pws <= 0:
                break

        # Update or create UnitTpsStock record
        tps_rec = UnitTpsStock.query.filter_by(
            unit_name=unit_item.unit_name,
            item_id=unit_item.item_id,
            army_number=army_number
        ).first()

        if not tps_rec:
            tps_rec = UnitTpsStock(
                unit_name=unit_item.unit_name,
                item_id=unit_item.item_id,
                army_number=army_number,
                tps_ser=ser_qty,
                tps_pws=pws_qty
            )
            db.session.add(tps_rec)
        else:
            tps_rec.tps_ser = (tps_rec.tps_ser or 0) + ser_qty
            tps_rec.tps_pws = (tps_rec.tps_pws or 0) + pws_qty

        # Log transaction with received_by strictly set to army_number for clean querying
        personnel_desc = f"{personnel.army_number} ({personnel.rank} {personnel.name})"
        trans = Transactions(
            issued_by=unit_name,
            received_by=personnel.army_number,
            item_id=unit_item.item_id,
            ser=ser_qty,
            pws=pws_qty,
            remarks=remarks or f"Issued to {personnel_desc}"
        )
        db.session.add(trans)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Successfully issued {ser_qty} SER / {pws_qty} PWS to {personnel_desc}!",
            "tps_ser": tps_rec.tps_ser,
            "tps_pws": tps_rec.tps_pws
        }), 200

    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({"success": False, "message": str(e)}), 500


@unit_bp.route('/history_ledger', methods=['GET'])
def history_ledger():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
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

        unit_names_list = [name.lower() for name in unit_names] if unit_names else [username.lower()]

        # 1. Fetch Army Personnel in this unit
        personnel_records = ArmyPersonnel.query.filter(
            db.func.lower(ArmyPersonnel.unit_name).in_(unit_names_list)
        ).order_by(ArmyPersonnel.name.asc()).all()

        personnel_map = {}
        for p in personnel_records:
            personnel_map[p.army_number] = {
                "id": p.id,
                "army_number": p.army_number,
                "name": p.name,
                "rank": p.rank,
                "company": p.company or "N/A",
                "items": [],
                "total_ser": 0,
                "total_pws": 0,
                "total_held": 0
            }

        # 2. Query UnitTpsStock records for this unit
        tps_records = UnitTpsStock.query.filter(
            db.func.lower(UnitTpsStock.unit_name).in_(unit_names_list)
        ).all()

        total_ser_issued = 0
        total_pws_issued = 0

        for rec in tps_records:
            ser = rec.tps_ser or 0
            pws = rec.tps_pws or 0
            total = ser + pws
            if total <= 0:
                continue

            total_ser_issued += ser
            total_pws_issued += pws

            item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
            item_cat = getattr(rec.item, 'category', 'N/A') if rec.item else 'N/A'
            item_au = getattr(rec.item, 'a_u', 'Nos') if rec.item else 'Nos'

            army_num = rec.army_number
            if army_num in personnel_map:
                personnel_map[army_num]["items"].append({
                    "item_id": rec.item_id,
                    "item_name": item_name,
                    "category": item_cat,
                    "a_u": item_au,
                    "tps_ser": ser,
                    "tps_pws": pws,
                    "total_held": total
                })
                personnel_map[army_num]["total_ser"] += ser
                personnel_map[army_num]["total_pws"] += pws
                personnel_map[army_num]["total_held"] += total
            else:
                p_rec = ArmyPersonnel.query.filter_by(army_number=army_num).first()
                p_name = p_rec.name if p_rec else army_num
                p_rank = p_rec.rank if p_rec else ""
                p_coy = p_rec.company if p_rec else "N/A"
                personnel_map[army_num] = {
                    "id": p_rec.id if p_rec else 0,
                    "army_number": army_num,
                    "name": p_name,
                    "rank": p_rank,
                    "company": p_coy or "N/A",
                    "items": [{
                        "item_id": rec.item_id,
                        "item_name": item_name,
                        "category": item_cat,
                        "a_u": item_au,
                        "tps_ser": ser,
                        "tps_pws": pws,
                        "total_held": total
                    }],
                    "total_ser": ser,
                    "total_pws": pws,
                    "total_held": total
                }

        personnel_holdings = list(personnel_map.values())
        companies = sorted(list(set(p["company"] for p in personnel_holdings if p["company"] and p["company"] != "N/A")))

        # 3. Query Transactions for history log
        txns = Transactions.query.filter(
            db.func.lower(Transactions.issued_by).in_(unit_names_list)
        ).order_by(Transactions.timestamp.desc()).limit(100).all()

        transaction_logs = []
        for t in txns:
            item_name = t.item.item_name if t.item else f"Item #{t.item_id}"
            received_personnel = personnel_map.get(t.received_by)
            rec_display = f"{received_personnel['rank']} {received_personnel['name']} ({t.received_by})" if received_personnel and received_personnel.get('name') != t.received_by else t.received_by

            transaction_logs.append({
                "id": t.id,
                "item_name": item_name,
                "received_by": rec_display,
                "army_number": t.received_by,
                "ser": t.ser or 0,
                "pws": t.pws or 0,
                "remarks": t.remarks or "",
                "timestamp": t.timestamp.strftime("%d %b %Y, %H:%M") if t.timestamp else "—"
            })

        soldiers_with_items = sum(1 for p in personnel_holdings if p["total_held"] > 0)

        return jsonify({
            "success": True,
            "unit_name": username,
            "personnel_holdings": personnel_holdings,
            "transactions": transaction_logs,
            "companies": companies,
            "summary": {
                "total_personnel": len(personnel_holdings),
                "total_personnel_with_items": soldiers_with_items,
                "total_ser_issued": total_ser_issued,
                "total_pws_issued": total_pws_issued,
                "total_items_issued": total_ser_issued + total_pws_issued
            }
        }), 200

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": str(e)}), 500


@unit_bp.route('/unit_logs', methods=['GET'])
def get_unit_logs():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
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

        unit_names_list = [name.lower() for name in unit_names] if unit_names else [username.lower()]

        # Query all personnel in unit to construct personnel lookup dict
        personnel_records = ArmyPersonnel.query.filter(
            db.func.lower(ArmyPersonnel.unit_name).in_(unit_names_list)
        ).all()
        personnel_map = {p.army_number: p for p in personnel_records}

        # Query Transactions
        txns = Transactions.query.filter(
            db.func.lower(Transactions.issued_by).in_(unit_names_list)
        ).order_by(Transactions.timestamp.desc()).all()

        logs = []
        for t in txns:
            item_name = t.item.item_name if t.item else f"Item #{t.item_id}"
            p_rec = personnel_map.get(t.received_by) or ArmyPersonnel.query.filter_by(army_number=t.received_by).first()
            if p_rec:
                rec_display = f"{p_rec.rank} {p_rec.name} ({p_rec.army_number})"
                company = p_rec.company or "N/A"
            else:
                rec_display = t.received_by
                company = "N/A"

            ser = t.ser or 0
            pws = t.pws or 0
            logs.append({
                "id": t.id,
                "timestamp": t.timestamp.strftime("%d %b %Y, %H:%M:%S") if t.timestamp else "—",
                "issued_by": t.issued_by,
                "received_by": rec_display,
                "army_number": t.received_by,
                "company": company,
                "item_name": item_name,
                "ser": ser,
                "pws": pws,
                "total": ser + pws,
                "remarks": t.remarks or "—"
            })

        return jsonify({
            "success": True,
            "unit_name": username,
            "total_logs": len(logs),
            "logs": logs
        }), 200

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": str(e)}), 500
