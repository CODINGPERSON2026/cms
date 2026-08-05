from imports import *
from extensions import db
from models import LoginUser, ActionLog
from models.our_items import OurItems, ItemRequestTable, ScmeItems, Units, Divs, ScmeIssuedItems, TrackUnitItems, FodStock, ItemAuth, Transactions
from models.org_ladder import OrgLadder
from validation import has_special_characters
from datetime import datetime, timezone

scme_bp = Blueprint("scme", __name__, url_prefix='/scme')


@scme_bp.route('/')
def scme_home():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return redirect("/auth/login")

    is_div_admin = (user_role == "division_admin")
    user_div = session.get("username", "").strip() if is_div_admin else None

    from sqlalchemy import func

    # 1. Total Catalog Items
    total_items = ScmeItems.query.filter(ScmeItems.type == 'scme').count()

    # 2. Active Units Tracked (Unique count of units in Units table)
    units_table_unique_count = db.session.query(func.count(func.distinct(Units.name))).filter(Units.name != '', Units.name.isnot(None)).scalar() or 0
    active_units = units_table_unique_count

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
    now_date = datetime.now()
    first_day_of_current_month = datetime(now_date.year, now_date.month, 1)

    # Adapter to seamlessly supply TrackUnitItems to templates expecting modal summary fields
    class TrackUnitAdapter:
        def __init__(self, rec, prev_rec=None):
            self.id = rec.id or 0
            self.item_id = rec.item_id or 0
            self.bbf_division = rec.unit_name or ''
            self.unit_name = rec.unit_name or ''
            self.item = rec.item
            self.scale = getattr(rec, 'scale', None) or "N/A"
            
            # Fetch AUTH from ItemAuth if present, fallback to rec.auth
            auth_rec = ItemAuth.query.filter(
                func.lower(func.trim(ItemAuth.unit_name)) == (rec.unit_name or '').lower().strip(),
                ItemAuth.item_id == rec.item_id
            ).first()
            auth_val = auth_rec.auth if (auth_rec and auth_rec.auth is not None) else (rec.auth or 0)
            self.auth_auth = 0
            self.auth_res = 0
            self.auth_total = auth_val
            self.unit_auth = auth_val
            
            # PREVIOUS MONTH DATA (FETCHED FROM DB RECORD BEFORE CURRENT MONTH)
            if prev_rec:
                p_ser = (prev_rec.ser or 0) + (getattr(prev_rec, 'available_ser', 0) or 0)
                p_pws = (prev_rec.pws or 0) + (getattr(prev_rec, 'available_pws', 0) or 0)
                self.prev_ser = p_ser
                self.prev_pws = p_pws
            else:
                self.prev_ser = 0
                self.prev_pws = 0
            
            self.prev_total = self.prev_ser + self.prev_pws
            self.bbf_ser = self.prev_ser
            self.bbf_pws = self.prev_pws
            self.bbf_total = self.prev_total
            self.bbf_comd = 0
            self.bbf_ihq = 0
            self.recd_ser = 0
            self.recd_pws = 0
            self.recd_total = 0
            self.issd_ser = 0
            self.issd_pws = 0
            self.issd_total = 0
            
            # CURRENT MONTH DATA (STOCK HELD FETCHED FROM DB: Ser = ser + available_ser, PWS = pws + available_pws)
            a_ser = getattr(rec, 'available_ser', 0) or 0
            a_pws = getattr(rec, 'available_pws', 0) or 0

            self.stock_ser = (rec.ser or 0) + a_ser
            self.stock_pws = (rec.pws or 0) + a_pws
            self.stock_total = self.stock_ser + self.stock_pws
            self.stock_comd = 0
            self.stock_ihq = 0
            self.add_knd = getattr(rec, 'add_knd', 0) or 0
            self.add_tn_model = getattr(rec, 'add_tn_model', 0) or 0
            self.add_n_area_otg = getattr(rec, 'add_n_area_otg', 0) or 0
            self.add_idt_ict = getattr(rec, 'add_idt_ict', 0) or 0
            self.add_remarks_ro_bal = 0
            self.tps = self.stock_total
            self.deficiency = self.unit_auth - self.stock_total
            self.created_at = rec.issued_at

    # Fetch division names directly from Divs table
    div_records = Divs.query.order_by(Divs.name).all()
    div_admin_names = list(dict.fromkeys(d.name.strip() for d in div_records if d.name and d.name.strip()))

    track_query = TrackUnitItems.query
    if is_div_admin and user_div:
        track_query = track_query.filter(TrackUnitItems.unit_name == user_div)
    else:
        if div_admin_names:
            track_query = track_query.filter(TrackUnitItems.unit_name.in_(div_admin_names))

    track_records = track_query.order_by(TrackUnitItems.issued_at.desc(), TrackUnitItems.id.desc()).all()
    
    # Group track_records by unique (unit_name, item_id) to eliminate duplicate rows per item
    grouped_track_map = {}
    for rec in track_records:
        u_key = (rec.unit_name or '').lower().strip()
        key = (u_key, rec.item_id)
        if key not in grouped_track_map:
            grouped_track_map[key] = []
        grouped_track_map[key].append(rec)

    ecc_states = []

    # ── Calculate first day of PREVIOUS month ──
    if now_date.month == 1:
        first_day_prev_month = datetime(now_date.year - 1, 12, 1)
    else:
        first_day_prev_month = datetime(now_date.year, now_date.month - 1, 1)

    first_day_next_month = datetime(
        now_date.year + (1 if now_date.month == 12 else 0),
        1 if now_date.month == 12 else now_date.month + 1,
        1
    )

    # ── PREVIOUS MONTH: Query transactions table for previous calendar month ──
    # Build lookup: { (received_by_lower, item_id): {'ser': X, 'pws': Y} }
    prev_month_map = {}
    prev_trans = Transactions.query.filter(
        Transactions.timestamp >= first_day_prev_month,
        Transactions.timestamp < first_day_of_current_month
    ).all()
    for t in prev_trans:
        r_key = (t.received_by or '').lower().strip()
        key = (r_key, t.item_id)
        if key not in prev_month_map:
            prev_month_map[key] = {'ser': 0, 'pws': 0}
        prev_month_map[key]['ser'] += (t.ser or 0)
        prev_month_map[key]['pws'] += (t.pws or 0)

    # ── ISSUED DURING MONTH: Query transactions table for current month ──
    # Build lookup: { (received_by_lower, item_id): {'ser': X, 'pws': Y} }
    issued_this_month_map = {}
    issd_trans = Transactions.query.filter(
        Transactions.timestamp >= first_day_of_current_month,
        Transactions.timestamp < first_day_next_month
    ).all()
    for t in issd_trans:
        r_key = (t.received_by or '').lower().strip()
        key = (r_key, t.item_id)
        if key not in issued_this_month_map:
            issued_this_month_map[key] = {'ser': 0, 'pws': 0}
        issued_this_month_map[key]['ser'] += (t.ser or 0)
        issued_this_month_map[key]['pws'] += (t.pws or 0)

    for (u_key, item_id), group_recs in grouped_track_map.items():
        # Latest record overall for base info
        rec = group_recs[0]

        adapter = TrackUnitAdapter(rec, None)

        # PREVIOUS MONTH: Real data from transactions table (previous calendar month)
        prev_data = prev_month_map.get((u_key, item_id), {'ser': 0, 'pws': 0})
        adapter.prev_ser   = prev_data['ser']
        adapter.prev_pws   = prev_data['pws']
        adapter.prev_total = adapter.prev_ser + adapter.prev_pws
        adapter.bbf_ser    = adapter.prev_ser
        adapter.bbf_pws    = adapter.prev_pws
        adapter.bbf_total  = adapter.prev_total

        # STOCK HELD: Cumulative sum of ALL months for this unit & item
        tot_ser = sum((r.ser or 0) + (getattr(r, 'available_ser', 0) or 0) for r in group_recs)
        tot_pws = sum((r.pws or 0) + (getattr(r, 'available_pws', 0) or 0) for r in group_recs)

        adapter.stock_ser   = tot_ser
        adapter.stock_pws   = tot_pws
        adapter.stock_total = tot_ser + tot_pws
        adapter.tps         = adapter.stock_total
        adapter.deficiency  = max(0, adapter.unit_auth - adapter.stock_total)

        # ISSUED DURING MONTH: Real issuance data from transactions table (current month)
        issd_data = issued_this_month_map.get((u_key, item_id), {'ser': 0, 'pws': 0})
        adapter.issd_ser   = issd_data['ser']
        adapter.issd_pws   = issd_data['pws']
        adapter.issd_total = adapter.issd_ser + adapter.issd_pws

        ecc_states.append(adapter)

    # ECC specific counts & datasets from TrackUnitItems
    total_ecc_items = ScmeItems.query.filter(ScmeItems.type == 'ecc').count()
    ecc_catalog_items = ScmeItems.query.filter(ScmeItems.type == 'ecc').order_by(ScmeItems.item_name).all()
    
    ecc_chart_data = []
    total_ecc_auth = 0
    total_ecc_held = 0
    global_ecc_deficiency = 0
    ecc_divisions = set()
    for s in ecc_states:
        div = s.unit_name
        if div:
            ecc_divisions.add(div)
        auth_val = s.unit_auth or 0
        held_val = s.stock_total or 0
        defi_val = max(0, auth_val - held_val)

        total_ecc_auth += auth_val
        total_ecc_held += held_val
        global_ecc_deficiency += defi_val

        ecc_chart_data.append({
            "id": s.id,
            "division": div,
            "item_name": s.item.item_name if s.item else "Unknown",
            "category": s.item.category if s.item else "Unknown",
            "scale": s.scale,
            "auth_total": auth_val,
            "unit_auth": auth_val,
            "bbf_total": s.prev_total,
            "recd_total": s.recd_total,
            "issd_total": s.issd_total,
            "stock_ser": s.stock_ser,
            "stock_pws": s.stock_pws,
            "stock_total": held_val,
            "tps": getattr(s, 'tps', 0) or 0,
            "deficiency": defi_val
        })
    active_ecc_divisions = units_table_unique_count

    # Compute ECC Supply Readiness by Division
    from collections import defaultdict
    ecc_div_readiness = defaultdict(lambda: {"auth": 0, "held": 0})
    for rec in track_records:
        if rec.unit_name:
            ecc_div_readiness[rec.unit_name]["auth"] += (rec.auth or 0)
            ecc_div_readiness[rec.unit_name]["held"] += rec.calc_held()

    ecc_readiness_data = [
        {
            "division": div.replace('_', ' ').upper(),
            "rate": round((float(totals["held"]) / float(totals["auth"]) * 100), 1) if (totals["auth"] or 0) > 0 else 0
        } for div, totals in ecc_div_readiness.items()
    ]

    crit_query = TrackUnitItems.query.filter(
        TrackUnitItems.auth > 0,
        TrackUnitItems.held < (TrackUnitItems.auth / 2)
    )
    if is_div_admin and user_div:
        crit_query = crit_query.filter(TrackUnitItems.unit_name == user_div)
    elif div_admin_names:
        crit_query = crit_query.filter(TrackUnitItems.unit_name.in_(div_admin_names))
    ecc_critical_alerts = crit_query.count()

    # Query Units table directly for Posted Strength by Unit chart
    units_query = Units.query
    if is_div_admin and user_div:
        units_query = units_query.filter(Units.name == user_div)
    elif div_admin_names:
        units_query = units_query.filter(Units.name.in_(div_admin_names))

    db_units = units_query.order_by(Units.name).all()

    db_units_data = [
        {
            "name": u.name.replace('_', ' ').upper() if u.name else "",
            "authorized_strength": u.authorized_strength or 0,
            "posted_strength": u.posted_strength or 0
        } for u in db_units
    ]

    # Build Month-wise Held Trend Dataset from TrackUnitItems
    all_history_records = track_query.order_by(TrackUnitItems.issued_at.asc(), TrackUnitItems.id.asc()).all()
    monthly_held_trend_data = []
    for rec in all_history_records:
        rec_dt = rec.issued_at
        month_label = rec_dt.strftime('%b %Y') if rec_dt else "N/A"
        item_obj = rec.item
        item_name_str = item_obj.item_name if (item_obj and hasattr(item_obj, 'item_name')) else f"Item #{rec.item_id}"
        monthly_held_trend_data.append({
            "unit": rec.unit_name,
            "item_id": rec.item_id,
            "item_name": item_name_str,
            "month": month_label,
            "held": rec.held or 0,
            "ser": rec.ser or 0,
            "pws": rec.pws or 0,
            "auth": rec.auth or 0
        })

    items = ScmeItems.query.order_by(ScmeItems.item_name).all()
    categories = sorted(list(set(i.category for i in items if i.category)))
    ecc_categories = categories

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
        db_units_data=db_units_data,
        monthly_held_trend_data=monthly_held_trend_data,
        is_div_admin=is_div_admin,
        user_div=user_div or "",
        items=items,
        categories=categories,
        ecc_categories=ecc_categories
    )
@scme_bp.route('/enter-items')
def enter_items():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return redirect("/auth/login")
    
    is_div_admin = (user_role == "division_admin")
    user_div = session.get("username", "").strip() if is_div_admin else ""
    
    # Get distinct categories from scme_items
    categories = [r[0] for r in db.session.query(ScmeItems.category).distinct().all()]
    scme_categories = [r[0] for r in db.session.query(ScmeItems.category).filter(ScmeItems.type == 'scme').distinct().all()]
    # ecc_categories are now derived after stocked_item_ids filter below
    
    divs_query = Divs.query
    if is_div_admin and user_div:
        divs_query = divs_query.filter(Divs.name == user_div)

    divs_list = divs_query.order_by(Divs.name).all()
    seen_names = set()
    units = []
    for d in divs_list:
        if d.name and d.name.strip() and d.name.strip() not in seen_names:
            seen_names.add(d.name.strip())
            units.append({"id": d.id, "name": d.name.strip()})
    
    # Get all items to filter in frontend JS
    items = ScmeItems.query.order_by(ScmeItems.item_name).all()
    scme_items = ScmeItems.query.filter(ScmeItems.type == 'scme').order_by(ScmeItems.item_name).all()

    # For ECC form: only show items that exist in fod_stock_table with quantity > 0
    from sqlalchemy import func
    stocked_item_ids = [
        r[0] for r in db.session.query(FodStock.item_id)
                                .group_by(FodStock.item_id)
                                .having(func.sum(FodStock.quantity) > 0)
                                .all()
    ]
    ecc_items = ScmeItems.query.filter(
        ScmeItems.id.in_(stocked_item_ids)
    ).order_by(ScmeItems.item_name).all()

    # Derive ECC categories only from those stocked items
    ecc_categories = sorted(set(i.category for i in ecc_items if i.category))
    
    # Get already issued items history
    issued_items = ScmeIssuedItems.query.order_by(ScmeIssuedItems.created_at.desc()).all()
    
    return render_template(
        '/scme_dashboard/enter_scme_items.html',
        categories=categories,
        scme_categories=scme_categories,
        ecc_categories=ecc_categories,
        units=units,
        items=items,
        scme_items=scme_items,
        ecc_items=ecc_items,
        stocked_item_ids=stocked_item_ids,
        issued_items=issued_items,
        is_div_admin=is_div_admin,
        user_div=user_div
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


@scme_bp.route('/api/get-unit-item-auth', methods=['GET'])
def api_get_unit_item_auth():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    unit_name = (request.args.get("unit_name") or "").strip()
    if not unit_name and user_role == "division_admin":
        unit_name = (session.get("user_div") or session.get("username") or "").strip()

    item_id = request.args.get("item_id")
    
    if not unit_name or not item_id:
        return jsonify({"success": False, "message": "Unit and Item are required"}), 400
        
    try:
        item_id_val = int(item_id)
        from sqlalchemy import func
        record = TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)) == unit_name.lower().strip(),
            TrackUnitItems.item_id == item_id_val
        ).order_by(TrackUnitItems.id.desc()).first()

        auth_val = (record.auth or 0) if record else 0
        scale_val = (record.scale or "") if record else ""

        # 2. Query ItemAuth (PRIMARY SOURCE FOR AUTH)
        auth_rec = ItemAuth.query.filter(
            func.lower(func.trim(ItemAuth.unit_name)) == unit_name.lower().strip(),
            ItemAuth.item_id == item_id_val
        ).first()

        if auth_rec and (auth_rec.auth or 0) > 0:
            auth_val = auth_rec.auth

        # 3. Query ScmeIssuedItems as fallback
        issued_rec = ScmeIssuedItems.query.filter(
            func.lower(func.trim(ScmeIssuedItems.unit_name)) == unit_name.lower().strip(),
            ScmeIssuedItems.item_id == item_id_val
        ).first()

        if auth_val == 0 and issued_rec and (issued_rec.unit_authorized or 0) > 0:
            auth_val = issued_rec.unit_authorized

        if not scale_val and issued_rec and issued_rec.scale:
            scale_val = issued_rec.scale

        if record:
            now = datetime.now()
            first_day_of_current_month = datetime(now.year, now.month, 1)
            rec_dt = record.issued_at
            if rec_dt:
                rec_naive = rec_dt.astimezone(timezone.utc).replace(tzinfo=None) if rec_dt.tzinfo else rec_dt
                is_current_month = rec_naive >= first_day_of_current_month
            else:
                is_current_month = False

            calc_held = record.calc_held()
            if (record.held or 0) == 0 and calc_held > 0:
                record.held = calc_held
                db.session.commit()

            return jsonify({
                "success": True,
                "exists": True,
                "is_current_month": is_current_month,
                "auth": auth_val,
                "scale": scale_val,
                "ser": record.ser or 0,
                "pws": record.pws or 0,
                "available_ser": record.available_ser or 0,
                "available_pws": record.available_pws or 0,
                "held": calc_held,
                "add_knd": getattr(record, 'add_knd', 0) or 0,
                "add_tn_model": getattr(record, 'add_tn_model', 0) or 0,
                "add_n_area_otg": getattr(record, 'add_n_area_otg', 0) or 0,
                "add_idt_ict": getattr(record, 'add_idt_ict', 0) or 0
            }), 200
        else:
            return jsonify({
                "success": True,
                "exists": False,
                "is_current_month": False,
                "auth": auth_val,
                "scale": scale_val,
                "ser": 0,
                "pws": 0,
                "available_ser": 0,
                "available_pws": 0,
                "held": 0,
                "add_knd": 0,
                "add_tn_model": 0,
                "add_n_area_otg": 0,
                "add_idt_ict": 0
            }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/get-previous-month-data', methods=['GET'])
def api_get_previous_month_data():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    unit_name = (request.args.get("unit_name") or "").strip()
    if not unit_name and user_role == "division_admin":
        unit_name = (session.get("user_div") or session.get("username") or "").strip()

    item_id = request.args.get("item_id")
    
    try:
        now = datetime.now()
        first_day_of_current_month = datetime(now.year, now.month, 1)

        query = TrackUnitItems.query

        if unit_name:
            query = query.filter(TrackUnitItems.unit_name == unit_name)
            
        if item_id:
            try:
                query = query.filter(TrackUnitItems.item_id == int(item_id))
            except ValueError:
                pass

        records = query.order_by(TrackUnitItems.id.desc()).all()
        
        previous_data_list = []
        for track_rec in records:
            rec_dt = track_rec.issued_at
            if rec_dt is None or (rec_dt.tzinfo and rec_dt.astimezone(timezone.utc).replace(tzinfo=None) < first_day_of_current_month) or (not rec_dt.tzinfo and rec_dt < first_day_of_current_month):
                auth_val = track_rec.auth or 0
                ser_val = track_rec.ser or 0
                pws_val = track_rec.pws or 0
                held_val = track_rec.held or (ser_val + pws_val)
                deficiency_val = max(0, auth_val - held_val)
                item_obj = track_rec.item
                item_name_str = item_obj.item_name if (item_obj and hasattr(item_obj, 'item_name')) else f"Item #{track_rec.item_id}"
                cat_str = item_obj.category if (item_obj and hasattr(item_obj, 'category')) else ""
                
                previous_data_list.append({
                    "id": track_rec.id,
                    "unit_name": track_rec.unit_name,
                    "item_id": track_rec.item_id,
                    "item_name": item_name_str,
                    "category": cat_str,
                    "created_at": rec_dt.strftime('%d %b %Y') if rec_dt else "N/A",
                    "auth": auth_val,
                    "ser": ser_val,
                    "pws": pws_val,
                    "held": held_val,
                    "deficiency": deficiency_val,
                    "add_knd": getattr(track_rec, 'add_knd', 0) or 0,
                    "add_tn_model": getattr(track_rec, 'add_tn_model', 0) or 0,
                    "add_n_area_otg": getattr(track_rec, 'add_n_area_otg', 0) or 0,
                    "add_idt_ict": getattr(track_rec, 'add_idt_ict', 0) or 0
                })

        has_tracked = len(previous_data_list) > 0
        tracked_data = previous_data_list[0] if has_tracked else None

        return jsonify({
            "success": True,
            "has_tracked": has_tracked,
            "count": len(previous_data_list),
            "data": previous_data_list,
            "tracked_data": tracked_data
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/add-ecc-state', methods=['POST'])
def api_add_ecc_state():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    try:
        data = request.get_json()
        item_id = data.get("item_id")
        scale = (data.get("scale") or "").strip()
        
        # Unit / Division Name
        bbf_division = (data.get("bbf_division") or "").strip()
        if user_role == "division_admin":
            bbf_division = session.get("username", "").strip()

        # Auth & Stock fields
        unit_auth = data.get("unit_auth") if data.get("unit_auth") is not None else data.get("auth")
        auth_auth = data.get("auth_auth") or unit_auth
        auth_res = data.get("auth_res") or 0
        
        stock_ser = data.get("stock_ser") if data.get("stock_ser") is not None else data.get("ser")
        stock_pws = data.get("stock_pws") if data.get("stock_pws") is not None else data.get("pws")
        
        # Additional Fields
        add_knd = data.get("add_knd")
        add_tn_model = data.get("add_tn_model")
        add_n_area_otg = data.get("add_n_area_otg")
        add_idt_ict = data.get("add_idt_ict")
        add_remarks_ro_bal = data.get("add_remarks_ro_bal")
        
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
            
            bbf_ser_val = int(data.get("bbf_ser") or 0)
            bbf_pws_val = int(data.get("bbf_pws") or 0)
            bbf_total_val = bbf_ser_val + bbf_pws_val
            bbf_comd_val = int(data.get("bbf_comd")) if data.get("bbf_comd") is not None and data.get("bbf_comd") != "" else None
            bbf_ihq_val = int(data.get("bbf_ihq")) if data.get("bbf_ihq") is not None and data.get("bbf_ihq") != "" else None
            
            recd_ser_val = int(data.get("recd_ser") or 0)
            recd_pws_val = int(data.get("recd_pws") or 0)
            recd_total_val = recd_ser_val + recd_pws_val
            
            issd_ser_val = int(data.get("issd_ser") or 0)
            issd_pws_val = int(data.get("issd_pws") or 0)
            issd_total_val = issd_ser_val + issd_pws_val
            
            stock_ser_val = int(stock_ser or 0)
            stock_pws_val = int(stock_pws or 0)
            stock_total_val = stock_ser_val + stock_pws_val
            stock_comd_val = int(data.get("stock_comd")) if data.get("stock_comd") is not None and data.get("stock_comd") != "" else None
            stock_ihq_val = int(data.get("stock_ihq")) if data.get("stock_ihq") is not None and data.get("stock_ihq") != "" else None
            
            add_knd_val = int(add_knd or 0)
            add_tn_model_val = int(add_tn_model or 0)
            add_n_area_otg_val = int(add_n_area_otg or 0)
            add_idt_ict_val = int(add_idt_ict or 0)
            add_remarks_ro_bal_val = int(add_remarks_ro_bal or 0)
            
            tps_val = int(data.get("tps") or 0)
            deficiency_val = unit_auth_val - stock_total_val
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "All input values (except scale) must be numbers."}), 400
            
        # Verify item exists in DB
        item_exists = ScmeItems.query.get(item_id_val)
        if not item_exists:
            return jsonify({"success": False, "message": "Selected Item does not exist."}), 400

        # Save/Update in TrackUnitItems table
        issue_count_val = int(data.get("issue_count") or 0)
        held_delta = issue_count_val if issue_count_val > 0 else stock_total_val

        # FOD Stock Availability Validation (check if stock exists in fod_stock_table)
        from sqlalchemy import func
        fod_total = db.session.query(func.sum(FodStock.quantity)).filter_by(item_id=item_id_val).scalar() or 0
        fod_ser = db.session.query(func.sum(FodStock.ser)).filter_by(item_id=item_id_val).scalar() or 0
        fod_pws = db.session.query(func.sum(FodStock.pws)).filter_by(item_id=item_id_val).scalar() or 0

        if fod_total <= 0:
            return jsonify({
                "success": False,
                "message": f"Item Not Available — '{item_exists.item_name}' has no stock. Please add stock via Add Stock page first."
            }), 400

        if stock_ser_val > fod_ser:
            return jsonify({
                "success": False,
                "message": f"Entered SER quantity ({stock_ser_val}) exceeds Available SER Stock ({fod_ser}) for item '{item_exists.item_name}'!"
            }), 400

        if stock_pws_val > fod_pws:
            return jsonify({
                "success": False,
                "message": f"Entered PWS quantity ({stock_pws_val}) exceeds Available PWS Stock ({fod_pws}) for item '{item_exists.item_name}'!"
            }), 400

        available_qty = fod_total
        if held_delta > available_qty:
            return jsonify({
                "success": False,
                "message": f"Issue quantity ({held_delta}) cannot exceed Available Stock ({available_qty}) for item '{item_exists.item_name}'!"
            }), 400

        now_dt = datetime.now(timezone.utc) if hasattr(timezone, 'utc') else datetime.utcnow()
        now_local = datetime.now()
        first_day_of_current_month = datetime(now_local.year, now_local.month, 1)

        # Query existing records for this unit & item
        all_recs = TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)) == bbf_division.lower().strip(),
            TrackUnitItems.item_id == item_id_val
        ).all()

        # Sync scale & auth across existing TrackUnitItems and ScmeIssuedItems/ItemAuth
        for r in all_recs:
            if scale:
                r.scale = scale
            if unit_auth_val >= 0:
                r.auth = unit_auth_val

        issued_rec = ScmeIssuedItems.query.filter(
            func.lower(func.trim(ScmeIssuedItems.unit_name)) == bbf_division.lower().strip(),
            ScmeIssuedItems.item_id == item_id_val
        ).first()
        if issued_rec:
            if scale:
                issued_rec.scale = scale
            if unit_auth_val >= 0:
                issued_rec.unit_authorized = unit_auth_val

        # Update or create ItemAuth record
        auth_rec = ItemAuth.query.filter(
            func.lower(func.trim(ItemAuth.unit_name)) == bbf_division.lower().strip(),
            ItemAuth.item_id == item_id_val
        ).first()
        if auth_rec:
            auth_rec.auth = unit_auth_val
        else:
            auth_rec = ItemAuth(unit_name=bbf_division, item_id=item_id_val, auth=unit_auth_val)
            db.session.add(auth_rec)
        
        current_month_rec = None
        for r in all_recs:
            rec_dt = r.issued_at
            if rec_dt:
                rec_naive = rec_dt.astimezone(timezone.utc).replace(tzinfo=None) if rec_dt.tzinfo else rec_dt
                if rec_naive >= first_day_of_current_month:
                    current_month_rec = r
                    break

        if current_month_rec:
            # SAME UNIT, ITEM, & MONTH EXISTS -> ACCUMULATE / SUM VALUES INTO EXISTING ROW
            current_month_rec.auth = unit_auth_val
            if scale:
                current_month_rec.scale = scale
            current_month_rec.available_res = (current_month_rec.available_res or 0) + held_delta
            current_month_rec.available_ser = (current_month_rec.available_ser or 0) + stock_ser_val
            current_month_rec.available_pws = (current_month_rec.available_pws or 0) + stock_pws_val
            current_month_rec.held = current_month_rec.calc_held()
            current_month_rec.add_knd = (current_month_rec.add_knd or 0) + add_knd_val
            current_month_rec.add_tn_model = (current_month_rec.add_tn_model or 0) + add_tn_model_val
            current_month_rec.add_n_area_otg = (current_month_rec.add_n_area_otg or 0) + add_n_area_otg_val
            current_month_rec.add_idt_ict = (current_month_rec.add_idt_ict or 0) + add_idt_ict_val
            current_month_rec.issued_at = now_dt
        else:
            # NO RECORD FOR CURRENT MONTH -> INSERT NEW ROW
            new_rec = TrackUnitItems(
                unit_name=bbf_division,
                item_id=item_id_val,
                scale=scale,
                auth=unit_auth_val,
                held=(stock_ser_val + stock_pws_val),
                ser=0,
                pws=0,
                available_res=held_delta,
                available_ser=stock_ser_val,
                available_pws=stock_pws_val,
                issued_at=now_dt,
                add_knd=add_knd_val,
                add_tn_model=add_tn_model_val,
                add_n_area_otg=add_n_area_otg_val,
                add_idt_ict=add_idt_ict_val
            )
            db.session.add(new_rec)

        # Record Transaction entry in transactions table
        trans_ser = stock_ser_val if stock_ser_val > 0 else held_delta
        trans_pws = stock_pws_val
        if trans_ser > 0 or trans_pws > 0:
            trans_rec = Transactions(
                issued_by=session.get("username") or "2_FOD",
                received_by=bbf_division,
                item_id=item_id_val,
                ser=trans_ser,
                pws=trans_pws,
                scale=scale,
                timestamp=now_dt
            )
            db.session.add(trans_rec)

        # Deduct issued SER and PWS from FOD Stock table
        rem_ser_to_deduct = stock_ser_val
        rem_pws_to_deduct = stock_pws_val
        if rem_ser_to_deduct == 0 and rem_pws_to_deduct == 0 and held_delta > 0:
            rem_ser_to_deduct = held_delta

        fod_records = FodStock.query.filter_by(item_id=item_id_val).order_by(FodStock.created_at.asc(), FodStock.id.asc()).all()

        for fod in fod_records:
            if rem_ser_to_deduct > 0 and (fod.ser or 0) > 0:
                deduct_ser = min(fod.ser, rem_ser_to_deduct)
                fod.ser -= deduct_ser
                rem_ser_to_deduct -= deduct_ser

            if rem_ser_to_deduct > 0 and (fod.pws or 0) > 0 and stock_ser_val == 0:
                deduct_pws_fallback = min(fod.pws, rem_ser_to_deduct)
                fod.pws -= deduct_pws_fallback
                rem_ser_to_deduct -= deduct_pws_fallback

            if rem_pws_to_deduct > 0 and (fod.pws or 0) > 0:
                deduct_pws = min(fod.pws, rem_pws_to_deduct)
                fod.pws -= deduct_pws
                rem_pws_to_deduct -= deduct_pws

            fod.quantity = (fod.ser or 0) + (fod.pws or 0)

            if rem_ser_to_deduct <= 0 and rem_pws_to_deduct <= 0:
                break

        db.session.commit()
            
        # Log action
        log_entry = ActionLog(
            user_id=session.get("user_id"),
            username=session.get("username", "Unknown"),
            role=session.get("role", "scme"),
            action_type="CREATE",
            module="ECC",
            details=f"Recorded unit item state in TrackUnitItems for Item: '{item_exists.item_name}', Division: {bbf_division}"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        target_rec = current_month_rec if current_month_rec else new_rec
        
        return jsonify({
            "success": True,
            "message": "ECC monthly state recorded & updated in TrackUnitItems successfully.",
            "state": {
                "id": target_rec.id if target_rec else 0,
                "item_name": item_exists.item_name,
                "scale": scale,
                "bbf_division": bbf_division,
                "auth_total": unit_auth_val,
                "bbf_total": bbf_total_val,
                "recd_total": recd_total_val,
                "issd_total": issd_total_val,
                "stock_total": stock_total_val,
                "deficiency": deficiency_val,
                "created_at": datetime.now().strftime('%d %b %Y, %H:%M')
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/ecc-state/<int:state_id>', methods=['PUT', 'DELETE'])
def api_ecc_state_actions(state_id):
    if "user_id" not in session or session.get("role") != "scme":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    record = TrackUnitItems.query.get(state_id)
    if not record:
        return jsonify({"success": False, "message": "Record not found."}), 404
        
    if request.method == 'DELETE':
        try:
            item_name = record.item.item_name if record.item else f"Item ID {record.item_id}"
            div_name = record.unit_name
            
            db.session.delete(record)
            
            # Log action
            log_entry = ActionLog(
                user_id=session.get("user_id"),
                username=session.get("username", "Unknown"),
                role=session.get("role", "scme"),
                action_type="DELETE",
                module="ECC",
                details=f"Deleted TrackUnitItems record for Item: '{item_name}', Division: {div_name}"
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


@scme_bp.route('/add-stock', methods=['GET', 'POST'])
def add_stock():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return redirect("/auth/login")

    # Ensure table exists
    try:
        db.create_all()
    except Exception:
        pass

    if request.method == 'POST':
        voucher_no = request.form.get('voucher_no', '').strip()
        category = request.form.get('category', '').strip()
        item_id = request.form.get('item_id', type=int)
        pws = request.form.get('pws', type=int, default=0) or 0
        ser = request.form.get('ser', type=int, default=0) or 0
        quantity = ser + pws
        source = request.form.get('source', '').strip()  # Depo / LP
        stock_type = request.form.get('type', '').strip()  # RES / IHQ / CMD

        if not voucher_no or not category or not item_id or not source or not stock_type:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('scme.add_stock'))

        new_stock = FodStock(
            voucher_no=voucher_no,
            category=category,
            item_id=item_id,
            quantity=quantity,
            source=source,
            pws=pws,
            ser=ser,
            type=stock_type
        )
        db.session.add(new_stock)

        # Log action if ActionLog exists
        try:
            log_entry = ActionLog(
                user_id=session.get("user_id"),
                username=session.get("username", "Unknown"),
                role=session.get("role", "scme"),
                action_type="CREATE",
                module="FOD Stock",
                details=f"Added FOD Stock: Voucher {voucher_no}, Qty {quantity}, Type {stock_type}"
            )
            db.session.add(log_entry)
        except Exception:
            pass

        db.session.commit()
        flash("Stock entry saved successfully to fod_stock_table!", "success")
        return redirect(url_for('scme.add_stock'))

    items = ScmeItems.query.order_by(ScmeItems.item_name).all()
    categories = db.session.query(ScmeItems.category).distinct().all()
    category_list = [c[0] for c in categories if c[0]]
    if not category_list:
        category_list = ['CAT-I', 'CAT-II']

    from sqlalchemy import func
    stock_totals = db.session.query(
        FodStock.item_id,
        func.sum(FodStock.quantity).label('total_qty'),
        func.sum(FodStock.ser).label('total_ser'),
        func.sum(FodStock.pws).label('total_pws'),
        func.max(FodStock.created_at).label('last_updated')
    ).group_by(FodStock.item_id).all()

    current_stock_summary = {}
    for st in stock_totals:
        current_stock_summary[st.item_id] = {
            "total_qty": int(st.total_qty or 0),
            "total_ser": int(st.total_ser or 0),
            "total_pws": int(st.total_pws or 0),
            "last_updated": st.last_updated.strftime('%d %b %Y, %H:%M') if st.last_updated else ''
        }

    current_stock_list = []
    total_fod_qty = 0
    total_fod_ser = 0
    total_fod_pws = 0

    for item in items:
        sum_data = current_stock_summary.get(item.id)
        if sum_data and sum_data["total_qty"] > 0:
            total_fod_qty += sum_data["total_qty"]
            total_fod_ser += sum_data["total_ser"]
            total_fod_pws += sum_data["total_pws"]
            current_stock_list.append({
                "item_id": item.id,
                "item_name": item.item_name,
                "category": item.category,
                "total_qty": sum_data["total_qty"],
                "total_ser": sum_data["total_ser"],
                "total_pws": sum_data["total_pws"],
                "last_updated": sum_data["last_updated"]
            })

    recent_stocks = FodStock.query.order_by(FodStock.created_at.desc(), FodStock.id.desc()).all()

    return render_template(
        '/scme_dashboard/add_stock.html',
        items=items,
        categories=category_list,
        recent_stocks=recent_stocks,
        current_stock_summary=current_stock_summary,
        current_stock_list=current_stock_list,
        total_fod_qty=total_fod_qty,
        total_fod_ser=total_fod_ser,
        total_fod_pws=total_fod_pws
    )
@scme_bp.route('/current-stock', methods=['GET'])
def current_stock_page():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return redirect("/auth/login")

    from sqlalchemy import func
    items = ScmeItems.query.order_by(ScmeItems.item_name).all()
    categories = db.session.query(ScmeItems.category).distinct().all()
    category_list = [c[0] for c in categories if c[0]]
    if not category_list:
        category_list = ['CAT-I', 'CAT-II']

    stock_totals = db.session.query(
        FodStock.item_id,
        func.sum(FodStock.quantity).label('total_qty'),
        func.sum(FodStock.ser).label('total_ser'),
        func.sum(FodStock.pws).label('total_pws'),
        func.max(FodStock.created_at).label('last_updated')
    ).group_by(FodStock.item_id).all()

    current_stock_summary = {}
    for st in stock_totals:
        current_stock_summary[st.item_id] = {
            "total_qty": int(st.total_qty or 0),
            "total_ser": int(st.total_ser or 0),
            "total_pws": int(st.total_pws or 0),
            "last_updated": st.last_updated.strftime('%d %b %Y, %H:%M') if st.last_updated else ''
        }

    current_stock_list = []
    total_fod_qty = 0
    total_fod_ser = 0
    total_fod_pws = 0
    items_with_stock_count = 0

    for item in items:
        sum_data = current_stock_summary.get(item.id)
        if sum_data and (sum_data["total_ser"] > 0 or sum_data["total_pws"] > 0):
            total_fod_qty += sum_data["total_qty"]
            total_fod_ser += sum_data["total_ser"]
            total_fod_pws += sum_data["total_pws"]
            items_with_stock_count += 1

            current_stock_list.append({
                "item_id": item.id,
                "item_name": item.item_name,
                "category": item.category,
                "total_qty": sum_data["total_qty"],
                "total_ser": sum_data["total_ser"],
                "total_pws": sum_data["total_pws"],
                "last_updated": sum_data["last_updated"]
            })

    return render_template(
        '/scme_dashboard/current_stock.html',
        items=items,
        categories=category_list,
        current_stock_list=current_stock_list,
        total_fod_qty=total_fod_qty,
        total_fod_ser=total_fod_ser,
        total_fod_pws=total_fod_pws,
        items_with_stock_count=items_with_stock_count
    )


@scme_bp.route('/api/current-stock', methods=['GET'])
def api_get_current_stock():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    from sqlalchemy import func
    items = ScmeItems.query.order_by(ScmeItems.item_name).all()
    stock_totals = db.session.query(
        FodStock.item_id,
        func.sum(FodStock.quantity).label('total_qty'),
        func.sum(FodStock.ser).label('total_ser'),
        func.sum(FodStock.pws).label('total_pws'),
        func.max(FodStock.created_at).label('last_updated')
    ).group_by(FodStock.item_id).all()

    stock_summary = {}
    for st in stock_totals:
        stock_summary[st.item_id] = {
            "total_qty": int(st.total_qty or 0),
            "total_ser": int(st.total_ser or 0),
            "total_pws": int(st.total_pws or 0),
            "last_updated": st.last_updated.strftime('%d %b %Y, %H:%M') if st.last_updated else 'N/A'
        }

    data = []
    total_qty_all = 0
    total_ser_all = 0
    total_pws_all = 0

    for item in items:
        sum_data = stock_summary.get(item.id)
        if sum_data and sum_data["total_qty"] > 0:
            total_qty_all += sum_data["total_qty"]
            total_ser_all += sum_data["total_ser"]
            total_pws_all += sum_data["total_pws"]
            data.append({
                "item_id": item.id,
                "item_name": item.item_name,
                "category": item.category,
                "total_qty": sum_data["total_qty"],
                "total_ser": sum_data["total_ser"],
                "total_pws": sum_data["total_pws"],
                "last_updated": sum_data["last_updated"]
            })

    return jsonify({
        "success": True,
        "items": data,
        "totals": {
            "total_items": len(data),
            "total_qty": total_qty_all,
            "total_ser": total_ser_all,
            "total_pws": total_pws_all
        }
    })


@scme_bp.route('/api/available-stock/<int:item_id>', methods=['GET'])
def api_get_available_stock(item_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    item = ScmeItems.query.get(item_id)
    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404

    from sqlalchemy import func
    fod_total = db.session.query(func.sum(FodStock.quantity)).filter_by(item_id=item_id).scalar() or 0
    ser_total = db.session.query(func.sum(FodStock.ser)).filter_by(item_id=item_id).scalar() or 0
    pws_total = db.session.query(func.sum(FodStock.pws)).filter_by(item_id=item_id).scalar() or 0
    available_qty = fod_total if fod_total > 0 else None

    return jsonify({
        "success": True,
        "item_id": item_id,
        "item_name": item.item_name,
        "has_fod_stock": (fod_total > 0),
        "fod_total": fod_total,
        "available_qty": available_qty,
        "ser_total": ser_total,
        "pws_total": pws_total
    })


@scme_bp.route('/api/set-item-auth', methods=['POST'])
def api_set_item_auth():
    if "user_id" not in session or session.get("role") not in ["scme", "super_admin", "division_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json() or {}
        unit_name = (data.get("unit_name") or "").strip()
        item_id = data.get("item_id")
        auth_val = data.get("auth")

        if not unit_name or not item_id or auth_val is None:
            return jsonify({"success": False, "message": "Division, Item, and Authorized Quantity (AUTH) are required."}), 400

        try:
            auth_int = int(auth_val)
            if auth_int < 0:
                return jsonify({"success": False, "message": "AUTH cannot be negative."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "AUTH must be a valid integer."}), 400

        item_exists = ScmeItems.query.get(item_id)
        if not item_exists:
            return jsonify({"success": False, "message": "Selected Item does not exist."}), 400

        # Update/Save ONLY in dedicated ItemAuth table
        item_auth_rec = ItemAuth.query.filter_by(unit_name=unit_name, item_id=item_id).first()
        if item_auth_rec:
            item_auth_rec.auth = auth_int
        else:
            item_auth_rec = ItemAuth(unit_name=unit_name, item_id=item_id, auth=auth_int)
            db.session.add(item_auth_rec)

        db.session.commit()

        try:
            log_entry = ActionLog(
                user_id=session.get("user_id"),
                username=session.get("username", "Unknown"),
                role=session.get("role", "scme"),
                action_type="UPDATE",
                module="SCME",
                details=f"Set Item Authorization (AUTH={auth_int}) for Item: '{item_exists.item_name}', Division: {unit_name}"
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"Successfully set AUTH = {auth_int} for item '{item_exists.item_name}' under {unit_name}.",
            "data": {
                "unit_name": unit_name,
                "item_id": item_id,
                "item_name": item_exists.item_name,
                "auth": auth_int
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/get-item-auth', methods=['GET'])
def api_get_item_auth():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    unit_name = (request.args.get("unit_name") or "").strip()
    item_id = request.args.get("item_id", type=int)

    if not unit_name or not item_id:
        return jsonify({"success": True, "auth": 0})

    # Read strictly from ItemAuth table ONLY
    auth_rec = ItemAuth.query.filter_by(unit_name=unit_name, item_id=item_id).first()
    auth_val = auth_rec.auth if (auth_rec and auth_rec.auth is not None) else 0

    return jsonify({
        "success": True,
        "unit_name": unit_name,
        "item_id": item_id,
        "auth": auth_val
    })