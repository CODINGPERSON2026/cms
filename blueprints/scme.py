from imports import *
from extensions import db
from models import LoginUser, ActionLog
from models.our_items import OurItems, ItemRequestTable, ScmeItems, Units, ScmeIssuedItems, EccMonthlyState
from models.org_ladder import OrgLadder
from validation import has_special_characters

scme_bp = Blueprint("scme", __name__, url_prefix='/scme')


@scme_bp.route('/')
def scme_home():
    if "user_id" not in session or session.get("role") != "scme":
        return redirect("/auth/login")

    from sqlalchemy import func

    # 1. Total Catalog Items
    total_items = ScmeItems.query.filter(ScmeItems.type == 'scme').count()

    # 2. Active Units Tracked
    active_units = db.session.query(ScmeIssuedItems.unit_name).distinct().count()

    # 3. Global Deficiency (Deafy)
    global_deficiency = db.session.query(func.sum(ScmeIssuedItems.deficiency)).scalar() or 0

    # 4. Fulfillment Rate — authorised total now comes from unit_authorized (a_u is a string)
    total_au = db.session.query(func.sum(ScmeIssuedItems.unit_authorized)).scalar() or 0
    total_held = db.session.query(func.sum(ScmeIssuedItems.held)).scalar() or 0
    # cast to float: SUM() returns Decimal, which can't divide a float directly
    total_au = float(total_au)
    total_held = float(total_held)
    fulfillment_rate = round((total_held / total_au * 100), 1) if total_au > 0 else 0

    # 5. Critical Alerts Count (held < 50% of authorised)
    critical_alerts = ScmeIssuedItems.query.filter(
        ScmeIssuedItems.held < (ScmeIssuedItems.unit_authorized / 2)
    ).count()

    # Chart 1: Unit x Item breakdown (authorised / held / deficiency)
    # Kept granular (unit, item, category) instead of unit-only, so the dashboard
    # can filter the chart by unit, item, and/or category on the client side.
    # NOTE: scale is now a percentage string ("50%") and can't be summed — removed from this aggregate.
    unit_stats = db.session.query(
        ScmeIssuedItems.unit_name,
        ScmeItems.item_name,
        ScmeItems.category,
        func.sum(ScmeIssuedItems.unit_authorized).label('unit_authorized'),
        func.sum(ScmeIssuedItems.held).label('held'),
        func.sum(ScmeIssuedItems.deficiency).label('deficiency')
    ).join(ScmeItems, ScmeItems.id == ScmeIssuedItems.item_id)\
     .group_by(ScmeIssuedItems.unit_name, ScmeItems.item_name, ScmeItems.category)\
     .all()

    unit_chart_data = [
        {
            "unit_name": row[0],
            "item_name": row[1],
            "category": row[2],
            "a_u": int(row[3] or 0),          # authorised total (kept key 'a_u' for the chart template)
            "held": int(row[4] or 0),
            "deficiency": int(row[5] or 0)
        } for row in unit_stats
    ]

    # Chart 2: Top 5 Items with Highest Deficiency
    top_deficient = db.session.query(
        ScmeItems.item_name,
        func.sum(ScmeIssuedItems.deficiency).label('total_def')
    ).join(ScmeIssuedItems, ScmeItems.id == ScmeIssuedItems.item_id)\
     .group_by(ScmeItems.item_name)\
     .order_by(func.sum(ScmeIssuedItems.deficiency).desc())\
     .limit(5).all()

    item_chart_data = [
        {
            "item_name": row[0],
            "deficiency": int(row[1] or 0)
        } for row in top_deficient
    ]

    # Chart 3: Fulfillment vs Deficiency breakdown
    overall_chart_data = {
        "held": int(total_held),
        "deficiency": int(global_deficiency)
    }

    # Chart 4: Deficiency Share by Unit
    unit_def_stats = db.session.query(
        ScmeIssuedItems.unit_name,
        func.sum(ScmeIssuedItems.deficiency).label('total_def')
    ).group_by(ScmeIssuedItems.unit_name).all()

    unit_deficiency_share_data = [
        {
            "unit_name": row[0].replace('_', ' ').upper(),
            "deficiency": int(row[1] or 0)
        } for row in unit_def_stats if (row[1] or 0) > 0
    ]

    # Chart 5: Accounting Unit (A/U) Quantity Split
    au_split_stats = db.session.query(
        ScmeIssuedItems.a_u,
        func.sum(ScmeIssuedItems.held).label('total_held')
    ).group_by(ScmeIssuedItems.a_u).all()

    au_split_data = [
        {
            "a_u": row[0],
            "held": int(row[1] or 0)
        } for row in au_split_stats if row[0]
    ]

    # Chart 6: Supply Readiness (Fulfillment Rate) by Unit
    unit_readiness_stats = db.session.query(
        ScmeIssuedItems.unit_name,
        func.sum(ScmeIssuedItems.unit_authorized).label('total_auth'),
        func.sum(ScmeIssuedItems.held).label('total_held')
    ).group_by(ScmeIssuedItems.unit_name).all()

    unit_readiness_data = [
        {
            "unit_name": row[0].replace('_', ' ').upper(),
            "rate": round((float(row[2] or 0) / float(row[1]) * 100), 1) if (row[1] or 0) > 0 else 0
        } for row in unit_readiness_stats
    ]

    issued_items = ScmeIssuedItems.query.order_by(ScmeIssuedItems.created_at.desc()).all()
    # Full catalog list for the "Registered Items" drill-down modal
    catalog_items = ScmeItems.query.filter(ScmeItems.type == 'scme').order_by(ScmeItems.item_name).all()
    ecc_states = EccMonthlyState.query.order_by(EccMonthlyState.created_at.desc()).all()

    # ECC specific counts & datasets
    total_ecc_items = ScmeItems.query.filter(ScmeItems.type == 'ecc').count()
    ecc_catalog_items = ScmeItems.query.filter(ScmeItems.type == 'ecc').order_by(ScmeItems.item_name).all()
    
    ecc_chart_data = []
    total_ecc_auth = 0
    total_ecc_held = 0
    global_ecc_deficiency = 0
    ecc_divisions = set()
    for state in ecc_states:
        if state.bbf_division:
            ecc_divisions.add(state.bbf_division)
        total_ecc_auth += (state.auth_total or 0)
        total_ecc_held += (state.stock_total or 0)
        global_ecc_deficiency += (state.deficiency or 0)
        ecc_chart_data.append({
            "id": state.id,
            "division": state.bbf_division,
            "item_name": state.item.item_name if state.item else "Unknown",
            "category": state.item.category if state.item else "Unknown",
            "scale": state.scale,
            "auth_total": state.auth_total or 0,
            "unit_auth": state.unit_auth or 0,
            "bbf_total": state.bbf_total or 0,
            "recd_total": state.recd_total or 0,
            "issd_total": state.issd_total or 0,
            "stock_ser": state.stock_ser or 0,
            "stock_pws": state.stock_pws or 0,
            "stock_total": state.stock_total or 0,
            "tps": state.tps or 0,
            "deficiency": state.deficiency or 0
        })
    active_ecc_divisions = len(ecc_divisions)

    # Compute ECC Supply Readiness by Division
    from collections import defaultdict
    ecc_div_readiness = defaultdict(lambda: {"auth": 0, "held": 0})
    for state in ecc_states:
        if state.bbf_division:
            ecc_div_readiness[state.bbf_division]["auth"] += (state.auth_total or 0)
            ecc_div_readiness[state.bbf_division]["held"] += (state.stock_total or 0)

    ecc_readiness_data = [
        {
            "division": div.replace('_', ' ').upper(),
            "rate": round((float(totals["held"]) / float(totals["auth"]) * 100), 1) if (totals["auth"] or 0) > 0 else 0
        } for div, totals in ecc_div_readiness.items()
    ]

    ecc_critical_alerts = EccMonthlyState.query.filter(
        EccMonthlyState.unit_auth > 0,
        EccMonthlyState.stock_total < (EccMonthlyState.unit_auth / 2)
    ).count()

    db_units = Units.query.order_by(Units.name).all()
    db_units_data = [
        {
            "name": u.name.replace('_', ' ').upper(),
            "authorized_strength": u.authorized_strength or 0,
            "posted_strength": u.posted_strength or 0
        } for u in db_units
    ]

    return render_template(
        '/scme_dashboard/scme.html',
        total_items=total_items,
        active_units=active_units,
        global_deficiency=global_deficiency,
        fulfillment_rate=fulfillment_rate,
        critical_alerts=critical_alerts,
        unit_chart_data=unit_chart_data,
        item_chart_data=item_chart_data,
        overall_chart_data=overall_chart_data,
        unit_deficiency_share_data=unit_deficiency_share_data,
        au_split_data=au_split_data,
        unit_readiness_data=unit_readiness_data,
        issued_items=issued_items,
        catalog_items=catalog_items,
        ecc_states=ecc_states,
        total_ecc_items=total_ecc_items,
        ecc_catalog_items=ecc_catalog_items,
        ecc_chart_data=ecc_chart_data,
        total_ecc_auth=total_ecc_auth,
        total_ecc_held=total_ecc_held,
        global_ecc_deficiency=global_ecc_deficiency,
        active_ecc_divisions=active_ecc_divisions,
        ecc_readiness_data=ecc_readiness_data,
        db_units=db_units,
        ecc_critical_alerts=ecc_critical_alerts,
        db_units_data=db_units_data
    )
@scme_bp.route('/enter-items')
def enter_items():
    if "user_id" not in session or session.get("role") != "scme":
        return redirect("/auth/login")
    
    # Get distinct categories from scme_items
    categories = [r[0] for r in db.session.query(ScmeItems.category).distinct().all()]
    scme_categories = [r[0] for r in db.session.query(ScmeItems.category).filter(ScmeItems.type == 'scme').distinct().all()]
    ecc_categories = [r[0] for r in db.session.query(ScmeItems.category).filter(ScmeItems.type == 'ecc').distinct().all()]
    
    # Get all units
    units = Units.query.order_by(Units.name).all()
    
    # Get all items to filter in frontend JS
    items = ScmeItems.query.order_by(ScmeItems.item_name).all()
    
    # Get already issued items history
    issued_items = ScmeIssuedItems.query.order_by(ScmeIssuedItems.created_at.desc()).all()
    
    # Get previously entered monthly states
    ecc_states = EccMonthlyState.query.order_by(EccMonthlyState.created_at.desc()).all()
    
    return render_template(
        '/scme_dashboard/enter_scme_items.html',
        categories=categories,
        scme_categories=scme_categories,
        ecc_categories=ecc_categories,
        units=units,
        items=items,
        issued_items=issued_items,
        ecc_states=ecc_states
    )


@scme_bp.route('/api/add-item', methods=['POST'])
def api_add_item():
    if "user_id" not in session or session.get("role") != "scme":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    try:
        data = request.get_json()
        item_name = data.get("item_name", "").strip()
        category = data.get("category", "").strip()
        item_type = data.get("type", "scme").strip().lower()
        
        if not item_name:
            return jsonify({"success": False, "message": "Item name is required"}), 400
            
        if not category:
            category = "CAT-II"
            
        if item_type not in ["ecc", "scme"]:
            item_type = "scme"

        if has_special_characters(item_name):
            return jsonify({"success": False, "message": "Item name contains invalid special characters."}), 400
            
        if has_special_characters(category):
            return jsonify({"success": False, "message": "Category contains invalid special characters."}), 400
            
        # Check if item already exists
        existing = ScmeItems.query.filter(ScmeItems.item_name == item_name).first()
        if existing:
            return jsonify({"success": False, "message": "An item with this name already exists."}), 400
            
        new_item = ScmeItems(item_name=item_name, category=category, type=item_type)
        db.session.add(new_item)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Item added successfully.",
            "item": {
                "id": new_item.id, 
                "item_name": new_item.item_name,
                "category": new_item.category,
                "type": new_item.type
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@scme_bp.route('/api/issue-item', methods=['POST'])
def api_issue_item():
    if "user_id" not in session or session.get("role") != "scme":
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        
        unit_name = (data.get("unit_name") or "").strip()
        item_id = data.get("item_id")
        a_u = (data.get("a_u") or "").strip()
        scale = (data.get("scale") or "").strip()
        unit_authorized = data.get("unit_authorized")
        held = data.get("held")

        
        if not unit_name or not item_id:
            return jsonify({"success": False, "message": "Unit Name and Item are required."}), 400
        if a_u not in ("Nos", "Prs"):
            return jsonify({"success": False, "message": "A/U must be Nos or Prs."}), 400

        # ── Scale: percentage string like "50%" (1-100) ──
        scale_digits = scale.replace("%", "").strip()
        if not scale_digits.isdigit() or not (1 <= int(scale_digits) <= 100):
            return jsonify({"success": False, "message": "Scale must be a percentage between 1% and 100%."}), 400
        scale_val = f"{int(scale_digits)}%"

        # ── Integer fields ──
        try:
            unit_authorized_val = int(unit_authorized)
            held_val = int(held)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Unit Authorized and Held must be numbers."}), 400

        if unit_authorized_val < 0 or held_val < 0:
            return jsonify({"success": False, "message": "Values cannot be negative."}), 400

        # Deficiency = Unit Authorized - Held
        deficiency_val = unit_authorized_val - held_val

        # ── Verify Unit and Item exist ──
        unit_exists = Units.query.filter_by(name=unit_name).first()
        item_exists = ScmeItems.query.get(item_id)

        if not unit_exists:
            return jsonify({"success": False, "message": "Selected Unit does not exist."}), 400
        if not item_exists:
            return jsonify({"success": False, "message": "Selected Item does not exist."}), 400

        new_issued = ScmeIssuedItems(
            unit_name=unit_name,
            item_id=item_id,
            a_u=a_u,
            unit_authorized=unit_authorized_val,
            scale=scale_val,
            held=held_val,
            deficiency=deficiency_val
        )
        db.session.add(new_issued)
        db.session.commit()

        # Log action
        log_entry = ActionLog(
            user_id=session.get("user_id"),
            username=session.get("username", "Unknown"),
            role=session.get("role", "scme"),
            action_type="CREATE",
            module="SCME",
            details=f"Recorded new SCME item: '{item_exists.item_name}' (Unit: {new_issued.unit_name}, Unit Auth: {new_issued.unit_authorized}, Held: {new_issued.held})"
        )
        db.session.add(log_entry)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "SCME issued item recorded successfully.",
            "issued_item": {
                "id": new_issued.id,
                "unit_name": new_issued.unit_name,
                "item_name": item_exists.item_name,
                "category": item_exists.category,
                "a_u": new_issued.a_u,
                "unit_authorized": new_issued.unit_authorized,
                "scale": new_issued.scale,
                "held": new_issued.held,
                "deficiency": new_issued.deficiency,
                "created_at": new_issued.created_at.strftime('%d %b %Y, %H:%M') if new_issued.created_at else ""
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@scme_bp.route('/api/issue-item/<int:item_id>', methods=['PUT'])
def api_update_issued_item(item_id):
    if "user_id" not in session or session.get("role") != "scme":
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        record = ScmeIssuedItems.query.get(item_id)
        if not record:
            return jsonify({"success": False, "message": "Record not found."}), 404

        data = request.get_json()

        unit_name = (data.get("unit_name") or "").strip()
        new_item_id = data.get("item_id")
        a_u = (data.get("a_u") or "").strip()
        scale = (data.get("scale") or "").strip()
        unit_authorized = data.get("unit_authorized")
        held = data.get("held")

        if not unit_name or not new_item_id:
            return jsonify({"success": False, "message": "Unit Name and Item are required."}), 400
        if a_u not in ("Nos", "Prs"):
            return jsonify({"success": False, "message": "A/U must be Nos or Prs."}), 400

        scale_digits = scale.replace("%", "").strip()
        if not scale_digits.isdigit() or not (1 <= int(scale_digits) <= 100):
            return jsonify({"success": False, "message": "Scale must be a percentage between 1% and 100%."}), 400
        scale_val = f"{int(scale_digits)}%"

        tx_type = data.get("transaction_type")
        tx_qty = data.get("transaction_qty")

        try:
            unit_authorized_val = int(unit_authorized)
            if tx_type in ("Issue", "Return") and tx_qty is not None:
                tx_qty_val = int(tx_qty)
                if tx_qty_val < 0:
                    return jsonify({"success": False, "message": "Transaction quantity cannot be negative."}), 400
                
                if tx_type == "Issue":
                    held_val = record.held + tx_qty_val
                else: # Return
                    held_val = record.held - tx_qty_val
            else:
                held_val = int(held)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Unit Authorized, Held, and Transaction Quantity must be numbers."}), 400

        if unit_authorized_val < 0 or held_val < 0:
            return jsonify({"success": False, "message": "Values cannot be negative. Held quantity cannot drop below 0."}), 400

        deficiency_val = unit_authorized_val - held_val

        unit_exists = Units.query.filter_by(name=unit_name).first()
        item_exists = ScmeItems.query.get(new_item_id)

        if not unit_exists:
            return jsonify({"success": False, "message": "Selected Unit does not exist."}), 400
        if not item_exists:
            return jsonify({"success": False, "message": "Selected Item does not exist."}), 400

        record.unit_name = unit_name
        record.item_id = new_item_id
        record.a_u = a_u
        record.unit_authorized = unit_authorized_val
        record.scale = scale_val
        record.held = held_val
        record.deficiency = deficiency_val

        db.session.commit()

        # Log action
        if tx_type in ("Issue", "Return") and tx_qty is not None:
            details_str = f"{tx_type}d {tx_qty} of '{item_exists.item_name}' for unit {record.unit_name}. (New Held: {record.held})"
        else:
            details_str = f"Updated SCME item: '{item_exists.item_name}' (Unit: {record.unit_name}, Unit Auth: {record.unit_authorized}, Held: {record.held})"

        log_entry = ActionLog(
            user_id=session.get("user_id"),
            username=session.get("username", "Unknown"),
            role=session.get("role", "scme"),
            action_type="UPDATE",
            module="SCME",
            details=details_str
        )
        db.session.add(log_entry)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "SCME issued item updated successfully.",
            "issued_item": {
                "id": record.id,
                "unit_name": record.unit_name,
                "item_name": item_exists.item_name,
                "category": item_exists.category,
                "a_u": record.a_u,
                "unit_authorized": record.unit_authorized,
                "scale": record.scale,
                "held": record.held,
                "deficiency": record.deficiency,
                "created_at": record.created_at.strftime('%d %b %Y, %H:%M') if record.created_at else ""
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/issue-item/<int:item_id>', methods=['DELETE'])
def api_delete_issued_item(item_id):
    if "user_id" not in session or session.get("role") != "scme":
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        record = ScmeIssuedItems.query.get(item_id)
        if not record:
            return jsonify({"success": False, "message": "Record not found."}), 404

        item_name = record.item.item_name if record.item else f"Item ID {record.item_id}"
        unit_name = record.unit_name

        db.session.delete(record)
        db.session.commit()

        # Log action
        log_entry = ActionLog(
            user_id=session.get("user_id"),
            username=session.get("username", "Unknown"),
            role=session.get("role", "scme"),
            action_type="DELETE",
            module="SCME",
            details=f"Deleted SCME item: '{item_name}' for unit {unit_name}"
        )
        db.session.add(log_entry)
        db.session.commit()

        return jsonify({"success": True, "message": "Record deleted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/logs', methods=['GET'])
def api_get_logs():
    if "user_id" not in session or session.get("role") != "scme":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        logs = ActionLog.query.filter_by(module="SCME").order_by(ActionLog.created_at.desc()).limit(50).all()
        log_list = []
        for log in logs:
            log_list.append({
                "id": log.id,
                "username": log.username,
                "role": log.role,
                "action_type": log.action_type,
                "details": log.details,
                "created_at": log.created_at.strftime('%d %b %Y, %H:%M') if log.created_at else ""
            })
        return jsonify({"success": True, "logs": log_list}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/add-ecc-state', methods=['POST'])
def api_add_ecc_state():
    if "user_id" not in session or session.get("role") != "scme":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    try:
        data = request.get_json()
        item_id = data.get("item_id")
        scale = (data.get("scale") or "").strip()
        
        # Section 2: Auth
        auth_auth = data.get("auth_auth")
        auth_res = data.get("auth_res")
        unit_auth = data.get("unit_auth")
        
        # Section 3: BBF Last Month
        bbf_division = (data.get("bbf_division") or "").strip()
        bbf_ser = data.get("bbf_ser")
        bbf_pws = data.get("bbf_pws")
        bbf_comd = data.get("bbf_comd")
        bbf_ihq = data.get("bbf_ihq")
        
        # Section 4: Received This Month
        recd_ser = data.get("recd_ser")
        recd_pws = data.get("recd_pws")
        
        # Section 5: Issued This Month
        issd_ser = data.get("issd_ser")
        issd_pws = data.get("issd_pws")
        
        # Section 6: Stock Held
        stock_ser = data.get("stock_ser")
        stock_pws = data.get("stock_pws")
        stock_comd = data.get("stock_comd")
        stock_ihq = data.get("stock_ihq")
        
        # Section 7: Additional Fields
        add_knd = data.get("add_knd")
        add_tn_model = data.get("add_tn_model")
        add_n_area_otg = data.get("add_n_area_otg")
        add_idt_ict = data.get("add_idt_ict")
        add_remarks_ro_bal = data.get("add_remarks_ro_bal")
        
        # Section 8: Stock Held with TPS
        tps = data.get("tps")
        deficiency = data.get("deficiency")
        
        # Validate required fields
        if not item_id or not bbf_division:
            return jsonify({"success": False, "message": "Item and Division are required."}), 400
            
        # Parse integers
        try:
            item_id_val = int(item_id)
            auth_auth_val = int(auth_auth or 0)
            auth_res_val = int(auth_res or 0)
            auth_total_val = auth_auth_val + auth_res_val
            unit_auth_val = int(unit_auth or 0)
            
            bbf_ser_val = int(bbf_ser or 0)
            bbf_pws_val = int(bbf_pws or 0)
            bbf_total_val = bbf_ser_val + bbf_pws_val
            bbf_comd_val = int(bbf_comd) if bbf_comd is not None and bbf_comd != "" else None
            bbf_ihq_val = int(bbf_ihq) if bbf_ihq is not None and bbf_ihq != "" else None
            
            recd_ser_val = int(recd_ser or 0)
            recd_pws_val = int(recd_pws or 0)
            recd_total_val = recd_ser_val + recd_pws_val
            
            issd_ser_val = int(issd_ser or 0)
            issd_pws_val = int(issd_pws or 0)
            issd_total_val = issd_ser_val + issd_pws_val
            
            stock_ser_val = int(stock_ser or 0)
            stock_pws_val = int(stock_pws or 0)
            stock_total_val = stock_ser_val + stock_pws_val
            stock_comd_val = int(stock_comd) if stock_comd is not None and stock_comd != "" else None
            stock_ihq_val = int(stock_ihq) if stock_ihq is not None and stock_ihq != "" else None
            
            add_knd_val = int(add_knd or 0)
            add_tn_model_val = int(add_tn_model or 0)
            add_n_area_otg_val = int(add_n_area_otg or 0)
            add_idt_ict_val = int(add_idt_ict or 0)
            add_remarks_ro_bal_val = int(add_remarks_ro_bal or 0)
            
            tps_val = int(tps or 0)
            deficiency_val = unit_auth_val - stock_total_val
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "All input values (except scale) must be numbers."}), 400
            
        # Verify item exists in DB
        item_exists = ScmeItems.query.get(item_id_val)
        if not item_exists:
            return jsonify({"success": False, "message": "Selected Item does not exist."}), 400
            
        # Create record
        new_state = EccMonthlyState(
            item_id=item_id_val,
            scale=scale,
            auth_auth=auth_auth_val,
            auth_res=auth_res_val,
            auth_total=auth_total_val,
            bbf_division=bbf_division,
            bbf_ser=bbf_ser_val,
            bbf_pws=bbf_pws_val,
            bbf_total=bbf_total_val,
            bbf_comd=bbf_comd_val,
            bbf_ihq=bbf_ihq_val,
            recd_ser=recd_ser_val,
            recd_pws=recd_pws_val,
            recd_total=recd_total_val,
            issd_ser=issd_ser_val,
            issd_pws=issd_pws_val,
            issd_total=issd_total_val,
            stock_ser=stock_ser_val,
            stock_pws=stock_pws_val,
            stock_total=stock_total_val,
            stock_comd=stock_comd_val,
            stock_ihq=stock_ihq_val,
            add_knd=add_knd_val,
            add_tn_model=add_tn_model_val,
            add_n_area_otg=add_n_area_otg_val,
            add_idt_ict=add_idt_ict_val,
            add_remarks_ro_bal=add_remarks_ro_bal_val,
            tps=tps_val,
            deficiency=deficiency_val,
            unit_auth=unit_auth_val
        )
        
        db.session.add(new_state)
        
        # Log action
        log_entry = ActionLog(
            user_id=session.get("user_id"),
            username=session.get("username", "Unknown"),
            role=session.get("role", "scme"),
            action_type="CREATE",
            module="ECC",
            details=f"Recorded monthly state for Item: '{item_exists.item_name}', Division: {bbf_division}"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "ECC monthly state recorded successfully.",
            "state": {
                "id": new_state.id,
                "item_name": item_exists.item_name,
                "scale": new_state.scale,
                "bbf_division": new_state.bbf_division,
                "auth_total": new_state.auth_total,
                "bbf_total": new_state.bbf_total,
                "recd_total": new_state.recd_total,
                "issd_total": new_state.issd_total,
                "stock_total": new_state.stock_total,
                "deficiency": new_state.deficiency,
                "created_at": new_state.created_at.strftime('%d %b %Y, %H:%M') if new_state.created_at else ""
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/ecc-state/<int:state_id>', methods=['PUT', 'DELETE'])
def api_ecc_state_actions(state_id):
    if "user_id" not in session or session.get("role") != "scme":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    record = EccMonthlyState.query.get(state_id)
    if not record:
        return jsonify({"success": False, "message": "Record not found."}), 404
        
    if request.method == 'DELETE':
        try:
            item_name = record.item.item_name if record.item else f"Item ID {record.item_id}"
            div_name = record.bbf_division
            
            db.session.delete(record)
            
            # Log action
            log_entry = ActionLog(
                user_id=session.get("user_id"),
                username=session.get("username", "Unknown"),
                role=session.get("role", "scme"),
                action_type="DELETE",
                module="ECC",
                details=f"Deleted ECC monthly state for Item: '{item_name}', Division: {div_name}"
            )
            db.session.add(log_entry)
            db.session.commit()
            
            return jsonify({"success": True, "message": "Record deleted successfully."}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
            
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            item_id = data.get("item_id")
            scale = (data.get("scale") or "").strip()
            
            # Section 2: Auth
            auth_auth = data.get("auth_auth")
            auth_res = data.get("auth_res")
            unit_auth = data.get("unit_auth")
            
            # Section 3: BBF Last Month
            bbf_division = (data.get("bbf_division") or "").strip()
            bbf_ser = data.get("bbf_ser")
            bbf_pws = data.get("bbf_pws")
            bbf_comd = data.get("bbf_comd")
            bbf_ihq = data.get("bbf_ihq")
            
            # Section 4: Received This Month
            recd_ser = data.get("recd_ser")
            recd_pws = data.get("recd_pws")
            
            # Section 5: Issued This Month
            issd_ser = data.get("issd_ser")
            issd_pws = data.get("issd_pws")
            
            # Section 6: Stock Held
            stock_ser = data.get("stock_ser")
            stock_pws = data.get("stock_pws")
            stock_comd = data.get("stock_comd")
            stock_ihq = data.get("stock_ihq")
            
            # Section 7: Additional Fields
            add_knd = data.get("add_knd")
            add_tn_model = data.get("add_tn_model")
            add_n_area_otg = data.get("add_n_area_otg")
            add_idt_ict = data.get("add_idt_ict")
            add_remarks_ro_bal = data.get("add_remarks_ro_bal")
            
            # Section 8: Stock Held with TPS
            tps = data.get("tps")
            
            # Validate required fields
            if not item_id or not bbf_division:
                return jsonify({"success": False, "message": "Item and Division are required."}), 400
                
            # Parse integers
            try:
                item_id_val = int(item_id)
                auth_auth_val = int(auth_auth or 0)
                auth_res_val = int(auth_res or 0)
                auth_total_val = auth_auth_val + auth_res_val
                unit_auth_val = int(unit_auth or 0)
                
                bbf_ser_val = int(bbf_ser or 0)
                bbf_pws_val = int(bbf_pws or 0)
                bbf_total_val = bbf_ser_val + bbf_pws_val
                bbf_comd_val = int(bbf_comd) if bbf_comd is not None and bbf_comd != "" else None
                bbf_ihq_val = int(bbf_ihq) if bbf_ihq is not None and bbf_ihq != "" else None
                
                recd_ser_val = int(recd_ser or 0)
                recd_pws_val = int(recd_pws or 0)
                recd_total_val = recd_ser_val + recd_pws_val
                
                issd_ser_val = int(issd_ser or 0)
                issd_pws_val = int(issd_pws or 0)
                issd_total_val = issd_ser_val + issd_pws_val
                
                stock_ser_val = int(stock_ser or 0)
                stock_pws_val = int(stock_pws or 0)
                stock_total_val = stock_ser_val + stock_pws_val
                stock_comd_val = int(stock_comd) if stock_comd is not None and stock_comd != "" else None
                stock_ihq_val = int(stock_ihq) if stock_ihq is not None and stock_ihq != "" else None
                
                add_knd_val = int(add_knd or 0)
                add_tn_model_val = int(add_tn_model or 0)
                add_n_area_otg_val = int(add_n_area_otg or 0)
                add_idt_ict_val = int(add_idt_ict or 0)
                add_remarks_ro_bal_val = int(add_remarks_ro_bal or 0)
                
                tps_val = int(tps or 0)
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": "All input values (except scale) must be numbers."}), 400
                
            item_exists = ScmeItems.query.get(item_id_val)
            if not item_exists:
                return jsonify({"success": False, "message": "Selected Item does not exist."}), 400
                
            # Update fields
            record.item_id = item_id_val
            record.scale = scale
            record.auth_auth = auth_auth_val
            record.auth_res = auth_res_val
            record.auth_total = auth_total_val
            record.bbf_division = bbf_division
            record.bbf_ser = bbf_ser_val
            record.bbf_pws = bbf_pws_val
            record.bbf_total = bbf_total_val
            record.bbf_comd = bbf_comd_val
            record.bbf_ihq = bbf_ihq_val
            record.recd_ser = recd_ser_val
            record.recd_pws = recd_pws_val
            record.recd_total = recd_total_val
            record.issd_ser = issd_ser_val
            record.issd_pws = issd_pws_val
            record.issd_total = issd_total_val
            record.stock_ser = stock_ser_val
            record.stock_pws = stock_pws_val
            record.stock_total = stock_total_val
            record.stock_comd = stock_comd_val
            record.stock_ihq = stock_ihq_val
            record.add_knd = add_knd_val
            record.add_tn_model = add_tn_model_val
            record.add_n_area_otg = add_n_area_otg_val
            record.add_idt_ict = add_idt_ict_val
            record.add_remarks_ro_bal = add_remarks_ro_bal_val
            record.tps = tps_val
            record.unit_auth = unit_auth_val
            record.deficiency = unit_auth_val - stock_total_val
            
            # Log action
            log_entry = ActionLog(
                user_id=session.get("user_id"),
                username=session.get("username", "Unknown"),
                role=session.get("role", "scme"),
                action_type="UPDATE",
                module="ECC",
                details=f"Updated ECC monthly state for Item: '{item_exists.item_name}', Division: {bbf_division}"
            )
            db.session.add(log_entry)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "ECC monthly state updated successfully.",
                "state": {
                    "id": record.id,
                    "item_name": item_exists.item_name,
                    "scale": record.scale,
                    "bbf_division": record.bbf_division,
                    "auth_total": record.auth_total,
                    "created_at": record.created_at.strftime('%d %b %Y, %H:%M') if record.created_at else ""
                }
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)}), 500