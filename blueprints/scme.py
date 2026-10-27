from imports import *
from extensions import db
from models import LoginUser, ActionLog, Notification
from models.our_items import OurItems, ItemRequestTable, ScmeItems, Units, Divs, ScmeIssuedItems, TrackUnitItems, FodStock, ItemAuth, Transactions, UnitTpsStock, Strength, ArmyPersonnel, CondemnationRequest
from models.org_ladder import OrgLadder
from validation import has_special_characters
from datetime import datetime, timezone
from sqlalchemy import func, or_

scme_bp = Blueprint("scme", __name__, url_prefix='/scme')


def normalize_div_name(name):
    if not name:
        return ""
    s = name.strip().upper()
    return s.replace(' ', '_')


def resolve_parent_dou_global(u_name, all_orgs=None, user_org_map=None):
    if not u_name:
        return ""
    s_name = u_name.strip()
    l_name = s_name.lower()

    if "dou" in l_name or "fod" in l_name:
        return normalize_div_name(s_name)

    if all_orgs is None:
        all_orgs = OrgLadder.query.all()
    org_by_id = {o.id: o for o in all_orgs}
    org_by_name = {o.name.strip().lower(): o for o in all_orgs if o.name}

    if user_org_map is None:
        all_users = LoginUser.query.all()
        user_org_map = {u.username.strip().lower(): u.org_id for u in all_users if u.username and u.org_id}

    org_id = user_org_map.get(l_name)
    if not org_id and l_name in org_by_name:
        org_id = org_by_name[l_name].id

    if org_id:
        curr = org_by_id.get(org_id)
        while curr:
            c_name = (curr.name or "").strip()
            c_type = (curr.type or "").strip().lower()
            if c_type in ["division", "dou"] or "dou" in c_name.lower() or "fod" in c_name.lower():
                return normalize_div_name(c_name)
            if not curr.parent_id:
                break
            curr = org_by_id.get(curr.parent_id)

    return normalize_div_name(s_name)


def get_parent_dou_tps_map():
    """
    Queries UnitTpsStock for records where tps_ser > 0 or tps_pws > 0.
    Maps child units to parent DOU via OrgLadder / LoginUser / name.
    Returns tuple: (parent_tps_map, item_total_tps_map)
      parent_tps_map: { (unit_key, item_id): tps_sum }
      item_total_tps_map: { item_id: tps_sum_across_all_units }
    """
    all_orgs = OrgLadder.query.all()
    all_users = LoginUser.query.all()
    user_org_map = {u.username.strip().lower(): u.org_id for u in all_users if u.username and u.org_id}

    def resolve_parent_dou(u_name):
        return resolve_parent_dou_global(u_name, all_orgs, user_org_map)

    tps_recs = UnitTpsStock.query.filter(
        (UnitTpsStock.tps_ser > 0) | (UnitTpsStock.tps_pws > 0)
    ).all()

    parent_tps_map = {}
    item_total_tps_map = {}

    for r in tps_recs:
        cnt = (r.tps_ser or 0) + (r.tps_pws or 0)
        if cnt <= 0:
            continue

        item_total_tps_map[r.item_id] = item_total_tps_map.get(r.item_id, 0) + cnt

        # 1. Parent DOU keys
        p_dou_norm = resolve_parent_dou(r.unit_name)
        if p_dou_norm:
            p1 = p_dou_norm.lower().strip()
            parent_tps_map[(p1, r.item_id)] = parent_tps_map.get((p1, r.item_id), 0) + cnt
            p1_norm = normalize_div_name(p_dou_norm).lower().strip()
            if p1_norm != p1:
                parent_tps_map[(p1_norm, r.item_id)] = parent_tps_map.get((p1_norm, r.item_id), 0) + cnt

        # 2. Direct Unit keys
        if r.unit_name:
            u1 = r.unit_name.lower().strip()
            if (u1, r.item_id) not in parent_tps_map:
                parent_tps_map[(u1, r.item_id)] = cnt
            u1_norm = normalize_div_name(r.unit_name).lower().strip()
            if (u1_norm, r.item_id) not in parent_tps_map:
                parent_tps_map[(u1_norm, r.item_id)] = cnt

    return parent_tps_map, item_total_tps_map


def ensure_transactions_type_column():
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE transactions ADD COLUMN `type` VARCHAR(50) NULL;"))
            conn.commit()
    except Exception:
        pass


@scme_bp.route('/')
def scme_home():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return redirect("/auth/login")

    ensure_transactions_type_column()
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
            norm_div = normalize_div_name(rec.unit_name or '').replace('_', ' ')
            self.bbf_division = norm_div
            self.unit_name = norm_div
            self.item = rec.item
            self.scale = getattr(rec, 'scale', None) or "N/A"
            
            # Fetch AUTH from ItemAuth (checking whole_auth/whole_res first, fallback to unit auth)
            item_whole_auth_rec = ItemAuth.query.filter(
                ItemAuth.item_id == rec.item_id,
                (ItemAuth.whole_auth.isnot(None)) | (ItemAuth.whole_res.isnot(None))
            ).order_by(ItemAuth.id.desc()).first()

            auth_rec = ItemAuth.query.filter(
                func.lower(func.trim(ItemAuth.unit_name)) == (rec.unit_name or '').lower().strip(),
                ItemAuth.item_id == rec.item_id
            ).first()
            unit_auth_val = auth_rec.auth if (auth_rec and auth_rec.auth is not None) else (rec.auth or 0)

            if item_whole_auth_rec:
                self.auth_auth = item_whole_auth_rec.whole_auth or 0
                self.auth_res = item_whole_auth_rec.whole_res or 0
                self.auth_total = self.auth_auth + self.auth_res
                self.unit_auth = unit_auth_val
                self.has_whole_auth = True
                if item_whole_auth_rec.scale:
                    self.scale = item_whole_auth_rec.scale
            else:
                self.auth_auth = unit_auth_val
                self.auth_res = 0
                self.auth_total = unit_auth_val
                self.unit_auth = unit_auth_val
                self.has_whole_auth = False
            
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
            self.recd_comd = 0
            self.recd_ihq = 0
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
            self.tps = 0
            self.deficiency = self.unit_auth - self.stock_total
            self.created_at = rec.issued_at

    # Fetch division names from LoginUser (role == division_admin) and Divs table
    div_users = LoginUser.query.filter(LoginUser.role == 'division_admin').order_by(LoginUser.username).all()
    div_records = Divs.query.order_by(Divs.name).all()

    # Sync missing division_admin users into Divs table if needed
    for u in div_users:
        if u.username and u.username.strip():
            u_clean = u.username.strip()
            if not any(d.name and d.name.strip().lower() == u_clean.lower() for d in div_records):
                new_div = Divs(name=u_clean, authorized_strength=0, posted_strength=0)
                db.session.add(new_div)
                div_records.append(new_div)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    all_div_admins = []
    seen_divs = set()
    for u in div_users:
        un = (u.username or '').strip()
        norm_u = un.lower().replace('_', ' ')
        if un and norm_u not in seen_divs:
            seen_divs.add(norm_u)
            all_div_admins.append(un)
    for d in div_records:
        dn = (d.name or '').strip()
        norm_d = dn.lower().replace('_', ' ')
        if dn and norm_d not in seen_divs:
            seen_divs.add(norm_d)
            all_div_admins.append(dn)

    def div_sort_key(name):
        is_619 = 0 if '619' in str(name) else 1
        nums = ''.join(c for c in name if c.isdigit())
        return (is_619, 0 if nums else 1, int(nums) if nums else 0, name.upper())

    all_div_admins.sort(key=div_sort_key)
    if is_div_admin and user_div:
        all_div_admins = [user_div]
        div_admin_names = [user_div]
    else:
        div_admin_names = all_div_admins

    track_query = TrackUnitItems.query
    if is_div_admin and user_div:
        track_query = track_query.filter(TrackUnitItems.unit_name == user_div)
    else:
        if div_admin_names:
            track_query = track_query.filter(TrackUnitItems.unit_name.in_(div_admin_names))

    track_records = track_query.order_by(TrackUnitItems.issued_at.desc(), TrackUnitItems.id.desc()).all()
    # Filter track_records strictly to items with type == 'ecc'
    track_records = [tr for tr in track_records if tr.item and (tr.item.type or '').lower() == 'ecc']
    
    # Group track_records by unique (unit_name, item_id) to eliminate duplicate rows per item
    grouped_track_map = {}
    for rec in track_records:
        u_key = (rec.unit_name or '').lower().strip()
        key = (u_key, rec.item_id)
        if key not in grouped_track_map:
            grouped_track_map[key] = []
        grouped_track_map[key].append(rec)

    all_catalog_items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').all()
    for cat_item in all_catalog_items:
        if ('2 fod', cat_item.id) not in grouped_track_map:
            dummy_rec = TrackUnitItems(
                unit_name='2 FOD',
                item_id=cat_item.id,
                ser=0,
                pws=0,
                auth=0,
                issued_at=first_day_of_current_month
            )
            dummy_rec.item = cat_item
            grouped_track_map[('2 fod', cat_item.id)] = [dummy_rec]

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
        iss_by = (t.issued_by or '').lower().strip().replace('_', ' ')
        rec_by = (t.received_by or '').lower().strip().replace('_', ' ')
        if iss_by == rec_by or rec_by in ['2 fod', '2_fod']:
            continue
        if '2 fod' in iss_by or '2_fod' in iss_by or iss_by in ['scme', 'admin', 'super_admin']:
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
        iss_by = (t.issued_by or '').lower().strip().replace('_', ' ')
        rec_by = (t.received_by or '').lower().strip().replace('_', ' ')
        if iss_by == rec_by or rec_by in ['2 fod', '2_fod']:
            continue
        if '2 fod' in iss_by or '2_fod' in iss_by or iss_by in ['scme', 'admin', 'super_admin']:
            r_key = (t.received_by or '').lower().strip()
            key = (r_key, t.item_id)
            if key not in issued_this_month_map:
                issued_this_month_map[key] = {'ser': 0, 'pws': 0}
            issued_this_month_map[key]['ser'] += (t.ser or 0)
            issued_this_month_map[key]['pws'] += (t.pws or 0)

    # ── QTY RECD DURING MONTH: Query Transactions table where received_by == '2 FOD' for current month ──
    fod_recd_trans = Transactions.query.filter(
        func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod']),
        Transactions.timestamp >= first_day_of_current_month,
        Transactions.timestamp < first_day_next_month
    ).all()

    fod_recd_map = {}
    for t in fod_recd_trans:
        if t.item_id not in fod_recd_map:
            fod_recd_map[t.item_id] = {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0}
        st_type = (t.type or '').strip().upper()
        if st_type in ['CMD', 'COMD']:
            fod_recd_map[t.item_id]['comd'] += int(t.ser or 0) + int(t.pws or 0)
        elif st_type == 'IHQ':
            fod_recd_map[t.item_id]['ihq'] += int(t.ser or 0) + int(t.pws or 0)
        else:
            fod_recd_map[t.item_id]['ser'] += int(t.ser or 0)
            fod_recd_map[t.item_id]['pws'] += int(t.pws or 0)

    # ── BBF DATA FROM TRANSACTIONS TABLE (timestamp < first_day_of_current_month for 2 FOD: Inward Receipts minus Outward Issues) ──
    fod_in_bbf = Transactions.query.filter(
        func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod']),
        Transactions.timestamp < first_day_of_current_month
    ).all()

    fod_out_bbf = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)).in_(['2 fod', '2_fod', 'scme', 'admin', 'super_admin']),
        ~func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod']),
        Transactions.timestamp < first_day_of_current_month
    ).all()

    fod_bbf_map = {}
    for t in fod_in_bbf:
        if t.item_id not in fod_bbf_map:
            fod_bbf_map[t.item_id] = {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0}
        st_type = (t.type or '').strip().upper()
        if st_type in ['CMD', 'COMD']:
            fod_bbf_map[t.item_id]['comd'] += int(t.ser or 0) + int(t.pws or 0)
        elif st_type == 'IHQ':
            fod_bbf_map[t.item_id]['ihq'] += int(t.ser or 0) + int(t.pws or 0)
        else:
            fod_bbf_map[t.item_id]['ser'] += int(t.ser or 0)
            fod_bbf_map[t.item_id]['pws'] += int(t.pws or 0)

    for t in fod_out_bbf:
        if t.item_id not in fod_bbf_map:
            fod_bbf_map[t.item_id] = {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0}
        st_type = (t.type or '').strip().upper()
        if st_type in ['CMD', 'COMD']:
            fod_bbf_map[t.item_id]['comd'] = max(0, fod_bbf_map[t.item_id]['comd'] - (int(t.ser or 0) + int(t.pws or 0)))
        elif st_type == 'IHQ':
            fod_bbf_map[t.item_id]['ihq'] = max(0, fod_bbf_map[t.item_id]['ihq'] - (int(t.ser or 0) + int(t.pws or 0)))
        else:
            fod_bbf_map[t.item_id]['ser'] = max(0, fod_bbf_map[t.item_id]['ser'] - int(t.ser or 0))
            fod_bbf_map[t.item_id]['pws'] = max(0, fod_bbf_map[t.item_id]['pws'] - int(t.pws or 0))

    parent_dou_tps_map, item_total_tps_map = get_parent_dou_tps_map()

    # ── STK HELD FROM FOD_STOCK_TABLE ──
    fod_stk_held = db.session.query(
        FodStock.item_id,
        FodStock.type,
        func.sum(FodStock.ser).label('sum_ser'),
        func.sum(FodStock.pws).label('sum_pws'),
        func.sum(FodStock.quantity).label('sum_qty')
    ).group_by(FodStock.item_id, FodStock.type).all()

    fod_stk_held_map = {}
    for f in fod_stk_held:
        if f.item_id not in fod_stk_held_map:
            fod_stk_held_map[f.item_id] = {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0}
        st_type = (f.type or '').strip().upper()
        if st_type in ['CMD', 'COMD']:
            fod_stk_held_map[f.item_id]['comd'] += int(f.sum_qty or f.sum_ser or 0)
        elif st_type == 'IHQ':
            fod_stk_held_map[f.item_id]['ihq'] += int(f.sum_qty or f.sum_ser or 0)
        else:
            fod_stk_held_map[f.item_id]['ser'] += int(f.sum_ser or 0)
            fod_stk_held_map[f.item_id]['pws'] += int(f.sum_pws or 0)

    # ── STK HELD CONDEMNATION LOOKUP ──
    all_cond_track_recs = TrackUnitItems.query.filter(
        (TrackUnitItems.condemned_ser > 0) | (TrackUnitItems.condemned_pws > 0)
    ).all()

    div_condemned_map = {}
    unit_condemned_map = {}

    all_orgs_list = OrgLadder.query.all()
    all_users_list = LoginUser.query.all()
    user_org_map = {u.username.strip().lower(): u.org_id for u in all_users_list if u.username and u.org_id}

    for cr in all_cond_track_recs:
        c_ser = cr.condemned_ser or 0
        c_pws = cr.condemned_pws or 0
        if c_ser <= 0 and c_pws <= 0:
            continue
        iid = cr.item_id
        u_raw = (cr.unit_name or '').strip().lower()
        u_norm = normalize_div_name(cr.unit_name).strip().lower()

        for k_u in [u_raw, u_norm, u_raw.replace('_', ' '), u_norm.replace('_', ' ')]:
            if (k_u, iid) not in unit_condemned_map:
                unit_condemned_map[(k_u, iid)] = {'ser': 0, 'pws': 0, 'total': 0}
            unit_condemned_map[(k_u, iid)]['ser'] += c_ser
            unit_condemned_map[(k_u, iid)]['pws'] += c_pws
            unit_condemned_map[(k_u, iid)]['total'] += (c_ser + c_pws)

        p_div = resolve_parent_dou_global(cr.unit_name, all_orgs_list, user_org_map)
        if p_div:
            p_norm = p_div.strip().lower()
            p_space = p_norm.replace('_', ' ')
            for k_p in [p_norm, p_space]:
                if (k_p, iid) not in div_condemned_map:
                    div_condemned_map[(k_p, iid)] = {'ser': 0, 'pws': 0, 'total': 0}
                div_condemned_map[(k_p, iid)]['ser'] += c_ser
                div_condemned_map[(k_p, iid)]['pws'] += c_pws
                div_condemned_map[(k_p, iid)]['total'] += (c_ser + c_pws)

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

        # STOCK HELD: From TrackUnitItems
        tot_ser = sum((r.ser or 0) + (getattr(r, 'available_ser', 0) or 0) for r in group_recs)
        tot_pws = sum((r.pws or 0) + (getattr(r, 'available_pws', 0) or 0) for r in group_recs)
        tot_held_calc = sum(r.calc_held() for r in group_recs)
        raw_held = tot_held_calc if tot_held_calc > 0 else (tot_ser + tot_pws)

        u_norm = normalize_div_name(rec.unit_name or '').lower().strip()
        raw_u = (rec.unit_name or '').lower().strip()

        # Condemnation lookup for division & unit
        cond_info = div_condemned_map.get((u_norm, item_id))
        if not cond_info:
            cond_info = div_condemned_map.get((raw_u, item_id))
        if not cond_info:
            cond_info = unit_condemned_map.get((raw_u, item_id), {'ser': 0, 'pws': 0, 'total': 0})

        c_ser = cond_info['ser']
        c_pws = cond_info['pws']
        c_tot = cond_info['total']

        # HELD = HELD - (condemned_ser + condemned_pws)
        adapter.stock_ser   = max(0, tot_ser - c_ser)
        adapter.stock_pws   = max(0, tot_pws - c_pws)
        adapter.stock_total = max(0, raw_held - c_tot)
        adapter.condemned_ser = c_ser
        adapter.condemned_pws = c_pws
        adapter.condemned_total = c_tot

        tps_val = parent_dou_tps_map.get((u_norm, item_id))
        if tps_val is None:
            tps_val = parent_dou_tps_map.get((raw_u, item_id))
        if (tps_val is None or tps_val == 0) and (not is_div_admin or (user_div and user_div.strip().lower() in ['2 fod', '2_fod'])):
            tps_val = item_total_tps_map.get(item_id, 0)
        adapter.tps = tps_val or 0

        # ISSUED DURING MONTH: Real issuance data from transactions table (current month)
        issd_data = issued_this_month_map.get((u_key, item_id), {'ser': 0, 'pws': 0})
        adapter.issd_ser   = issd_data['ser']
        adapter.issd_pws   = issd_data['pws']
        adapter.issd_total = adapter.issd_ser + adapter.issd_pws

        # QTY RECD DURING MONTH & FOD DEPOT STOCK: Only for '2 FOD'
        if u_key == '2 fod':
            recd_data = fod_recd_map.get(item_id, {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0})
            adapter.recd_ser = recd_data['ser']
            adapter.recd_pws = recd_data['pws']
            adapter.recd_comd = recd_data.get('comd', 0)
            adapter.recd_ihq = recd_data.get('ihq', 0)
            adapter.recd_total = adapter.recd_ser + adapter.recd_pws + adapter.recd_comd + adapter.recd_ihq

            bbf_data = fod_bbf_map.get(item_id, {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0})
            adapter.bbf_ser += bbf_data['ser']
            adapter.bbf_pws += bbf_data['pws']
            adapter.bbf_comd += bbf_data['comd']
            adapter.bbf_ihq += bbf_data['ihq']
            adapter.bbf_total = adapter.bbf_ser + adapter.bbf_pws + adapter.bbf_comd + adapter.bbf_ihq

            stk_data = fod_stk_held_map.get(item_id, {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0})
            adapter.stock_ser = max(0, stk_data['ser'] - c_ser)
            adapter.stock_pws = max(0, stk_data['pws'] - c_pws)
            adapter.stock_comd = stk_data['comd']
            adapter.stock_ihq = stk_data['ihq']
            adapter.stock_total = max(0, (stk_data['ser'] + stk_data['pws'] + stk_data['comd'] + stk_data['ihq']) - c_tot)
        else:
            adapter.recd_ser = 0
            adapter.recd_pws = 0
            adapter.recd_total = 0

        adapter.deficiency  = adapter.unit_auth - adapter.stock_total

        ecc_states.append(adapter)

    def ecc_item_sort_key(adapter):
        item = adapter.item if hasattr(adapter, 'item') else None
        cat = (item.category if item else "") or ""
        cat_upper = cat.upper().replace(" ", "").replace("-", "")
        if "CAT1" in cat_upper or ("CATI" in cat_upper and "CATII" not in cat_upper):
            cat_rank = 1
        elif "CAT2" in cat_upper or "CATII" in cat_upper:
            cat_rank = 2
        else:
            cat_rank = 3
        item_name = (item.item_name if item else "") or ""
        unit_name = getattr(adapter, 'unit_name', "") or ""
        return (cat_rank, item_name.lower(), unit_name.lower())

    ecc_states.sort(key=ecc_item_sort_key)

    # ECC specific counts & datasets from TrackUnitItems
    total_ecc_items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').count()
    ecc_catalog_items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').all()
    ecc_catalog_items.sort(key=lambda item: (
        1 if ("CAT1" in (item.category or "").upper().replace(" ", "").replace("-", "") or ("CATI" in (item.category or "").upper().replace(" ", "").replace("-", "") and "CATII" not in (item.category or "").upper().replace(" ", "").replace("-", ""))) else (2 if ("CAT2" in (item.category or "").upper().replace(" ", "").replace("-", "") or "CATII" in (item.category or "").upper().replace(" ", "").replace("-", "")) else 3),
        (item.item_name or "").lower()
    ))
    
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
        defi_val = auth_val - held_val

        total_ecc_auth += auth_val
        total_ecc_held += held_val
        global_ecc_deficiency += max(0, defi_val)

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
            "condemned_ser": getattr(s, 'condemned_ser', 0) or 0,
            "condemned_pws": getattr(s, 'condemned_pws', 0) or 0,
            "tps": getattr(s, 'tps', 0) or 0,
            "deficiency": defi_val
        })
    # Ensure all division admins (DOUs) exist in ecc_chart_data for all ECC catalog items
    existing_chart_pairs = {
        (((d.get("division") or "").strip().lower()).replace('_', ' '), (d.get("item_name") or "").strip().lower())
        for d in ecc_chart_data
    }
    
    item_auth_all = ItemAuth.query.all()
    auth_lookup = {}
    for ia in item_auth_all:
        if ia.unit_name and ia.item_id:
            auth_lookup[(ia.unit_name.strip().lower(), ia.item_id)] = ia.auth or 0
            auth_lookup[(ia.unit_name.strip().lower().replace('_', ' '), ia.item_id)] = ia.auth or 0

    for div_name in all_div_admins:
        d_lower = div_name.strip().lower()
        d_norm_space = d_lower.replace('_', ' ')
        for cat_item in ecc_catalog_items:
            i_name = (cat_item.item_name or "").strip()
            if (d_norm_space, i_name.lower()) not in existing_chart_pairs:
                u_auth = auth_lookup.get((d_norm_space, cat_item.id), 0)
                ecc_chart_data.append({
                    "id": 0,
                    "division": div_name,
                    "item_name": i_name,
                    "category": cat_item.category or "CAT-I",
                    "scale": "1 per indl",
                    "auth_total": u_auth,
                    "unit_auth": u_auth,
                    "bbf_total": 0,
                    "recd_total": 0,
                    "issd_total": 0,
                    "stock_ser": 0,
                    "stock_pws": 0,
                    "stock_total": 0,
                    "condemned_ser": 0,
                    "condemned_pws": 0,
                    "tps": 0,
                    "deficiency": u_auth
                })
                existing_chart_pairs.add((d_lower, i_name.lower()))

    active_ecc_divisions = len(all_div_admins)

    # Build division_child_units_map and child units chart data for Item Analysis chart
    all_orgs = OrgLadder.query.all()
    division_child_units_map = {}
    unit_to_parent_div_map = {}

    for div_name in all_div_admins:
        d_clean = (div_name or '').strip()
        d_lower = d_clean.lower()
        d_space = d_lower.replace('_', ' ')

        # Find org ladder node matching div_name
        div_node = next((
            o for o in all_orgs 
            if o.name and (o.name.strip().lower() == d_lower or o.name.strip().lower() == d_space)
        ), None)

        child_units = []
        if div_node:
            def collect_child_units(node):
                collected = []
                for ch in (node.children or []):
                    ch_type = (ch.type or '').strip().lower()
                    if ch_type == 'unit' or not ch.children:
                        if ch.name and ch.name.strip():
                            collected.append(ch.name.strip())
                    else:
                        collected.extend(collect_child_units(ch))
                return collected

            child_units = collect_child_units(div_node)

        def u_sort_key(u):
            digits = ''.join(c for c in u if c.isdigit())
            return (int(digits) if digits else 9999, u.upper())

        child_units = sorted(list(dict.fromkeys(child_units)), key=u_sort_key)
        division_child_units_map[d_clean] = child_units
        if '_' in d_clean:
            division_child_units_map[d_clean.replace('_', ' ')] = child_units

        for cu in child_units:
            unit_to_parent_div_map[cu.lower().strip()] = d_clean

    # Fetch all child units' TrackUnitItems, ItemAuth, and dou_issued transactions
    all_child_unit_names = []
    for u_list in division_child_units_map.values():
        all_child_unit_names.extend(u_list)
    all_child_unit_names = list(set(all_child_unit_names))

    ecc_child_units_chart_data = []
    if all_child_unit_names:
        child_names_lower = [u.lower().strip() for u in all_child_unit_names]

        # 1. TrackUnitItems
        child_track_recs = TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)).in_(child_names_lower)
        ).all()
        child_track_recs = [tr for tr in child_track_recs if tr.item and (tr.item.type or '').lower() == 'ecc']

        # Group by (unit_name_lower, item_id)
        child_track_grouped = {}
        for tr in child_track_recs:
            u_k = (tr.unit_name or '').lower().strip()
            k = (u_k, tr.item_id)
            if k not in child_track_grouped:
                child_track_grouped[k] = []
            child_track_grouped[k].append(tr)

        # 2. ItemAuth
        child_auth_all = ItemAuth.query.filter(
            func.lower(func.trim(ItemAuth.unit_name)).in_(child_names_lower)
        ).all()
        child_auth_lookup = {
            (ia.unit_name.lower().strip(), ia.item_id): ia.auth or 0
            for ia in child_auth_all if ia.unit_name and ia.item_id
        }

        # 3. Transactions issued to child units from parent DOU
        dou_trans_all = Transactions.query.filter(
            func.lower(func.trim(Transactions.received_by)).in_(child_names_lower)
        ).all()
        dou_trans_map = {}
        for t in dou_trans_all:
            rec_by = (t.received_by or '').lower().strip()
            k = (rec_by, t.item_id)
            if k not in dou_trans_map:
                dou_trans_map[k] = {'ser': 0, 'pws': 0}
            dou_trans_map[k]['ser'] += (t.ser or 0)
            dou_trans_map[k]['pws'] += (t.pws or 0)

        # 4. Build records for every child unit across ecc_catalog_items
        for cu_name in all_child_unit_names:
            cu_lower = cu_name.lower().strip()
            parent_div = unit_to_parent_div_map.get(cu_lower, "")

            for cat_item in ecc_catalog_items:
                iid = cat_item.id
                i_name = (cat_item.item_name or "").strip()
                k = (cu_lower, iid)

                group_recs = child_track_grouped.get(k, [])
                auth_val = child_auth_lookup.get(k)
                if auth_val is None and group_recs:
                    auth_val = group_recs[0].auth or 0
                if auth_val is None:
                    auth_val = 0

                # Held calculation: held = max(0, held - (condemned_ser + condemned_pws))
                cond_ser = sum(getattr(r, 'condemned_ser', 0) or 0 for r in group_recs)
                cond_pws = sum(getattr(r, 'condemned_pws', 0) or 0 for r in group_recs)

                if k in dou_trans_map:
                    orig_ser = dou_trans_map[k]['ser']
                    orig_pws = dou_trans_map[k]['pws']
                elif group_recs:
                    orig_ser = sum((r.ser or 0) + (getattr(r, 'available_ser', 0) or 0) for r in group_recs)
                    orig_pws = sum((r.pws or 0) + (getattr(r, 'available_pws', 0) or 0) for r in group_recs)
                    if orig_ser == 0 and orig_pws == 0:
                        tot_calc = sum(r.calc_held() for r in group_recs)
                        orig_ser = tot_calc
                else:
                    orig_ser = 0
                    orig_pws = 0

                tot_orig = orig_ser + orig_pws
                tot_cond = cond_ser + cond_pws
                held_val = max(0, tot_orig - tot_cond)
                rem_s = max(0, orig_ser - cond_ser)
                rem_p = max(0, orig_pws - cond_pws)
                if rem_s + rem_p > held_val:
                    if cond_pws > orig_pws:
                        rem_s = max(0, rem_s - (cond_pws - orig_pws))
                    if cond_ser > orig_ser:
                        rem_p = max(0, rem_p - (cond_ser - orig_ser))
                net_ser = rem_s
                net_pws = max(0, held_val - net_ser)
                defi_val = auth_val - held_val

                ecc_child_units_chart_data.append({
                    "id": group_recs[0].id if group_recs else 0,
                    "division": parent_div,
                    "unit_name": cu_name,
                    "item_name": i_name,
                    "category": cat_item.category or "CAT-I",
                    "scale": group_recs[0].scale if group_recs else "1 per indl",
                    "auth_total": auth_val,
                    "unit_auth": auth_val,
                    "stock_ser": net_ser,
                    "stock_pws": net_pws,
                    "stock_total": held_val,
                    "condemned_ser": cond_ser,
                    "condemned_pws": cond_pws,
                    "deficiency": defi_val
                })

    # Compute ECC Supply Readiness by Division
    from collections import defaultdict
    ecc_div_readiness = defaultdict(lambda: {"auth": 0, "held": 0})
    for rec in track_records:
        if rec.unit_name:
            ecc_div_readiness[rec.unit_name]["auth"] += (rec.auth or 0)
            ecc_div_readiness[rec.unit_name]["held"] += rec.calc_held()

    for div in all_div_admins:
        if div not in ecc_div_readiness:
            ecc_div_readiness[div] = {"auth": 0, "held": 0}

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

    dou_child_count_map = {}
    for u in db_units:
        u_name = u.name or ""
        units_list = (
            division_child_units_map.get(u_name)
            or division_child_units_map.get(u_name.replace('_', ' '))
            or division_child_units_map.get(u_name.replace(' ', '_'))
            or []
        )
        cnt = len(units_list)
        dou_child_count_map[u_name] = cnt
        dou_child_count_map[u_name.lower()] = cnt
        dou_child_count_map[u_name.replace('_', ' ')] = cnt
        dou_child_count_map[u_name.replace('_', ' ').lower()] = cnt
        setattr(u, 'child_units_count', cnt)

    db_units_data = [
        {
            "name": u.name.replace('_', ' ').upper() if u.name else "",
            "authorized_strength": u.authorized_strength or 0,
            "posted_strength": u.posted_strength or 0
        } for u in db_units
    ]

    # Build Month-wise Held Trend Dataset from TrackUnitItems
    all_history_records = track_query.order_by(TrackUnitItems.issued_at.asc(), TrackUnitItems.id.asc()).all()
    all_history_records = [tr for tr in all_history_records if tr.item and (tr.item.type or '').lower() == 'ecc']
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

    items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').order_by(ScmeItems.item_name).all()
    categories = sorted(list(set(i.category for i in items if i.category)))
    ecc_categories = categories

    # ── Dataset for Overall Analysis Chart (AUTH vs STK HELD WITH 2 FOD) ──
    ecc_all_items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').order_by(ScmeItems.id).all()

    fod_stock_sums = dict(
        db.session.query(
            FodStock.item_id,
            func.coalesce(func.sum(FodStock.quantity), 0)
        ).group_by(FodStock.item_id).all()
    )

    whole_auth_recs = ItemAuth.query.filter(
        (ItemAuth.whole_auth.isnot(None)) | (ItemAuth.whole_res.isnot(None))
    ).order_by(ItemAuth.id.desc()).all()
    whole_auth_by_item = {}
    for r in whole_auth_recs:
        if r.item_id not in whole_auth_by_item:
            whole_auth_by_item[r.item_id] = (r.whole_auth or 0) if r.whole_auth is not None else (r.whole_res or 0)

    unit_auth_sums = dict(
        db.session.query(
            ItemAuth.item_id,
            func.coalesce(func.sum(ItemAuth.auth), 0)
        ).filter(ItemAuth.auth > 0).group_by(ItemAuth.item_id).all()
    )

    track_auth_sums = dict(
        db.session.query(
            TrackUnitItems.item_id,
            func.coalesce(func.sum(TrackUnitItems.auth), 0)
        ).filter(TrackUnitItems.auth > 0).group_by(TrackUnitItems.item_id).all()
    )

    overall_analysis_data = []
    for item in ecc_all_items:
        if item.id in whole_auth_by_item and whole_auth_by_item[item.id] > 0:
            auth_val = int(whole_auth_by_item[item.id])
        elif item.id in unit_auth_sums and unit_auth_sums[item.id] > 0:
            auth_val = int(unit_auth_sums[item.id])
        elif item.id in track_auth_sums and track_auth_sums[item.id] > 0:
            auth_val = int(track_auth_sums[item.id])
        else:
            auth_val = 0

        stk_val = int(fod_stock_sums.get(item.id, 0))

        cat_str = (item.category or "CAT-I").strip().upper()
        norm_cat = "CAT-II" if ("CAT-II" in cat_str or "CAT II" in cat_str or "CAT2" in cat_str) else "CAT-I"

        overall_analysis_data.append({
            "item_id": item.id,
            "item_name": item.item_name,
            "category": norm_cat,
            "auth": auth_val,
            "stk_held_2fod": stk_val
        })

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
        division_child_units_map=division_child_units_map,
        ecc_child_units_chart_data=ecc_child_units_chart_data,
        total_ecc_auth=total_ecc_auth,
        total_ecc_held=total_ecc_held,
        global_ecc_deficiency=global_ecc_deficiency,
        active_ecc_divisions=active_ecc_divisions,
        ecc_readiness_data=ecc_readiness_data,
        db_units=db_units,
        dou_child_count_map=dou_child_count_map,
        ecc_critical_alerts=ecc_critical_alerts,
        db_units_data=db_units_data,
        overall_analysis_data=overall_analysis_data,
        monthly_held_trend_data=monthly_held_trend_data,
        is_div_admin=is_div_admin,
        user_div=user_div or "",
        items=items,
        categories=categories,
        ecc_categories=ecc_categories,
        all_div_admins=all_div_admins
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

        # Send Notification to Division/Unit Admin
        try:
            sender_name = session.get("username") or "2_FOD"
            notif = Notification(
                title="New SCME Equipment Allocated to You",
                message=f"{sender_name} issued item '{item_exists.item_name}' (Auth: {new_issued.unit_authorized}, Held: {new_issued.held}) to you.",
                sender_name=sender_name,
                target_user=new_issued.unit_name,
                target_role="division_admin",
                item_id=item_id
            )
            db.session.add(notif)
        except Exception as ne:
            print("Notification insert notice:", ne)

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
        from sqlalchemy import func, or_
        record = TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)) == unit_name.lower().strip(),
            TrackUnitItems.item_id == item_id_val
        ).order_by(TrackUnitItems.id.desc()).first()

        auth_val = (record.auth or 0) if record else 0
        scale_val = (record.scale or "").strip() if record else ""

        # 2. Query ItemAuth (PRIMARY SOURCE FOR AUTH & UNIT SCALE)
        auth_rec = ItemAuth.query.filter(
            func.lower(func.trim(ItemAuth.unit_name)) == unit_name.lower().strip(),
            ItemAuth.item_id == item_id_val
        ).first()

        if auth_rec:
            if (auth_rec.auth or 0) > 0:
                auth_val = auth_rec.auth
            if auth_rec.scale and auth_rec.scale.strip():
                scale_val = auth_rec.scale.strip()

        # 3. Query ScmeIssuedItems as fallback
        issued_rec = ScmeIssuedItems.query.filter(
            func.lower(func.trim(ScmeIssuedItems.unit_name)) == unit_name.lower().strip(),
            ScmeIssuedItems.item_id == item_id_val
        ).first()

        if auth_val == 0 and issued_rec and (issued_rec.unit_authorized or 0) > 0:
            auth_val = issued_rec.unit_authorized

        if not scale_val and issued_rec and issued_rec.scale:
            scale_val = issued_rec.scale.strip()

        # 4. Fallback to Global ItemAuth (where unit_name is NULL or empty)
        if not scale_val:
            global_auth = ItemAuth.query.filter(
                ItemAuth.item_id == item_id_val,
                or_(ItemAuth.unit_name == None, func.trim(ItemAuth.unit_name) == '')
            ).first()
            if global_auth and global_auth.scale and global_auth.scale.strip():
                scale_val = global_auth.scale.strip()

        # 5. Default fallback if still empty
        if not scale_val:
            scale_val = "1 PER INDL"

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
                deficiency_val = auth_val - held_val
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
        stock_type = (data.get("stock_type") or "FREE STK").strip().upper()
        # Normalise aliases
        if stock_type in ['FREE', 'FREE STK', 'FREESTOCK']:
            stock_type = 'FREE STK'
        elif stock_type in ['CMD', 'COMD']:
            stock_type = 'COMD'
        elif stock_type == 'IHQ':
            stock_type = 'IHQ'
        else:
            stock_type = 'FREE STK'
        
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

        now_dt = datetime.now()
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
                type=stock_type,
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

        # Send Notification to Division Admin
        try:
            sender_name = session.get("username") or "2_FOD"
            notif = Notification(
                title="New ECC Stock Allocated to You",
                message=f"{sender_name} issued item '{item_exists.item_name}' (SER: {stock_ser_val}, PWS: {stock_pws_val}) to you.",
                sender_name=sender_name,
                target_user=bbf_division,
                target_role="division_admin",
                item_id=item_id_val
            )
            db.session.add(notif)
        except Exception as ne:
            print("Notification insert notice:", ne)

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
        source = request.form.get('source', '').strip()  # Depo / LP
        stock_type = request.form.get('type', '').strip()  # FREE STK / IHQ / CMD

        quantity = ser + pws
        stock_type_clean = stock_type.strip().upper()
        if stock_type_clean in ['CMD', 'COMD']:
            stock_type = 'CMD'
        elif stock_type_clean == 'IHQ':
            stock_type = 'IHQ'
        else:
            stock_type = 'FREE STK'

        if not voucher_no or not category or not item_id or not source or not stock_type:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('scme.add_stock'))

        # Unique voucher_no check
        from sqlalchemy import func
        existing_vch = FodStock.query.filter(func.lower(FodStock.voucher_no) == voucher_no.lower()).first()
        if existing_vch:
            flash("This voucher number already exists.", "danger")
            return redirect(url_for('scme.add_stock'))

        # Backend validation: Ensure item_auth has non-null whole_auth and whole_res
        auth_check = ItemAuth.query.filter(
            ItemAuth.item_id == item_id,
            ItemAuth.whole_auth.isnot(None),
            ItemAuth.whole_res.isnot(None)
        ).first()

        if not auth_check:
            flash("Cannot update stock: Whole AUTH and Whole RES must be filled in item_auth for this item before updating stock. Please click 'INSERT AUTH' first.", "danger")
            return redirect(url_for('scme.add_stock', item_id=item_id))

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

        # Ensure type column exists in transactions table
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE transactions ADD COLUMN type VARCHAR(50);"))
                conn.commit()
        except Exception:
            pass

        # Record transaction entry with issued_by='2 FOD' and received_by='2 FOD' for Qty Recd & BBF tracking
        tx_entry = Transactions(
            issued_by="2 FOD",
            received_by="2 FOD",
            item_id=item_id,
            ser=ser,
            pws=pws,
            type=stock_type,
            remarks=f"Stock Added - Voucher {voucher_no}"
        )
        db.session.add(tx_entry)

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

    from sqlalchemy import func
    items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').order_by(ScmeItems.item_name).all()
    categories = db.session.query(ScmeItems.category).filter(func.lower(ScmeItems.type) == 'ecc').distinct().all()
    category_list = [c[0] for c in categories if c[0]]
    if not category_list:
        category_list = ['CAT-I', 'CAT-II']

    # Query item_id set having non-null whole_auth & whole_res
    valid_auth_records = ItemAuth.query.filter(
        ItemAuth.whole_auth.isnot(None),
        ItemAuth.whole_res.isnot(None)
    ).all()
    valid_auth_item_ids = set(r.item_id for r in valid_auth_records if r.item_id)

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
    recent_auth_entries = ItemAuth.query.filter(
        (ItemAuth.whole_auth.isnot(None)) | (ItemAuth.whole_res.isnot(None))
    ).order_by(ItemAuth.created_at.desc(), ItemAuth.id.desc()).limit(20).all()

    return render_template(
        '/scme_dashboard/add_stock.html',
        items=items,
        categories=category_list,
        recent_stocks=recent_stocks,
        recent_auth_entries=recent_auth_entries,
        current_stock_summary=current_stock_summary,
        current_stock_list=current_stock_list,
        total_fod_qty=total_fod_qty,
        total_fod_ser=total_fod_ser,
        total_fod_pws=total_fod_pws,
        valid_auth_item_ids=valid_auth_item_ids
    )

@scme_bp.route('/insert-auth', methods=['POST'])
def insert_auth():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return redirect("/auth/login")

    item_id = request.form.get('item_id', type=int)
    whole_auth = request.form.get('whole_auth', type=int)
    whole_res = request.form.get('whole_res', type=int)

    if not item_id:
        flash("Please select an item.", "danger")
        return redirect(url_for('scme.add_stock'))

    if whole_auth is None and whole_res is None:
        flash("Please enter AUTH or RES value.", "danger")
        return redirect(url_for('scme.add_stock'))

    scale = request.form.get('scale', '').strip() or None

    # Search for an existing global or matching ItemAuth record for this item_id to update
    existing_rec = ItemAuth.query.filter(
        ItemAuth.item_id == item_id,
        db.or_(ItemAuth.unit_name == None, db.func.trim(ItemAuth.unit_name) == '')
    ).first()

    if existing_rec:
        existing_rec.whole_auth = whole_auth
        existing_rec.whole_res = whole_res
        if scale:
            existing_rec.scale = scale
    else:
        new_auth_rec = ItemAuth(
            unit_name=None,
            item_id=item_id,
            auth=None,
            whole_auth=whole_auth,
            whole_res=whole_res,
            scale=scale
        )
        db.session.add(new_auth_rec)

    try:
        log_entry = ActionLog(
            user_id=session.get("user_id"),
            username=session.get("username", "Unknown"),
            role=session.get("role", "scme"),
            action_type="UPDATE" if existing_rec else "CREATE",
            module="Item Auth",
            details=f"Updated Auth Record: Item ID {item_id}, Whole Auth {whole_auth}, Whole Res {whole_res}"
        )
        db.session.add(log_entry)
    except Exception:
        pass

    db.session.commit()
    flash("Auth record saved/updated successfully in item_auth table!", "success")
    return redirect(url_for('scme.add_stock'))

@scme_bp.route('/current-stock', methods=['GET'])
def current_stock_page():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return redirect("/auth/login")

    from sqlalchemy import func, case
    cat_order = case(
        (func.upper(ScmeItems.category).in_(['CAT-I', 'CAT I', 'CAT 1', 'CAT1']), 1),
        (func.upper(ScmeItems.category).in_(['CAT-II', 'CAT II', 'CAT 2', 'CAT2']), 2),
        else_=3
    )
    items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').order_by(cat_order, ScmeItems.category.asc(), ScmeItems.item_name.asc()).all()
    categories = db.session.query(ScmeItems.category).filter(func.lower(ScmeItems.type) == 'ecc').distinct().all()
    category_list = [c[0] for c in categories if c[0]]
    if not category_list:
        category_list = ['CAT-I', 'CAT-II']

    # Available Stock = SUM(inward) - SUM(outward) to match BBF logic
    inward_rows = db.session.query(
        Transactions.item_id,
        func.sum(Transactions.ser).label('in_ser'),
        func.sum(Transactions.pws).label('in_pws'),
        func.max(Transactions.timestamp).label('last_in')
    ).filter(
        func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod'])
    ).group_by(Transactions.item_id).all()

    outward_rows = db.session.query(
        Transactions.item_id,
        func.sum(Transactions.ser).label('out_ser'),
        func.sum(Transactions.pws).label('out_pws'),
        func.max(Transactions.timestamp).label('last_out')
    ).filter(
        func.lower(func.trim(Transactions.issued_by)).in_(['2 fod', '2_fod', 'scme', 'admin', 'super_admin']),
        ~func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod'])
    ).group_by(Transactions.item_id).all()

    inward_map = {r.item_id: (int(r.in_ser or 0), int(r.in_pws or 0), r.last_in) for r in inward_rows}
    outward_map = {r.item_id: (int(r.out_ser or 0), int(r.out_pws or 0), r.last_out) for r in outward_rows}

    all_tx_item_ids = set(inward_map.keys()).union(set(outward_map.keys()))
    current_stock_summary = {}
    for iid in all_tx_item_ids:
        in_s, in_p, last_in = inward_map.get(iid, (0, 0, None))
        out_s, out_p, last_out = outward_map.get(iid, (0, 0, None))

        net_ser = max(0, in_s - out_s)
        net_pws = max(0, in_p - out_p)
        net_qty = net_ser + net_pws

        last_dt = None
        if last_in and last_out:
            last_dt = max(last_in, last_out)
        else:
            last_dt = last_in or last_out

        current_stock_summary[iid] = {
            "total_ser": net_ser,
            "total_pws": net_pws,
            "total_qty": net_qty,
            "last_updated": last_dt.strftime('%d %b %Y, %H:%M') if last_dt else ''
        }

    current_stock_list = []
    total_fod_qty = 0
    total_fod_ser = 0
    total_fod_pws = 0
    items_with_stock_count = 0

    for item in items:
        sum_data = current_stock_summary.get(item.id)
        ser_qty   = sum_data["total_ser"] if sum_data else 0
        pws_qty   = sum_data["total_pws"] if sum_data else 0
        total_qty = sum_data["total_qty"] if sum_data else 0
        last_updated = (sum_data["last_updated"] if sum_data and sum_data["last_updated"] else 'N/A')

        if ser_qty > 0 or pws_qty > 0:
            items_with_stock_count += 1

        total_fod_qty += total_qty
        total_fod_ser += ser_qty
        total_fod_pws += pws_qty

        current_stock_list.append({
            "item_id": item.id,
            "item_name": item.item_name,
            "category": item.category,
            "total_qty": total_qty,
            "total_ser": ser_qty,
            "total_pws": pws_qty,
            "last_updated": last_updated
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

    from sqlalchemy import func, case
    cat_order = case(
        (func.upper(ScmeItems.category).in_(['CAT-I', 'CAT I', 'CAT 1', 'CAT1']), 1),
        (func.upper(ScmeItems.category).in_(['CAT-II', 'CAT II', 'CAT 2', 'CAT2']), 2),
        else_=3
    )
    items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').order_by(cat_order, ScmeItems.category.asc(), ScmeItems.item_name.asc()).all()

    # Available Stock = SUM(inward) - SUM(outward) to match BBF logic
    inward_rows = db.session.query(
        Transactions.item_id,
        func.sum(Transactions.ser).label('in_ser'),
        func.sum(Transactions.pws).label('in_pws'),
        func.max(Transactions.timestamp).label('last_in')
    ).filter(
        func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod'])
    ).group_by(Transactions.item_id).all()

    outward_rows = db.session.query(
        Transactions.item_id,
        func.sum(Transactions.ser).label('out_ser'),
        func.sum(Transactions.pws).label('out_pws'),
        func.max(Transactions.timestamp).label('last_out')
    ).filter(
        func.lower(func.trim(Transactions.issued_by)).in_(['2 fod', '2_fod', 'scme', 'admin', 'super_admin']),
        ~func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod'])
    ).group_by(Transactions.item_id).all()

    inward_map = {r.item_id: (int(r.in_ser or 0), int(r.in_pws or 0), r.last_in) for r in inward_rows}
    outward_map = {r.item_id: (int(r.out_ser or 0), int(r.out_pws or 0), r.last_out) for r in outward_rows}

    all_tx_item_ids = set(inward_map.keys()).union(set(outward_map.keys()))
    stock_summary = {}
    for iid in all_tx_item_ids:
        in_s, in_p, last_in = inward_map.get(iid, (0, 0, None))
        out_s, out_p, last_out = outward_map.get(iid, (0, 0, None))

        net_ser = max(0, in_s - out_s)
        net_pws = max(0, in_p - out_p)
        net_qty = net_ser + net_pws

        last_dt = None
        if last_in and last_out:
            last_dt = max(last_in, last_out)
        else:
            last_dt = last_in or last_out

        stock_summary[iid] = {
            "total_ser": net_ser,
            "total_pws": net_pws,
            "total_qty": net_qty,
            "last_updated": last_dt.strftime('%d %b %Y, %H:%M') if last_dt else 'N/A'
        }

    data = []
    total_qty_all = 0
    total_ser_all = 0
    total_pws_all = 0

    for item in items:
        sum_data = stock_summary.get(item.id)
        ser_qty   = sum_data["total_ser"] if sum_data else 0
        pws_qty   = sum_data["total_pws"] if sum_data else 0
        total_qty = sum_data["total_qty"] if sum_data else 0
        last_updated = (sum_data["last_updated"] if sum_data and sum_data["last_updated"] else 'N/A')

        total_qty_all += total_qty
        total_ser_all += ser_qty
        total_pws_all += pws_qty

        data.append({
            "item_id": item.id,
            "item_name": item.item_name,
            "category": item.category,
            "total_qty": total_qty,
            "total_ser": ser_qty,
            "total_pws": pws_qty,
            "last_updated": last_updated
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


@scme_bp.route('/api/check-voucher', methods=['GET'])
def api_check_voucher():
    if "user_id" not in session:
        return jsonify({"exists": False, "message": "Unauthorized"}), 401
    
    voucher_no = request.args.get('voucher_no', '').strip()
    if not voucher_no:
        return jsonify({"exists": False})

    from sqlalchemy import func
    existing = FodStock.query.filter(func.lower(FodStock.voucher_no) == voucher_no.lower()).first()
    return jsonify({"exists": existing is not None})


@scme_bp.route('/api/available-stock/<int:item_id>', methods=['GET'])
def api_get_available_stock(item_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    item = ScmeItems.query.get(item_id)
    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404

    from sqlalchemy import func

    # Inward: all receipts received by 2 FOD
    fod_in_rows = Transactions.query.filter(
        Transactions.item_id == item_id,
        func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod'])
    ).all()

    # Outward: issued from 2 FOD to units
    fod_out_rows = Transactions.query.filter(
        Transactions.item_id == item_id,
        func.lower(func.trim(Transactions.issued_by)).in_(['2 fod', '2_fod', 'scme', 'admin', 'super_admin']),
        ~func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod'])
    ).all()

    # Accumulate inward by type
    in_free_ser = in_free_pws = 0
    in_comd_ser = in_comd_pws = 0
    in_ihq_ser = in_ihq_pws = 0

    for t in fod_in_rows:
        st = (t.type or '').strip().upper()
        if st in ['CMD', 'COMD']:
            in_comd_ser += int(t.ser or 0)
            in_comd_pws += int(t.pws or 0)
        elif st == 'IHQ':
            in_ihq_ser += int(t.ser or 0)
            in_ihq_pws += int(t.pws or 0)
        else:
            in_free_ser += int(t.ser or 0)
            in_free_pws += int(t.pws or 0)

    # Accumulate outward by type
    out_free_ser = out_free_pws = 0
    out_comd_ser = out_comd_pws = 0
    out_ihq_ser = out_ihq_pws = 0

    for t in fod_out_rows:
        st = (t.type or '').strip().upper()
        if st in ['CMD', 'COMD']:
            out_comd_ser += int(t.ser or 0)
            out_comd_pws += int(t.pws or 0)
        elif st == 'IHQ':
            out_ihq_ser += int(t.ser or 0)
            out_ihq_pws += int(t.pws or 0)
        else:
            out_free_ser += int(t.ser or 0)
            out_free_pws += int(t.pws or 0)

    free_ser = max(0, in_free_ser - out_free_ser)
    free_pws = max(0, in_free_pws - out_free_pws)
    comd_ser = max(0, in_comd_ser - out_comd_ser)
    comd_pws = max(0, in_comd_pws - out_comd_pws)
    ihq_ser = max(0, in_ihq_ser - out_ihq_ser)
    ihq_pws = max(0, in_ihq_pws - out_ihq_pws)

    comd_avail = comd_ser + comd_pws
    ihq_avail = ihq_ser + ihq_pws
    free_avail = free_ser + free_pws

    fod_total = free_avail + comd_avail + ihq_avail
    available_qty = fod_total if fod_total > 0 else None

    return jsonify({
        "success": True,
        "item_id": item_id,
        "item_name": item.item_name,
        "has_fod_stock": (fod_total > 0),
        "fod_total": fod_total,
        "available_qty": available_qty,
        "ser_total": free_ser + comd_ser + ihq_ser,
        "pws_total": free_pws + comd_pws + ihq_pws,
        # Per-type breakdown with SER and PWS
        "free_ser": free_ser,
        "free_pws": free_pws,
        "free_total": free_avail,
        "comd_ser": comd_ser,
        "comd_pws": comd_pws,
        "comd": comd_avail,
        "ihq_ser": ihq_ser,
        "ihq_pws": ihq_pws,
        "ihq": ihq_avail,
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

        # Flexible search in ItemAuth table to update existing unit record instead of creating duplicates
        norm_unit = unit_name.lower().strip().replace('_', ' ')
        all_recs_for_item = ItemAuth.query.filter(ItemAuth.item_id == item_id).all()
        item_auth_rec = None
        for rec in all_recs_for_item:
            if rec.unit_name:
                rec_unit_norm = rec.unit_name.lower().strip().replace('_', ' ')
                if rec_unit_norm == norm_unit:
                    item_auth_rec = rec
                    break

        if item_auth_rec:
            item_auth_rec.auth = auth_int
            # Ensure unit_name stays clean
            if not item_auth_rec.unit_name:
                item_auth_rec.unit_name = unit_name
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

    if not item_id:
        return jsonify({"success": False, "message": "Item ID required"}), 400

    from sqlalchemy import func, or_
    norm_unit = unit_name.lower().strip().replace('_', ' ') if unit_name else ""
    all_recs_for_item = ItemAuth.query.filter(ItemAuth.item_id == item_id).all()
    
    auth_val = 0
    whole_auth_val = None
    whole_res_val = None
    scale_val = ""
    global_scale = ""

    possible_names = {
        unit_name.lower().strip(),
        unit_name.replace('_', ' ').lower().strip(),
        unit_name.replace(' ', '_').lower().strip()
    } if unit_name else set()

    for rec in all_recs_for_item:
        if not rec.unit_name or not rec.unit_name.strip():
            if rec.whole_auth is not None:
                whole_auth_val = rec.whole_auth
            if rec.whole_res is not None:
                whole_res_val = rec.whole_res
            if rec.scale and rec.scale.strip():
                global_scale = rec.scale.strip()
        else:
            rec_unit_norm = rec.unit_name.lower().strip().replace('_', ' ')
            if norm_unit and (rec_unit_norm == norm_unit or rec.unit_name.lower().strip() in possible_names):
                auth_val = rec.auth if (rec.auth is not None) else 0
                if rec.scale and rec.scale.strip():
                    scale_val = rec.scale.strip()

    # Fallback to TrackUnitItems
    if (auth_val is None or auth_val == 0) and possible_names:
        track_rec = TrackUnitItems.query.filter(
            db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_(list(possible_names)),
            TrackUnitItems.item_id == item_id
        ).order_by(TrackUnitItems.id.desc()).first()
        if track_rec:
            if auth_val is None or auth_val == 0:
                if track_rec.auth is not None:
                    auth_val = track_rec.auth
            if not scale_val and track_rec.scale:
                scale_val = track_rec.scale.strip()

    # Fallback to ScmeIssuedItems
    if (auth_val is None or auth_val == 0) and possible_names:
        issued_rec = ScmeIssuedItems.query.filter(
            db.func.lower(db.func.trim(ScmeIssuedItems.unit_name)).in_(list(possible_names)),
            ScmeIssuedItems.item_id == item_id
        ).first()
        if issued_rec:
            if auth_val is None or auth_val == 0:
                if issued_rec.unit_authorized is not None:
                    auth_val = issued_rec.unit_authorized
            if not scale_val and issued_rec.scale:
                scale_val = issued_rec.scale.strip()

    if not scale_val:
        scale_val = global_scale or "1 PER INDL"

    return jsonify({
        "success": True,
        "unit_name": unit_name,
        "item_id": item_id,
        "auth": auth_val,
        "whole_auth": whole_auth_val,
        "whole_res": whole_res_val,
        "scale": scale_val
    })


def build_monthly_reports_payload(filter_type, month_param, year_param, is_div_admin, user_div):
    ensure_transactions_type_column()
    from sqlalchemy import func
    filter_type = (filter_type or "month").lower()
    if filter_type not in ["month", "year"]:
        filter_type = "month"

    now_date = datetime.now()

    if filter_type == "year":
        try:
            sel_year = int(year_param) if year_param else now_date.year
        except Exception:
            sel_year = now_date.year

        first_day_sel = datetime(sel_year, 1, 1)
        first_day_next = datetime(sel_year + 1, 1, 1)
        first_day_prev = datetime(sel_year - 1, 1, 1)

        selected_period_label = f"YEAR {sel_year}"
        table_header_banner = f"ANNUAL REPORT FOR THE YEAR {sel_year}"
        selected_month_str = ""
        selected_year_str = f"{sel_year:04d}"
    else:
        try:
            if month_param:
                sel_year, sel_month = int(month_param.split("-")[0]), int(month_param.split("-")[1])
            else:
                sel_year, sel_month = now_date.year, now_date.month
        except Exception:
            sel_year, sel_month = now_date.year, now_date.month

        first_day_sel = datetime(sel_year, sel_month, 1)
        if sel_month == 12:
            first_day_next = datetime(sel_year + 1, 1, 1)
        else:
            first_day_next = datetime(sel_year, sel_month + 1, 1)

        if sel_month == 1:
            first_day_prev = datetime(sel_year - 1, 12, 1)
        else:
            first_day_prev = datetime(sel_year, sel_month - 1, 1)

        selected_period_label = first_day_sel.strftime('%B %Y')
        table_header_banner = f"MONTHLY REPORT FOR THE MONTH OF {selected_period_label.upper()}"
        selected_month_str = f"{sel_year:04d}-{sel_month:02d}"
        selected_year_str = f"{sel_year:04d}"

    # ── Available months & years lists for pickers ──
    months_set = set()

    # 1. From Transactions
    try:
        tx_months = db.session.query(func.date_format(Transactions.timestamp, '%Y-%m')).filter(Transactions.timestamp.isnot(None)).distinct().all()
        for r in tx_months:
            if r[0]: months_set.add(r[0])
    except Exception:
        pass

    # 2. From FodStock
    try:
        fod_months = db.session.query(func.date_format(FodStock.created_at, '%Y-%m')).filter(FodStock.created_at.isnot(None)).distinct().all()
        for r in fod_months:
            if r[0]: months_set.add(r[0])
    except Exception:
        pass

    # 3. From TrackUnitItems
    try:
        track_months = db.session.query(func.date_format(TrackUnitItems.issued_at, '%Y-%m')).filter(TrackUnitItems.issued_at.isnot(None)).distinct().all()
        for r in track_months:
            if r[0]: months_set.add(r[0])
    except Exception:
        pass

    # 4. Standard calendar months up to current month for this year, and all 12 months for previous year
    cur_year = now_date.year
    for m in range(1, now_date.month + 1):
        months_set.add(f"{cur_year:04d}-{m:02d}")
    for m in range(1, 13):
        months_set.add(f"{cur_year - 1:04d}-{m:02d}")

    # Ensure selected month is in the list
    if month_param and len(month_param.split('-')) == 2:
        months_set.add(month_param)

    available_months = sorted(list(months_set), reverse=True)

    years_set = {str(now_date.year), str(now_date.year - 1)}
    for ym in available_months:
        years_set.add(ym.split('-')[0])
    available_years = sorted(list(years_set), reverse=True)

    div_records = Divs.query.order_by(Divs.name).all()
    div_admin_names = list(dict.fromkeys(d.name.strip() for d in div_records if d.name and d.name.strip()))

    track_query = TrackUnitItems.query.filter(
        TrackUnitItems.issued_at < first_day_next
    )
    if is_div_admin and user_div:
        track_query = track_query.filter(TrackUnitItems.unit_name == user_div)
    elif div_admin_names:
        track_query = track_query.filter(TrackUnitItems.unit_name.in_(div_admin_names))

    track_records = track_query.order_by(TrackUnitItems.issued_at.desc(), TrackUnitItems.id.desc()).all()
    # Filter track_records strictly to items with type == 'ecc'
    track_records = [tr for tr in track_records if tr.item and (tr.item.type or '').lower() == 'ecc']

    grouped_track_map = {}
    for rec in track_records:
        u_key = (rec.unit_name or '').lower().strip()
        key = (u_key, rec.item_id)
        if key not in grouped_track_map:
            grouped_track_map[key] = []
        grouped_track_map[key].append(rec)

    # Ensure ALL catalog items with type == 'ecc' exist in grouped_track_map so all ECC items are listed!
    all_ecc_catalog_items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').all()
    target_default_div = user_div if (is_div_admin and user_div) else '2 FOD'
    with db.session.no_autoflush:
        for cat_item in all_ecc_catalog_items:
            u_key_target = target_default_div.lower().strip()
            if (u_key_target, cat_item.id) not in grouped_track_map:
                dummy_rec = TrackUnitItems(
                    unit_name=target_default_div,
                    item_id=cat_item.id,
                    ser=0,
                    pws=0,
                    auth=0,
                    issued_at=first_day_sel
                )
                dummy_rec.item = cat_item
                grouped_track_map[(u_key_target, cat_item.id)] = [dummy_rec]

    prev_month_map = {}
    prev_trans = Transactions.query.filter(
        Transactions.timestamp >= first_day_prev,
        Transactions.timestamp < first_day_sel
    ).all()
    for t in prev_trans:
        iss_by = (t.issued_by or '').lower().strip().replace('_', ' ')
        rec_by = (t.received_by or '').lower().strip().replace('_', ' ')
        if iss_by == rec_by or rec_by in ['2 fod', '2_fod']:
            continue
        if '2 fod' in iss_by or '2_fod' in iss_by or iss_by in ['scme', 'admin', 'super_admin']:
            r_key = (t.received_by or '').lower().strip()
            key = (r_key, t.item_id)
            if key not in prev_month_map:
                prev_month_map[key] = {'ser': 0, 'pws': 0}
            prev_month_map[key]['ser'] += (t.ser or 0)
            prev_month_map[key]['pws'] += (t.pws or 0)

    issued_this_month_map = {}
    fod_total_issued_map = {}
    issd_trans = Transactions.query.filter(
        Transactions.timestamp >= first_day_sel,
        Transactions.timestamp < first_day_next
    ).all()
    for t in issd_trans:
        iss_by = (t.issued_by or '').lower().strip().replace('_', ' ')
        rec_by = (t.received_by or '').lower().strip().replace('_', ' ')
        if iss_by == rec_by:
            continue
        if ('2 fod' in iss_by or '2_fod' in iss_by or iss_by in ['scme', 'admin', 'super_admin']) and rec_by not in ['2 fod', '2_fod']:
            if t.item_id not in fod_total_issued_map:
                fod_total_issued_map[t.item_id] = {'ser': 0, 'pws': 0}
            fod_total_issued_map[t.item_id]['ser'] += (t.ser or 0)
            fod_total_issued_map[t.item_id]['pws'] += (t.pws or 0)

        raw_iss_by = (t.issued_by or '').lower().strip()
        for k_iss in {raw_iss_by, raw_iss_by.replace('_', ' '), raw_iss_by.replace(' ', '_')}:
            key = (k_iss, t.item_id)
            if key not in issued_this_month_map:
                issued_this_month_map[key] = {'ser': 0, 'pws': 0}
            issued_this_month_map[key]['ser'] += (t.ser or 0)
            issued_this_month_map[key]['pws'] += (t.pws or 0)

    # ── QTY RECD DURING MONTH: Query Transactions table where received_by == '2 FOD' for selected month ──
    fod_recd_trans = Transactions.query.filter(
        func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod']),
        Transactions.timestamp >= first_day_sel,
        Transactions.timestamp < first_day_next
    ).all()

    fod_recd_map = {}
    for t in fod_recd_trans:
        if t.item_id not in fod_recd_map:
            fod_recd_map[t.item_id] = {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0}
        st_type = (t.type or '').strip().upper()
        if st_type in ['CMD', 'COMD']:
            fod_recd_map[t.item_id]['comd'] += int(t.ser or 0) + int(t.pws or 0)
        elif st_type == 'IHQ':
            fod_recd_map[t.item_id]['ihq'] += int(t.ser or 0) + int(t.pws or 0)
        else:
            fod_recd_map[t.item_id]['ser'] += int(t.ser or 0)
            fod_recd_map[t.item_id]['pws'] += int(t.pws or 0)

    # ── BBF DATA FROM TRANSACTIONS TABLE (timestamp < first_day_sel for 2 FOD: Inward Receipts minus Outward Issues) ──
    fod_in_bbf = Transactions.query.filter(
        func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod']),
        Transactions.timestamp < first_day_sel
    ).all()

    fod_out_bbf = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)).in_(['2 fod', '2_fod', 'scme', 'admin', 'super_admin']),
        ~func.lower(func.trim(Transactions.received_by)).in_(['2 fod', '2_fod']),
        Transactions.timestamp < first_day_sel
    ).all()

    fod_bbf_map = {}
    for t in fod_in_bbf:
        if t.item_id not in fod_bbf_map:
            fod_bbf_map[t.item_id] = {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0}
        st_type = (t.type or '').strip().upper()
        if st_type in ['CMD', 'COMD']:
            fod_bbf_map[t.item_id]['comd'] += int(t.ser or 0) + int(t.pws or 0)
        elif st_type == 'IHQ':
            fod_bbf_map[t.item_id]['ihq'] += int(t.ser or 0) + int(t.pws or 0)
        else:
            fod_bbf_map[t.item_id]['ser'] += int(t.ser or 0)
            fod_bbf_map[t.item_id]['pws'] += int(t.pws or 0)

    for t in fod_out_bbf:
        if t.item_id not in fod_bbf_map:
            fod_bbf_map[t.item_id] = {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0}
        st_type = (t.type or '').strip().upper()
        if st_type in ['CMD', 'COMD']:
            fod_bbf_map[t.item_id]['comd'] = max(0, fod_bbf_map[t.item_id]['comd'] - (int(t.ser or 0) + int(t.pws or 0)))
        elif st_type == 'IHQ':
            fod_bbf_map[t.item_id]['ihq'] = max(0, fod_bbf_map[t.item_id]['ihq'] - (int(t.ser or 0) + int(t.pws or 0)))
        else:
            fod_bbf_map[t.item_id]['ser'] = max(0, fod_bbf_map[t.item_id]['ser'] - int(t.ser or 0))
            fod_bbf_map[t.item_id]['pws'] = max(0, fod_bbf_map[t.item_id]['pws'] - int(t.pws or 0))

    catalog_item_map = {i.id: i for i in ScmeItems.query.all()}

    # ── PRE-FETCH ALL ItemAuth RECORDS ONCE (fixed, not month-dependent) ──
    # whole_auth_map: item_id -> {whole_auth, whole_res, scale}   (global auth row)
    # unit_auth_map:  (item_id, norm_unit_name) -> auth            (per-unit row)
    all_item_auth_recs = ItemAuth.query.all()

    whole_auth_map = {}   # item_id -> best whole_auth record
    unit_auth_map  = {}   # (item_id, lower_unit_name) -> auth int

    for ia in all_item_auth_recs:
        iid = ia.item_id
        # Whole-auth row: ONLY rows where unit_name is NULL or empty (the global 2 FOD row)
        is_global_row = not ia.unit_name or not ia.unit_name.strip()
        if is_global_row and (ia.whole_auth is not None or ia.whole_res is not None):
            if iid not in whole_auth_map or (ia.id > whole_auth_map[iid].id):
                whole_auth_map[iid] = ia
        # Per-unit auth row
        if ia.unit_name and ia.unit_name.strip():
            key = (iid, ia.unit_name.lower().strip())
            if ia.auth is not None:
                unit_auth_map[key] = ia.auth


    class TrackUnitAdapterReport:
        def __init__(self, rec):
            self.id = rec.id or 0
            self.item_id = rec.item_id or 0
            norm_div = normalize_div_name(rec.unit_name or '').replace('_', ' ')
            self.bbf_division = norm_div
            self.unit_name = norm_div
            self.item = rec.item or catalog_item_map.get(rec.item_id)
            self.item_name = self.item.item_name if self.item else "Unknown Item"
            self.category = self.item.category if self.item else ""
            self.scale = getattr(rec, 'scale', None) or "N/A"

            # ── Fixed AUTH from ItemAuth table (never changes with month) ──
            whole_rec = whole_auth_map.get(rec.item_id)
            unit_key  = (rec.item_id, (rec.unit_name or '').lower().strip())
            unit_auth_val = unit_auth_map.get(unit_key, 0)

            if whole_rec:
                self.auth_auth  = whole_rec.whole_auth or 0
                self.auth_res   = whole_rec.whole_res or 0
                self.auth_total = self.auth_auth + self.auth_res
                self.unit_auth  = unit_auth_val
                self.has_whole_auth = True
                if whole_rec.scale:
                    self.scale = whole_rec.scale
            else:
                # No whole_auth row — use per-unit auth from ItemAuth (still fixed)
                self.auth_auth  = unit_auth_val
                self.auth_res   = 0
                self.auth_total = unit_auth_val
                self.unit_auth  = unit_auth_val
                self.has_whole_auth = False

            self.prev_ser = 0
            self.prev_pws = 0
            self.prev_total = 0
            self.bbf_ser = 0
            self.bbf_pws = 0
            self.bbf_total = 0
            self.bbf_comd = 0
            self.bbf_ihq = 0
            self.recd_ser = 0
            self.recd_pws = 0
            self.recd_comd = 0
            self.recd_ihq = 0
            self.recd_total = 0
            self.issd_ser = 0
            self.issd_pws = 0
            self.issd_total = 0
            self.stock_ser = 0
            self.stock_pws = 0
            self.stock_total = 0
            self.stock_comd = 0
            self.stock_ihq = 0
            self.dou_free_ser = 0
            self.dou_free_pws = 0
            self.dou_free_total = 0
            self.unit_stk_ser = 0
            self.unit_stk_pws = 0
            self.unit_stk_total = 0
            self.total_condemnation = 0
            self.add_knd = getattr(rec, 'add_knd', 0) or 0
            self.add_tn_model = getattr(rec, 'add_tn_model', 0) or 0
            self.add_n_area_otg = getattr(rec, 'add_n_area_otg', 0) or 0
            self.add_idt_ict = getattr(rec, 'add_idt_ict', 0) or 0
            self.add_remarks_ro_bal = 0
            self.tps = 0
            self.deficiency = 0
            self.created_at = rec.issued_at

    parent_dou_tps_map, item_total_tps_map = get_parent_dou_tps_map()
    ecc_states = []

    # ── STK HELD FROM FOD_STOCK_TABLE ──
    fod_stk_held = db.session.query(
        FodStock.item_id,
        FodStock.type,
        func.sum(FodStock.ser).label('sum_ser'),
        func.sum(FodStock.pws).label('sum_pws'),
        func.sum(FodStock.quantity).label('sum_qty')
    ).group_by(FodStock.item_id, FodStock.type).all()

    fod_stk_held_map = {}
    for f in fod_stk_held:
        if f.item_id not in fod_stk_held_map:
            fod_stk_held_map[f.item_id] = {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0}
        st_type = (f.type or '').strip().upper()
        if st_type in ['CMD', 'COMD']:
            fod_stk_held_map[f.item_id]['comd'] += int(f.sum_qty or f.sum_ser or 0)
        elif st_type == 'IHQ':
            fod_stk_held_map[f.item_id]['ihq'] += int(f.sum_qty or f.sum_ser or 0)
        else:
            fod_stk_held_map[f.item_id]['ser'] += int(f.sum_ser or 0)
            fod_stk_held_map[f.item_id]['pws'] += int(f.sum_pws or 0)

    # ── COMPUTE DOU FREE STOCK & CHILD UNIT STOCK (ACROSS DOUs) ──
    dou_query_divs = Divs.query.all()
    if is_div_admin and user_div:
        u_div_norm = user_div.lower().strip()
        dou_query_divs = [d for d in dou_query_divs if d.name.lower().strip() in [u_div_norm, u_div_norm.replace(' ', '_'), u_div_norm.replace('_', ' ')]]

    all_history_trans = Transactions.query.filter(Transactions.timestamp < first_day_next).all()

    dou_aggregate_map = {}
    for it_id in catalog_item_map.keys():
        dou_aggregate_map[it_id] = {'dou_free_ser': 0, 'dou_free_pws': 0, 'unit_stk_ser': 0, 'unit_stk_pws': 0}

    all_div_names_set = set()
    for d in Divs.query.all():
        d_lower = d.name.lower().strip()
        all_div_names_set.update({d_lower, d_lower.replace('_', ' '), d_lower.replace(' ', '_')})
    all_div_names_set.update({'2 fod', '2_fod', 'scme', 'admin', 'super_admin'})

    all_org_ladder = OrgLadder.query.all()
    all_login_users = LoginUser.query.all()
    user_to_org_map = {lu.username.strip().lower(): lu.org_id for lu in all_login_users if lu.username and lu.org_id}

    for div in dou_query_divs:
        dname = div.name.lower().strip()
        div_aliases = {dname, dname.replace('_', ' '), dname.replace(' ', '_')}

        child_units = set()
        div_node = next((o for o in all_org_ladder if o.name and o.name.strip().lower() in div_aliases), None)
        if div_node:
            def get_sub_units(curr):
                sub = []
                for ch in (curr.children or []):
                    ch_t = (ch.type or '').strip().lower()
                    if ch_t == 'unit' or not ch.children:
                        if ch.name: sub.append(ch.name.strip().lower())
                    else:
                        sub.extend(get_sub_units(ch))
                return sub
            for su in get_sub_units(div_node):
                child_units.update({su, su.replace('_', ' '), su.replace(' ', '_')})

        for t in all_history_trans:
            iss = (t.issued_by or '').lower().strip()
            rec = (t.received_by or '').lower().strip()
            if iss in div_aliases and rec and rec not in all_div_names_set:
                child_units.update({rec, rec.replace('_', ' '), rec.replace(' ', '_')})
            if ('2 fod' in iss or '2_fod' in iss) and rec and rec not in all_div_names_set:
                resolved = resolve_parent_dou_global(rec, all_org_ladder, user_to_org_map)
                if resolved.lower() in div_aliases:
                    child_units.update({rec, rec.replace('_', ' '), rec.replace(' ', '_')})

        b_r, b_i, r_m, i_m, c_r, c_i = {}, {}, {}, {}, {}, {}

        for t in all_history_trans:
            iid = t.item_id
            iss = (t.issued_by or '').lower().strip()
            rec = (t.received_by or '').lower().strip()
            ser = t.ser or 0
            pws = t.pws or 0
            ts = t.timestamp

            if ts < first_day_sel:
                if rec in div_aliases:
                    cur = b_r.get(iid, (0, 0))
                    b_r[iid] = (cur[0] + ser, cur[1] + pws)
                if iss in div_aliases:
                    cur = b_i.get(iid, (0, 0))
                    b_i[iid] = (cur[0] + ser, cur[1] + pws)

            if ts >= first_day_sel and ts < first_day_next:
                if rec in div_aliases:
                    cur = r_m.get(iid, (0, 0))
                    r_m[iid] = (cur[0] + ser, cur[1] + pws)
                if iss in div_aliases:
                    cur = i_m.get(iid, (0, 0))
                    i_m[iid] = (cur[0] + ser, cur[1] + pws)

            if child_units:
                if rec in child_units and (iss in div_aliases or '2 fod' in iss or '2_fod' in iss or iss in ['scme', 'admin', 'super_admin']):
                    cur = c_r.get(iid, (0, 0))
                    c_r[iid] = (cur[0] + ser, cur[1] + pws)
                if iss in child_units:
                    cur = c_i.get(iid, (0, 0))
                    c_i[iid] = (cur[0] + ser, cur[1] + pws)

        for iid in catalog_item_map.keys():
            br = b_r.get(iid, (0, 0))
            bi = b_i.get(iid, (0, 0))
            b_s = max(0, br[0] - bi[0])
            b_p = max(0, br[1] - bi[1])

            rm = r_m.get(iid, (0, 0))
            im = i_m.get(iid, (0, 0))
            r_s, r_p = rm[0], rm[1]
            i_s, i_p = im[0], im[1]

            dou_free_s = max(0, b_s + r_s - i_s)
            dou_free_p = max(0, b_p + r_p - i_p)

            cr = c_r.get(iid, (0, 0))
            ci = c_i.get(iid, (0, 0))
            u_s = max(0, cr[0] - ci[0])
            u_p = max(0, cr[1] - ci[1])

            if iid not in dou_aggregate_map:
                dou_aggregate_map[iid] = {'dou_free_ser': 0, 'dou_free_pws': 0, 'unit_stk_ser': 0, 'unit_stk_pws': 0}
            dou_aggregate_map[iid]['dou_free_ser'] += dou_free_s
            dou_aggregate_map[iid]['dou_free_pws'] += dou_free_p
            dou_aggregate_map[iid]['unit_stk_ser'] += u_s
            dou_aggregate_map[iid]['unit_stk_pws'] += u_p

    # ── COMPUTE TOTAL CONDEMNATION ACROSS CHILD DOUs / UNITS ──
    all_child_unit_names = set(all_div_names_set)
    for div in dou_query_divs:
        dname = div.name.lower().strip()
        div_aliases = {dname, dname.replace('_', ' '), dname.replace(' ', '_')}
        for t in all_history_trans:
            iss = (t.issued_by or '').lower().strip()
            rec = (t.received_by or '').lower().strip()
            if iss in div_aliases and rec and rec not in all_div_names_set:
                all_child_unit_names.add(rec)
                all_child_unit_names.add(rec.replace('_', ' '))
                all_child_unit_names.add(rec.replace(' ', '_'))

    cond_query = TrackUnitItems.query
    if is_div_admin and user_div:
        cond_query = cond_query.filter(func.lower(func.trim(TrackUnitItems.unit_name)).in_([u.lower().strip() for u in all_child_unit_names if u]))
    cond_track_records = cond_query.all()

    cond_ser_map = {}
    cond_pws_map = {}
    condemned_map = {}
    for ctr in cond_track_records:
        c_date = getattr(ctr, 'condemnation_date', None)
        if c_date and c_date >= first_day_next:
            continue
        iid = ctr.item_id
        c_ser = ctr.condemned_ser or 0
        c_pws = ctr.condemned_pws or 0
        cond_ser_map[iid] = cond_ser_map.get(iid, 0) + c_ser
        cond_pws_map[iid] = cond_pws_map.get(iid, 0) + c_pws
        condemned_map[iid] = condemned_map.get(iid, 0) + (c_ser + c_pws)

    for (u_key, item_id), group_recs in grouped_track_map.items():
        rec = group_recs[0]
        adapter = TrackUnitAdapterReport(rec)

        prev_data = prev_month_map.get((u_key, item_id), {'ser': 0, 'pws': 0})
        adapter.prev_ser = prev_data['ser']
        adapter.prev_pws = prev_data['pws']
        adapter.prev_total = adapter.prev_ser + adapter.prev_pws
        adapter.bbf_ser = adapter.prev_ser
        adapter.bbf_pws = adapter.prev_pws
        adapter.bbf_total = adapter.prev_total

        tot_ser = sum((r.ser or 0) + (getattr(r, 'available_ser', 0) or 0) for r in group_recs)
        tot_pws = sum((r.pws or 0) + (getattr(r, 'available_pws', 0) or 0) for r in group_recs)
        tot_held_calc = sum(r.calc_held() for r in group_recs)

        adapter.stock_ser = tot_ser
        adapter.stock_pws = tot_pws
        adapter.stock_total = tot_held_calc if tot_held_calc > 0 else (tot_ser + tot_pws)

        u_norm = normalize_div_name(rec.unit_name or '').lower().strip()
        raw_u = (rec.unit_name or '').lower().strip()
        tps_val = parent_dou_tps_map.get((u_norm, item_id))
        if tps_val is None:
            tps_val = parent_dou_tps_map.get((raw_u, item_id))
        if (tps_val is None or tps_val == 0) and (not is_div_admin or (user_div and user_div.strip().lower() in ['2 fod', '2_fod'])):
            tps_val = item_total_tps_map.get(item_id, 0)
        adapter.tps = tps_val or 0

        if u_key in ['2 fod', '2_fod'] or u_key.replace('_', ' ') == '2 fod':
            issd_data = fod_total_issued_map.get(item_id, {'ser': 0, 'pws': 0})
        else:
            issd_data = issued_this_month_map.get((u_key, item_id), {'ser': 0, 'pws': 0})
        adapter.issd_ser = issd_data['ser']
        adapter.issd_pws = issd_data['pws']
        adapter.issd_total = adapter.issd_ser + adapter.issd_pws

        # QTY RECD DURING MONTH & FOD DEPOT STOCK: Only for '2 FOD'
        if u_key in ['2 fod', '2_fod'] or u_key.replace('_', ' ') == '2 fod':
            recd_data = fod_recd_map.get(item_id, {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0})
            adapter.recd_ser = recd_data['ser']
            adapter.recd_pws = recd_data['pws']
            adapter.recd_comd = recd_data.get('comd', 0)
            adapter.recd_ihq = recd_data.get('ihq', 0)
            adapter.recd_total = adapter.recd_ser + adapter.recd_pws + adapter.recd_comd + adapter.recd_ihq

            bbf_data = fod_bbf_map.get(item_id, {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0})
            adapter.bbf_ser = bbf_data['ser']
            adapter.bbf_pws = bbf_data['pws']
            adapter.bbf_comd = bbf_data['comd']
            adapter.bbf_ihq = bbf_data['ihq']
            adapter.bbf_total = adapter.bbf_ser + adapter.bbf_pws + adapter.bbf_comd + adapter.bbf_ihq

            stk_data = fod_stk_held_map.get(item_id, {'ser': 0, 'pws': 0, 'comd': 0, 'ihq': 0})
            adapter.stock_ser = stk_data['ser']
            adapter.stock_pws = stk_data['pws']
            adapter.stock_comd = stk_data['comd']
            adapter.stock_ihq = stk_data['ihq']
            adapter.stock_total = stk_data['ser'] + stk_data['pws'] + stk_data['comd'] + stk_data['ihq']
        else:
            adapter.recd_ser = 0
            adapter.recd_pws = 0
            adapter.recd_total = 0

        adapter.deficiency = adapter.unit_auth - adapter.stock_total

        dou_data = dou_aggregate_map.get(adapter.item_id, {'dou_free_ser': 0, 'dou_free_pws': 0, 'unit_stk_ser': 0, 'unit_stk_pws': 0})
        adapter.dou_free_ser = dou_data['dou_free_ser']
        adapter.dou_free_pws = dou_data['dou_free_pws']
        adapter.dou_free_total = adapter.dou_free_ser + adapter.dou_free_pws
        adapter.unit_stk_ser = dou_data['unit_stk_ser']
        adapter.unit_stk_pws = dou_data['unit_stk_pws']
        adapter.unit_stk_total = adapter.unit_stk_ser + adapter.unit_stk_pws
        adapter.condemned_ser = cond_ser_map.get(adapter.item_id, 0)
        adapter.condemned_pws = cond_pws_map.get(adapter.item_id, 0)
        adapter.total_condemnation = condemned_map.get(adapter.item_id, 0)

        ecc_states.append(adapter)

    def ecc_item_sort_key(adapter):
        item_name = getattr(adapter, 'item_name', None) or (adapter.item.item_name if adapter.item else "")
        cat = getattr(adapter, 'category', None) or (adapter.item.category if adapter.item else "")
        cat_upper = cat.upper().replace(" ", "").replace("-", "")
        if "CAT1" in cat_upper or ("CATI" in cat_upper and "CATII" not in cat_upper):
            cat_rank = 1
        elif "CAT2" in cat_upper or "CATII" in cat_upper:
            cat_rank = 2
        else:
            cat_rank = 3
        unit_name = getattr(adapter, 'unit_name', "") or ""
        return (cat_rank, item_name.lower(), unit_name.lower())

    ecc_states.sort(key=ecc_item_sort_key)

    return {
        "ecc_states": ecc_states,
        "filter_type": filter_type,
        "available_months": available_months,
        "available_years": available_years,
        "selected_month_str": selected_month_str,
        "selected_year_str": selected_year_str,
        "selected_period_label": selected_period_label,
        "table_header_banner": table_header_banner,
        "is_div_admin": is_div_admin,
        "user_div": user_div or ""
    }


@scme_bp.route('/monthly-reports')
def monthly_reports():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return redirect("/auth/login")

    is_div_admin = (user_role == "division_admin")
    user_div = session.get("username", "").strip() if is_div_admin else None

    filter_type = request.args.get("type", "month")
    month_param = request.args.get("month", "")
    year_param = request.args.get("year", "")

    payload = build_monthly_reports_payload(filter_type, month_param, year_param, is_div_admin, user_div)

    return render_template(
        '/scme_dashboard/monthly_reports.html',
        **payload
    )


@scme_bp.route('/api/monthly-reports-data')
def api_monthly_reports_data():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "division_admin", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    is_div_admin = (user_role == "division_admin")
    user_div = session.get("username", "").strip() if is_div_admin else None

    filter_type = request.args.get("type", "month")
    month_param = request.args.get("month", "")
    year_param = request.args.get("year", "")

    payload = build_monthly_reports_payload(filter_type, month_param, year_param, is_div_admin, user_div)

    states_json = []
    for s in payload["ecc_states"]:
        states_json.append({
            "id": s.id,
            "item_id": s.item_id,
            "item_name": getattr(s, 'item_name', s.item.item_name if s.item else "Unknown Item"),
            "category": getattr(s, 'category', s.item.category if s.item else ""),
            "scale": s.scale or "1 per indl",
            "auth_auth": s.auth_auth,
            "auth_res": s.auth_res,
            "auth_total": s.auth_total,
            "unit_auth": s.unit_auth,
            "bbf_division": s.bbf_division,
            "bbf_ser": s.bbf_ser,
            "bbf_pws": s.bbf_pws,
            "bbf_total": s.bbf_total,
            "bbf_comd": s.bbf_comd,
            "bbf_ihq": s.bbf_ihq,
            "recd_ser": s.recd_ser,
            "recd_pws": s.recd_pws,
            "recd_comd": getattr(s, 'recd_comd', 0),
            "recd_ihq": getattr(s, 'recd_ihq', 0),
            "recd_total": s.recd_total,
            "issd_ser": s.issd_ser,
            "issd_pws": s.issd_pws,
            "issd_total": s.issd_total,
            "stock_ser": s.stock_ser,
            "stock_pws": s.stock_pws,
            "stock_total": s.stock_total,
            "stock_comd": s.stock_comd,
            "stock_ihq": s.stock_ihq,
            "dou_free_ser": s.dou_free_ser,
            "dou_free_pws": s.dou_free_pws,
            "dou_free_total": s.dou_free_total,
            "unit_stk_ser": s.unit_stk_ser,
            "unit_stk_pws": s.unit_stk_pws,
            "unit_stk_total": s.unit_stk_total,
            "condemned_ser": getattr(s, 'condemned_ser', 0) or 0,
            "condemned_pws": getattr(s, 'condemned_pws', 0) or 0,
            "total_condemnation": getattr(s, 'total_condemnation', 0) or 0,
            "add_knd": s.add_knd,
            "add_tn_model": s.add_tn_model,
            "add_n_area_otg": s.add_n_area_otg,
            "add_idt_ict": s.add_idt_ict,
            "add_remarks_ro_bal": s.add_remarks_ro_bal,
            "tps": s.tps,
            "deficiency": s.deficiency
        })

    return jsonify({
        "success": True,
        "filter_type": payload["filter_type"],
        "selected_period_label": payload["selected_period_label"],
        "table_header_banner": payload["table_header_banner"],
        "selected_month_str": payload["selected_month_str"],
        "selected_year_str": payload["selected_year_str"],
        "available_months": payload["available_months"],
        "available_years": payload["available_years"],
        "ecc_states": states_json
    })




@scme_bp.route('/api/admin-lists')
def api_admin_lists():
    """Return lists of DOU admins and unit admins for SCME dropdown selectors."""
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    def sort_key(name):
        is_619 = 0 if '619' in str(name) else 1
        nums = ''.join(c for c in name if c.isdigit())
        return (is_619, 0 if nums else 1, int(nums) if nums else 0, name.upper())

    # DOU admins — from LoginUser with role division_admin/division + Divs + OrgLadder division
    div_users = LoginUser.query.filter(func.lower(LoginUser.role).in_(['division_admin', 'division'])).all()
    div_records = Divs.query.all()
    div_orgs = OrgLadder.query.filter(func.lower(OrgLadder.type) == 'division').all()

    seen_divs = set()
    dou_list = []
    for candidate in [u.username for u in div_users] + [d.name for d in div_records] + [o.name for o in div_orgs]:
        name = (candidate or '').strip()
        norm = name.lower().replace('_', ' ')
        if name and 'fod' not in norm and norm not in seen_divs:
            seen_divs.add(norm)
            dou_list.append(name)

    dou_list.sort(key=sort_key)

    # Unit admins — from LoginUser with role unit/unit_admin + OrgLadder unit
    unit_users = LoginUser.query.filter(func.lower(LoginUser.role).in_(['unit', 'unit_admin'])).all()
    unit_orgs = OrgLadder.query.filter(func.lower(OrgLadder.type) == 'unit').all()

    seen_units = set()
    unit_list = []
    for candidate in [u.username for u in unit_users] + [o.name for o in unit_orgs]:
        name = (candidate or '').strip()
        norm = name.lower().replace('_', ' ')
        # Ensure we never add any division admin, FOD, or duplicate to unit list
        if name and norm not in seen_divs and 'dou' not in norm and 'fod' not in norm and norm not in seen_units:
            seen_units.add(norm)
            unit_list.append(name)

    # DOU to Child Units map
    dou_units_map = {d: [] for d in dou_list}
    all_orgs = OrgLadder.query.all()
    all_users = LoginUser.query.all()
    user_org_map = {u.username.strip().lower(): u.org_id for u in all_users if u.username and u.org_id}

    for u_name in unit_list:
        parent = resolve_parent_dou_global(u_name, all_orgs=all_orgs, user_org_map=user_org_map)
        matched = None
        for d in dou_list:
            if d.lower().replace('_', ' ') == parent.lower().replace('_', ' '):
                matched = d
                break
        if matched and u_name not in dou_units_map[matched]:
            dou_units_map[matched].append(u_name)

    # Check transactions if any additional child units were issued by DOU
    for d in dou_list:
        d_variants = [d.lower(), d.lower().replace('_', ' '), d.lower().replace(' ', '_')]
        trans_units = Transactions.query.filter(
            func.lower(func.trim(Transactions.issued_by)).in_(d_variants)
        ).with_entities(Transactions.received_by).distinct().all()
        for tu in trans_units:
            if tu and tu[0]:
                tu_val = tu[0].strip()
                tu_norm = tu_val.lower().replace('_', ' ')
                if tu_norm not in seen_divs and 'dou' not in tu_norm and 'fod' not in tu_norm:
                    found_unit = None
                    for un in unit_list:
                        if un.lower().replace('_', ' ') == tu_norm:
                            found_unit = un
                            break
                    target_u = found_unit or tu_val
                    if target_u not in dou_units_map[d]:
                        dou_units_map[d].append(target_u)

    for d in dou_list:
        dou_units_map[d].sort(key=sort_key)

    return jsonify({
        "success": True,
        "dou_admins": dou_list,
        "unit_admins": unit_list,
        "dou_units_map": dou_units_map
    })


@scme_bp.route('/api/dou-report-data')
def api_dou_report_data():
    """SCME-only: return DOU monthly report rows as JSON for inline viewing."""
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    dou_name = request.args.get('dou', '').strip()
    month_param = request.args.get('month', '').strip()

    if not dou_name:
        return jsonify({"success": False, "message": "No DOU specified"}), 400

    # --- Replicate division.py dou_monthly_reports() logic without session changes ---
    from datetime import datetime
    now_date = datetime.now()
    try:
        if month_param:
            sel_year, sel_month = int(month_param.split("-")[0]), int(month_param.split("-")[1])
        else:
            sel_year, sel_month = now_date.year, now_date.month
    except Exception:
        sel_year, sel_month = now_date.year, now_date.month

    first_day_sel = datetime(sel_year, sel_month, 1)
    first_day_next = datetime(sel_year + (1 if sel_month == 12 else 0),
                              1 if sel_month == 12 else sel_month + 1, 1)
    selected_period_label = first_day_sel.strftime('%b %Y').upper()
    selected_month_str = f"{sel_year:04d}-{sel_month:02d}"

    user_div_name = dou_name
    div_names_set = {
        user_div_name.lower().strip(),
        user_div_name.replace('_', ' ').lower().strip(),
        user_div_name.replace(' ', '_').lower().strip()
    }
    possible_div_names = [n for n in div_names_set if n]
    div_names = possible_div_names

    # QTY RECD
    recd_trans = Transactions.query.filter(
        func.lower(func.trim(Transactions.received_by)).in_(possible_div_names),
        Transactions.timestamp >= first_day_sel, Transactions.timestamp < first_day_next
    ).all()
    recd_map = {}
    for t in recd_trans:
        if t.item_id not in recd_map: recd_map[t.item_id] = {'ser': 0, 'pws': 0}
        recd_map[t.item_id]['ser'] += (t.ser or 0)
        recd_map[t.item_id]['pws'] += (t.pws or 0)

    # QTY ISSUED
    issd_trans = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)).in_(possible_div_names),
        Transactions.timestamp >= first_day_sel, Transactions.timestamp < first_day_next
    ).all()
    issd_map = {}
    for t in issd_trans:
        if t.item_id not in issd_map: issd_map[t.item_id] = {'ser': 0, 'pws': 0}
        issd_map[t.item_id]['ser'] += (t.ser or 0)
        issd_map[t.item_id]['pws'] += (t.pws or 0)

    # BBF
    from sqlalchemy import func as sqlfunc
    bbf_recd = db.session.query(Transactions.item_id,
        sqlfunc.sum(Transactions.ser).label('s'), sqlfunc.sum(Transactions.pws).label('p')
    ).filter(sqlfunc.lower(sqlfunc.trim(Transactions.received_by)).in_(possible_div_names),
             Transactions.timestamp < first_day_sel).group_by(Transactions.item_id).all()
    bbf_issd = db.session.query(Transactions.item_id,
        sqlfunc.sum(Transactions.ser).label('s'), sqlfunc.sum(Transactions.pws).label('p')
    ).filter(sqlfunc.lower(sqlfunc.trim(Transactions.issued_by)).in_(possible_div_names),
             Transactions.timestamp < first_day_sel).group_by(Transactions.item_id).all()
    bbf_map = {}
    for r in bbf_recd:
        bbf_map[r.item_id] = {'ser': int(r.s or 0), 'pws': int(r.p or 0)}
    for r in bbf_issd:
        if r.item_id not in bbf_map: bbf_map[r.item_id] = {'ser': 0, 'pws': 0}
        bbf_map[r.item_id]['ser'] -= int(r.s or 0)
        bbf_map[r.item_id]['pws'] -= int(r.p or 0)

    # Posted Strength
    from models.our_items import Divs as DivsModel, Strength as StrengthModel
    div_rec = DivsModel.query.filter(func.lower(func.trim(DivsModel.name)).in_(possible_div_names)).first()
    div_posted_str = (div_rec.posted_strength or div_rec.authorized_strength or 0) if div_rec else 0
    if not div_posted_str:
        s_rec = StrengthModel.query.filter(func.lower(func.trim(StrengthModel.unit_name)).in_(possible_div_names)).first()
        if s_rec: div_posted_str = s_rec.posted_strength or s_rec.authorized_strength or 0

    # Auth
    from models.org_ladder import OrgLadder as OrgLadderModel
    auth_records = ItemAuth.query.filter(func.lower(func.trim(ItemAuth.unit_name)).in_(div_names)).all()
    auth_map = {ar.item_id: ar for ar in auth_records}
    track_records = TrackUnitItems.query.filter(func.lower(func.trim(TrackUnitItems.unit_name)).in_(div_names)).order_by(TrackUnitItems.id.desc()).all()
    track_map = {}
    for tr in track_records:
        if tr.item_id not in track_map: track_map[tr.item_id] = tr

    # Child unit condemnation
    dou_org = OrgLadderModel.query.filter(
        func.lower(func.trim(OrgLadderModel.name)).in_(possible_div_names)
    ).first()
    child_unit_names = []
    if dou_org:
        def _collect_children(node):
            names = []
            for ch in (node.children or []):
                if (ch.type or '').lower() == 'unit':
                    names.extend([ch.name.lower().strip(), ch.name.replace('_',' ').lower().strip(), ch.name.replace(' ','_').lower().strip()])
                else:
                    names.extend(_collect_children(ch))
            return names
        child_unit_names = list(set(_collect_children(dou_org)))

    dou_issued_targets = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)).in_(possible_div_names)
    ).with_entities(Transactions.received_by).distinct().all()
    for row_t in dou_issued_targets:
        if row_t[0]:
            c_val = row_t[0].strip().lower()
            child_unit_names.extend([c_val, c_val.replace('_',' '), c_val.replace(' ','_')])
    child_unit_names = list(set([n for n in child_unit_names if n]))

    unit_stk_map = {}
    if child_unit_names:
        child_recd = Transactions.query.filter(
            func.lower(func.trim(Transactions.issued_by)).in_(possible_div_names),
            func.lower(func.trim(Transactions.received_by)).in_(child_unit_names),
            Transactions.timestamp < first_day_next
        ).all()
        for t in child_recd:
            if t.item_id not in unit_stk_map: unit_stk_map[t.item_id] = {'ser':0,'pws':0}
            unit_stk_map[t.item_id]['ser'] += (t.ser or 0)
            unit_stk_map[t.item_id]['pws'] += (t.pws or 0)
        child_issd = Transactions.query.filter(
            func.lower(func.trim(Transactions.issued_by)).in_(child_unit_names),
            Transactions.timestamp < first_day_next
        ).all()
        for t in child_issd:
            if t.item_id in unit_stk_map:
                unit_stk_map[t.item_id]['ser'] = max(0, unit_stk_map[t.item_id]['ser'] - (t.ser or 0))
                unit_stk_map[t.item_id]['pws'] = max(0, unit_stk_map[t.item_id]['pws'] - (t.pws or 0))

    cond_ser_map = {}; cond_pws_map = {}
    if child_unit_names:
        child_track = TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)).in_(child_unit_names)
        ).all()
        for ctr in child_track:
            c_date = getattr(ctr, 'condemnation_date', None)
            if c_date and c_date >= first_day_next: continue
            cond_ser_map[ctr.item_id] = cond_ser_map.get(ctr.item_id, 0) + (ctr.condemned_ser or 0)
            cond_pws_map[ctr.item_id] = cond_pws_map.get(ctr.item_id, 0) + (ctr.condemned_pws or 0)

    all_items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').all()
    def cat_sort_key(item):
        cat = (item.category or "").upper().replace(" ","").replace("-","")
        if "CAT1" in cat or ("CATI" in cat and "CATII" not in cat): return (1, (item.item_name or "").lower())
        if "CAT2" in cat or "CATII" in cat: return (2, (item.item_name or "").lower())
        return (3, (item.item_name or "").lower())
    all_items.sort(key=cat_sort_key)

    master_auth_map = {ma.item_id: ma for ma in ItemAuth.query.filter((ItemAuth.unit_name == None) | (ItemAuth.unit_name == '')).all()}

    report_rows = []
    for item in all_items:
        tr = track_map.get(item.id)
        ar = auth_map.get(item.id)
        ma = master_auth_map.get(item.id)

        if ar and ar.auth is not None and ar.auth > 0: auth_val = ar.auth
        elif tr and tr.auth is not None and tr.auth > 0: auth_val = tr.auth
        else: auth_val = 0

        scale_val = "N/A"
        for s_src in [tr, ar, ma]:
            if s_src and getattr(s_src, 'scale', None) and s_src.scale.strip() and s_src.scale.upper() not in ["ECC", ""]:
                scale_val = s_src.scale.strip().upper(); break

        b_ser = max(0, bbf_map.get(item.id, {}).get('ser', 0))
        b_pws = max(0, bbf_map.get(item.id, {}).get('pws', 0))
        r_ser = recd_map.get(item.id, {}).get('ser', 0)
        r_pws = recd_map.get(item.id, {}).get('pws', 0)
        i_ser = issd_map.get(item.id, {}).get('ser', 0)
        i_pws = issd_map.get(item.id, {}).get('pws', 0)
        stk_ser = max(0, b_ser + r_ser - i_ser)
        stk_pws = max(0, b_pws + r_pws - i_pws)
        u_cond_ser = cond_ser_map.get(item.id, 0)
        u_cond_pws = cond_pws_map.get(item.id, 0)
        total_cond = u_cond_ser + u_cond_pws
        u_info = unit_stk_map.get(item.id, {'ser':0,'pws':0})
        u_ser = max(0, u_info.get('ser',0) - u_cond_ser)
        u_pws = max(0, u_info.get('pws',0) - u_cond_pws)
        u_total = u_ser + u_pws
        tot_ser = u_ser + stk_ser; tot_pws = u_pws + stk_pws; tot_total = tot_ser + tot_pws
        sur_defi = auth_val - tot_total

        report_rows.append({
            "item_name": item.item_name,
            "au": getattr(item, 'a_u', 'Nos') or 'Nos',
            "scale": scale_val,
            "auth": auth_val,
            "bbf_ser": b_ser, "bbf_pws": b_pws,
            "recd_ser": r_ser, "recd_pws": r_pws,
            "issd_ser": i_ser, "issd_pws": i_pws,
            "stk_ser": stk_ser, "stk_pws": stk_pws, "stk_total": stk_ser + stk_pws,
            "unit_stk_ser": u_ser, "unit_stk_pws": u_pws, "unit_stk_total": u_total,
            "tot_stk_ser": tot_ser, "tot_stk_pws": tot_pws, "tot_stk_total": tot_total,
            "total_condemnation": total_cond,
            "sur_defi": sur_defi
        })

    return jsonify({
        "success": True,
        "dou_name": dou_name,
        "selected_period_label": selected_period_label,
        "selected_month_str": selected_month_str,
        "posted_strength": div_posted_str,
        "report_rows": report_rows
    })


@scme_bp.route('/api/unit-report-data')
def api_unit_report_data():
    """SCME-only: return Unit monthly report rows as JSON for inline viewing."""
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    unit_name = request.args.get('unit', '').strip()
    month_param = request.args.get('month', '').strip()

    if not unit_name:
        return jsonify({"success": False, "message": "No unit specified"}), 400

    from blueprints.unit_monthly_generation import build_unit_monthly_report_payload
    payload = build_unit_monthly_report_payload(unit_name, month_param if month_param else None)

    return jsonify({
        "success": True,
        "unit_name": unit_name,
        "selected_period_label": payload.get("selected_period_label", ""),
        "selected_month_str": payload.get("selected_month_str", ""),
        "posted_strength": payload.get("posted_strength", 0),
        "unit_username": payload.get("unit_username", unit_name),
        "report_rows": payload.get("report_rows", [])
    })


@scme_bp.route('/api/update-div-strength', methods=['POST'])
def update_div_strength():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.get_json() or {}
        div_id = data.get("div_id")
        div_name = (data.get("div_name") or "").strip()
        auth_val = int(data.get("authorized_strength") or 0)
        posted_val = int(data.get("posted_strength") or 0)

        unit_rec = None
        if div_id:
            unit_rec = Divs.query.get(div_id)
        if not unit_rec and div_name:
            unit_rec = Divs.query.filter(
                db.func.lower(db.func.trim(Divs.name)) == div_name.lower()
            ).first()

        if not unit_rec:
            return jsonify({"success": False, "message": "Division not found."}), 404

        unit_rec.authorized_strength = auth_val
        unit_rec.posted_strength = posted_val

        # Also update Strength model record if present
        s_rec = Strength.query.filter(
            db.func.lower(db.func.trim(Strength.unit_name)) == unit_rec.name.lower().strip()
        ).first()
        if s_rec:
            s_rec.authorized_strength = auth_val
            s_rec.posted_strength = posted_val
        else:
            s_rec = Strength(unit_name=unit_rec.name.strip(), posted_strength=posted_val, authorized_strength=auth_val)
            db.session.add(s_rec)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Strengths for {unit_rec.name.replace('_', ' ').upper()} updated successfully!",
            "authorized_strength": auth_val,
            "posted_strength": posted_val
        }), 200

    except Exception as e:
        db.session.rollback()
        print("Error updating division strength:", e)
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/get-all-units', methods=['GET'])
def api_get_all_units():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    all_orgs = OrgLadder.query.all()
    all_users = LoginUser.query.all()
    user_org_map = {u.username.strip().lower(): u.org_id for u in all_users if u.username and u.org_id}

    dous = []
    dou_units_map = {}

    # 1. Identify all DOUs / Divisions (excluding ORD and 2_FOD)
    for o in all_orgs:
        t = (o.type or '').strip().lower()
        n = (o.name or '').strip()
        if not n or n.upper() in ['ORD', '2_FOD', '2 FOD']:
            continue
        if t in ['division', 'dou'] or 'dou' in n.lower() or (o.parent and o.parent.name == 'ORD'):
            if n not in dous:
                dous.append(n)
                dou_units_map[n] = []

    div_users = LoginUser.query.filter(LoginUser.role.in_(['division_admin', 'dou_admin'])).all()
    for du in div_users:
        n = du.username.strip()
        if n and n.upper() not in ['ORD', '2_FOD', '2 FOD'] and n not in dou_units_map:
            dous.append(n)
            dou_units_map[n] = []

    dous = sorted(list(set(dous)))

    # Fallback: if no DOUs found, create a default "GENERAL" group
    if not dous:
        dous = ["GENERAL"]
        dou_units_map["GENERAL"] = []

    # 2. For each DOU, collect its child units
    for dou_name in dous:
        node = next((o for o in all_orgs if o.name and o.name.strip().lower() == dou_name.lower()), None)
        child_names = []
        if node:
            def collect_children(curr):
                collected = []
                for ch in (curr.children or []):
                    ch_type = (ch.type or '').strip().lower()
                    if ch_type == 'unit' or not ch.children:
                        if ch.name and ch.name.strip():
                            collected.append(ch.name.strip())
                    else:
                        collected.extend(collect_children(ch))
                return collected
            child_names.extend(collect_children(node))

        # Check LoginUsers with role='unit' under this DOU
        for lu in all_users:
            if lu.role == 'unit':
                p_name = lu.org.parent.name if (lu.org and lu.org.parent) else ""
                if p_name.strip().lower() == dou_name.lower():
                    child_names.append(lu.username.strip())

        # Check TrackUnitItems mapped to this DOU
        for (tu_name,) in db.session.query(TrackUnitItems.unit_name).distinct().all():
            if tu_name:
                resolved_dou = resolve_parent_dou_global(tu_name, all_orgs, user_org_map)
                if resolved_dou.lower() == dou_name.lower():
                    child_names.append(tu_name.strip())

        # Deduplicate and format child units
        deduped = []
        seen = set()
        for cn in child_names:
            if cn.lower() != dou_name.lower() and cn.lower() not in seen:
                seen.add(cn.lower())
                deduped.append({"name": cn, "label": cn})

        # Also add the DOU itself as an option (e.g. for direct DOU issues)
        if dou_name.upper() not in ['ORD', '2_FOD', '2 FOD']:
            deduped.append({"name": dou_name, "label": f"{dou_name} (DOU Main)"})

        dou_units_map[dou_name] = deduped

    # Flat unit_list for backwards compatibility
    unit_list = []
    seen_flat = set()
    for d, u_items in dou_units_map.items():
        for u in u_items:
            if u["name"].lower() not in seen_flat:
                seen_flat.add(u["name"].lower())
                unit_list.append({"name": u["name"], "parent": d})

    unit_list.sort(key=lambda x: x["name"])

    return jsonify({
        "success": True,
        "dous": dous,
        "dou_units_map": dou_units_map,
        "units": unit_list
    })


@scme_bp.route('/api/stocked-items', methods=['GET'])
def api_get_stocked_items():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        # Items with quantity > 0 in fod_stock_table
        stocked_records = db.session.query(
            FodStock.item_id,
            func.sum(FodStock.quantity).label('total_qty'),
            func.sum(FodStock.ser).label('total_ser'),
            func.sum(FodStock.pws).label('total_pws')
        ).group_by(FodStock.item_id).having(func.sum(FodStock.quantity) > 0).all()

        item_ids = [r.item_id for r in stocked_records]
        items = ScmeItems.query.filter(ScmeItems.id.in_(item_ids)).order_by(ScmeItems.item_name).all()
        stock_map = {r.item_id: {"total": int(r.total_qty or 0), "ser": int(r.total_ser or 0), "pws": int(r.total_pws or 0)} for r in stocked_records}

        result = []
        for it in items:
            s_info = stock_map.get(it.id, {"total": 0, "ser": 0, "pws": 0})
            result.append({
                "id": it.id,
                "name": it.item_name,
                "category": it.category or "General",
                "total": s_info["total"],
                "ser": s_info["ser"],
                "pws": s_info["pws"]
            })

        categories = sorted(list(set(r["category"] for r in result)))
        return jsonify({"success": True, "items": result, "categories": categories})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/direct-issue-to-unit', methods=['POST'])
def api_direct_issue_to_unit():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "super_admin"]:
        return jsonify({"success": False, "message": "Unauthorized: Only 2_FOD or Super Admin can issue directly to unit."}), 403

    try:
        data = request.get_json() or {}
        unit_name = (data.get("unit_name") or "").strip()
        item_id = data.get("item_id")
        stock_type = (data.get("stock_type") or "FREE STK").strip().upper()
        remarks = (data.get("remarks") or "").strip()

        try:
            val_ser = int(data.get("ser") or 0)
            val_pws = int(data.get("pws") or 0)
            if val_ser < 0 or val_pws < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "SER and PWS must be non-negative integers."}), 400

        val_total = val_ser + val_pws
        if not unit_name:
            return jsonify({"success": False, "message": "Target Unit is required."}), 400
        if not item_id:
            return jsonify({"success": False, "message": "Item selection is required."}), 400
        if val_total <= 0:
            return jsonify({"success": False, "message": "Please enter a quantity to issue (SER or PWS)."}), 400

        try:
            item_id_val = int(item_id)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid item ID."}), 400

        item = ScmeItems.query.get(item_id_val)
        if not item:
            return jsonify({"success": False, "message": "Selected item not found."}), 404

        # Validate available stock in FodStock
        fod_total = db.session.query(func.sum(FodStock.quantity)).filter_by(item_id=item_id_val).scalar() or 0
        fod_ser = db.session.query(func.sum(FodStock.ser)).filter_by(item_id=item_id_val).scalar() or 0
        fod_pws = db.session.query(func.sum(FodStock.pws)).filter_by(item_id=item_id_val).scalar() or 0

        if fod_total < val_total:
            return jsonify({"success": False, "message": f"Requested quantity ({val_total}) exceeds available FOD stock ({fod_total})."}), 400
        if val_ser > fod_ser:
            return jsonify({"success": False, "message": f"Requested SER ({val_ser}) exceeds available FOD SER stock ({fod_ser})."}), 400
        if val_pws > fod_pws:
            return jsonify({"success": False, "message": f"Requested PWS ({val_pws}) exceeds available FOD PWS stock ({fod_pws})."}), 400

        now_dt = datetime.now()

        # Deduct from FodStock (FIFO order)
        rem_ser_to_deduct = val_ser
        rem_pws_to_deduct = val_pws
        fod_records = FodStock.query.filter_by(item_id=item_id_val).order_by(FodStock.created_at.asc(), FodStock.id.asc()).all()

        for fod in fod_records:
            if rem_ser_to_deduct > 0 and (fod.ser or 0) > 0:
                ded_ser = min(fod.ser, rem_ser_to_deduct)
                fod.ser -= ded_ser
                rem_ser_to_deduct -= ded_ser

            if rem_pws_to_deduct > 0 and (fod.pws or 0) > 0:
                ded_pws = min(fod.pws, rem_pws_to_deduct)
                fod.pws -= ded_pws
                rem_pws_to_deduct -= ded_pws

            fod.quantity = (fod.ser or 0) + (fod.pws or 0)
            if rem_ser_to_deduct <= 0 and rem_pws_to_deduct <= 0:
                break

        # Record in Transactions table: issued_by = '2_FOD', received_by = unit_name
        tx = Transactions(
            issued_by=session.get("username") or "2_FOD",
            received_by=unit_name,
            item_id=item_id_val,
            ser=val_ser,
            pws=val_pws,
            type=stock_type,
            remarks=remarks or "Direct Issue from 2_FOD to Unit",
            timestamp=now_dt
        )
        db.session.add(tx)

        # Update / Insert TrackUnitItems for the unit
        track_rec = TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)) == unit_name.lower().strip(),
            TrackUnitItems.item_id == item_id_val
        ).first()

        if track_rec:
            track_rec.available_ser = (track_rec.available_ser or 0) + val_ser
            track_rec.available_pws = (track_rec.available_pws or 0) + val_pws
            track_rec.available_res = (track_rec.available_ser or 0) + (track_rec.available_pws or 0)
            track_rec.held = track_rec.calc_held()
            track_rec.ser = (track_rec.ser or 0) + val_ser
            track_rec.pws = (track_rec.pws or 0) + val_pws
            if track_rec.held_pws is not None:
                track_rec.held_pws = (track_rec.held_pws or 0) + val_pws
            track_rec.issued_at = now_dt
        else:
            track_rec = TrackUnitItems(
                unit_name=unit_name,
                item_id=item_id_val,
                scale="100%",
                auth=0,
                held=val_total,
                ser=val_ser,
                pws=val_pws,
                held_pws=val_pws,
                available_ser=val_ser,
                available_pws=val_pws,
                available_res=val_total,
                issued_at=now_dt
            )
            track_rec.held = track_rec.calc_held()
            db.session.add(track_rec)

        # Update ScmeIssuedItems for unit
        issued_rec = ScmeIssuedItems.query.filter(
            func.lower(func.trim(ScmeIssuedItems.unit_name)) == unit_name.lower().strip(),
            ScmeIssuedItems.item_id == item_id_val
        ).first()

        if issued_rec:
            issued_rec.held = (issued_rec.held or 0) + val_total
            issued_rec.deficiency = max(0, (issued_rec.unit_authorized or 0) - (issued_rec.held or 0))
        else:
            issued_rec = ScmeIssuedItems(
                unit_name=unit_name,
                item_id=item_id_val,
                a_u="Nos",
                unit_authorized=0,
                scale="100%",
                held=val_total,
                deficiency=0
            )
            db.session.add(issued_rec)

        # Send notification to unit
        try:
            notif = Notification(
                title="Direct Stock Issued from 2 FOD",
                message=f"2_FOD issued item '{item.item_name}' (SER: {val_ser}, PWS: {val_pws}) directly to your unit.",
                sender_name=session.get("username") or "2_FOD",
                target_user=unit_name,
                target_role="unit",
                item_id=item_id_val
            )
            db.session.add(notif)
        except Exception:
            pass

        # ActionLog
        try:
            log_entry = ActionLog(
                user_id=session.get("user_id"),
                username=session.get("username", "Unknown"),
                role=session.get("role", "scme"),
                action_type="CREATE",
                module="Direct Issue",
                action_description=f"Direct issued item '{item.item_name}' (SER: {val_ser}, PWS: {val_pws}) to {unit_name}",
                timestamp=now_dt
            )
            db.session.add(log_entry)
        except Exception:
            pass

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Successfully issued {val_total} units ({val_ser} SER, {val_pws} PWS) of '{item.item_name}' directly to {unit_name}!"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@scme_bp.route('/api/check-dou-delete-status')
def api_check_dou_delete_status():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    dou_name = request.args.get('dou_name', '').strip()
    if not dou_name:
        return jsonify({"success": False, "message": "DOU name required"}), 400

    dou_variants = [
        dou_name,
        dou_name.lower(),
        dou_name.upper(),
        dou_name.replace(' ', '_'),
        dou_name.replace('_', ' '),
        dou_name.lower().replace(' ', '_'),
        dou_name.lower().replace('_', ' ')
    ]
    dou_variants_lower = list(set([v.lower().strip() for v in dou_variants]))

    # 1. Check OrgLadder
    all_orgs = OrgLadder.query.all()
    dou_org = None
    for o in all_orgs:
        if o.name and o.name.strip().lower() in dou_variants_lower and (o.type or '').lower() == 'division':
            dou_org = o
            break

    child_units = set()
    if dou_org:
        for o in all_orgs:
            if o.parent_id == dou_org.id and (o.type or '').lower() == 'unit' and o.name:
                child_units.add(o.name.strip())

    # 2. Check LoginUser
    all_users = LoginUser.query.all()
    user_org_map = {u.username.strip().lower(): u.org_id for u in all_users if u.username and u.org_id}
    unit_users = [u for u in all_users if (u.role or '').lower() in ['unit', 'unit_admin']]
    for u in unit_users:
        u_name = u.username.strip()
        parent = resolve_parent_dou_global(u_name, all_orgs=all_orgs, user_org_map=user_org_map)
        if parent and parent.lower().replace('_', ' ') in [v.replace('_', ' ') for v in dou_variants_lower]:
            child_units.add(u_name)

    # 3. Check Transactions
    trans_units = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)).in_(dou_variants_lower)
    ).with_entities(Transactions.received_by).distinct().all()
    for tu in trans_units:
        if tu and tu[0]:
            tu_val = tu[0].strip()
            tu_norm = tu_val.lower().replace('_', ' ')
            if 'dou' not in tu_norm and 'fod' not in tu_norm:
                child_units.add(tu_val)

    sorted_child_units = sorted(list(child_units), key=lambda x: (
        int(''.join(c for c in x if c.isdigit())) if any(c.isdigit() for c in x) else 9999,
        x.upper()
    ))

    # Check if the DOU itself holds any equipment in TrackUnitItems, TPS, or Issued
    dou_track = TrackUnitItems.query.filter(
        func.lower(func.trim(TrackUnitItems.unit_name)).in_(dou_variants_lower)
    ).all()
    dou_held = sum((tr.held or 0) + (tr.ser or 0) + (tr.pws or 0) for tr in dou_track)

    dou_tps = UnitTpsStock.query.filter(
        func.lower(func.trim(UnitTpsStock.unit_name)).in_(dou_variants_lower)
    ).all()
    dou_held += sum((t.tps_ser or 0) + (t.tps_pws or 0) for t in dou_tps)

    dou_issued = ScmeIssuedItems.query.filter(
        func.lower(func.trim(ScmeIssuedItems.unit_name)).in_(dou_variants_lower)
    ).all()
    dou_held += sum((ir.held or 0) for ir in dou_issued)

    has_child_units = len(sorted_child_units) > 0
    can_delete = (not has_child_units) and (dou_held == 0)

    return jsonify({
        "success": True,
        "dou_name": dou_name,
        "has_child_units": has_child_units,
        "child_units": sorted_child_units,
        "total_held": dou_held,
        "can_delete": can_delete,
        "message": f"Found {len(sorted_child_units)} child unit(s) under {dou_name}." if has_child_units else ("DOU holds equipment." if dou_held > 0 else f"DOU '{dou_name}' has 0 child units and 0 equipment, ready for permanent deletion.")
    })


@scme_bp.route('/api/check-unit-delete-status')
def api_check_unit_delete_status():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    unit_name = request.args.get('unit_name', '').strip()
    if not unit_name:
        return jsonify({"success": False, "message": "Unit name required"}), 400

    unit_variants = [
        unit_name,
        unit_name.lower(),
        unit_name.upper(),
        unit_name.replace(' ', '_'),
        unit_name.replace('_', ' '),
        unit_name.lower().replace(' ', '_'),
        unit_name.lower().replace('_', ' ')
    ]
    unit_variants_lower = list(set([v.lower().strip() for v in unit_variants]))

    # Check stock in TrackUnitItems
    track_records = TrackUnitItems.query.filter(
        func.lower(func.trim(TrackUnitItems.unit_name)).in_(unit_variants_lower)
    ).all()

    held_items = []
    total_held = 0

    for tr in track_records:
        rec_held = (tr.held or 0)
        rec_ser = (tr.ser or 0)
        rec_pws = (tr.pws or 0)
        calc_h = tr.calc_held() if hasattr(tr, 'calc_held') else (rec_ser + rec_pws)
        actual_held = max(rec_held, calc_h)
        if actual_held > 0 or rec_ser > 0 or rec_pws > 0:
            item_name = tr.item.item_name if (tr.item and hasattr(tr.item, 'item_name')) else f"Item #{tr.item_id}"
            held_items.append({
                "item_name": item_name,
                "held": actual_held,
                "ser": rec_ser,
                "pws": rec_pws
            })
            total_held += actual_held

    # Check stock in UnitTpsStock
    tps_records = UnitTpsStock.query.filter(
        func.lower(func.trim(UnitTpsStock.unit_name)).in_(unit_variants_lower)
    ).all()
    for tps in tps_records:
        tps_ser = tps.tps_ser or 0
        tps_pws = tps.tps_pws or 0
        if tps_ser > 0 or tps_pws > 0:
            item_name = f"TPS Item #{tps.item_id}"
            held_items.append({
                "item_name": item_name,
                "held": tps_ser + tps_pws,
                "ser": tps_ser,
                "pws": tps_pws
            })
            total_held += (tps_ser + tps_pws)

    # Check stock in ScmeIssuedItems
    issued_records = ScmeIssuedItems.query.filter(
        func.lower(func.trim(ScmeIssuedItems.unit_name)).in_(unit_variants_lower)
    ).all()
    for sc_rec in issued_records:
        sc_held = sc_rec.held or 0
        if sc_held > 0:
            item_name = sc_rec.item.item_name if (sc_rec.item and hasattr(sc_rec.item, 'item_name')) else f"Issued Item #{sc_rec.item_id}"
            if not any(hi['item_name'] == item_name for hi in held_items):
                held_items.append({
                    "item_name": item_name,
                    "held": sc_held,
                    "ser": sc_held,
                    "pws": 0
                })
                total_held += sc_held

    can_delete = (total_held == 0)

    return jsonify({
        "success": True,
        "unit_name": unit_name,
        "can_delete": can_delete,
        "total_held": total_held,
        "held_items": held_items,
        "message": f"Unit holds {total_held} item(s)." if total_held > 0 else "Unit holds 0 equipment and can be deleted."
    })


@scme_bp.route('/api/delete-unit', methods=['POST'])
def api_delete_unit():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    unit_name = (data.get('unit_name') or '').strip()
    if not unit_name:
        return jsonify({"success": False, "message": "Unit name is required"}), 400

    unit_variants = [
        unit_name,
        unit_name.lower(),
        unit_name.upper(),
        unit_name.replace(' ', '_'),
        unit_name.replace('_', ' '),
        unit_name.lower().replace(' ', '_'),
        unit_name.lower().replace('_', ' ')
    ]
    unit_variants_lower = list(set([v.lower().strip() for v in unit_variants]))

    # 1. STRICT SAFETY CHECK: Verify unit currently holds 0 equipment
    track_records = TrackUnitItems.query.filter(
        func.lower(func.trim(TrackUnitItems.unit_name)).in_(unit_variants_lower)
    ).all()

    total_held = sum((tr.held or 0) for tr in track_records)
    total_ser = sum((tr.ser or 0) for tr in track_records)
    total_pws = sum((tr.pws or 0) for tr in track_records)

    tps_records = UnitTpsStock.query.filter(
        func.lower(func.trim(UnitTpsStock.unit_name)).in_(unit_variants_lower)
    ).all()
    total_tps = sum((t.tps_ser or 0) + (t.tps_pws or 0) for t in tps_records)

    issued_records = ScmeIssuedItems.query.filter(
        func.lower(func.trim(ScmeIssuedItems.unit_name)).in_(unit_variants_lower)
    ).all()
    total_issued = sum((ir.held or 0) for ir in issued_records)

    grand_total_held = total_held + total_ser + total_pws + total_tps + total_issued
    if grand_total_held > 0:
        return jsonify({
            "success": False,
            "message": f"Deletion blocked: Unit '{unit_name}' currently holds {grand_total_held} item(s) in equipment/stock. All stock must be returned before deleting this unit."
        }), 400

    # 2. REMOVE FROM EVERYWHERE
    try:
        # A. Find and delete OrgLadder entry and related LoginUsers
        unit_orgs = OrgLadder.query.filter(
            func.lower(func.trim(OrgLadder.name)).in_(unit_variants_lower),
            func.lower(OrgLadder.type) == 'unit'
        ).all()
        unit_org_ids = [o.id for o in unit_orgs]

        # Delete LoginUsers by org_id or username
        users_to_del = LoginUser.query.filter(
            (func.lower(func.trim(LoginUser.username)).in_(unit_variants_lower)) |
            (LoginUser.org_id.in_(unit_org_ids) if unit_org_ids else False)
        ).all()
        for u in users_to_del:
            Notification.query.filter(Notification.target_user == u.username).delete(synchronize_session=False)
            db.session.delete(u)

        # Delete OrgLadder records
        for o in unit_orgs:
            db.session.delete(o)

        # B. Delete from TrackUnitItems
        TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)).in_(unit_variants_lower)
        ).delete(synchronize_session=False)

        # C. Delete from UnitTpsStock
        UnitTpsStock.query.filter(
            func.lower(func.trim(UnitTpsStock.unit_name)).in_(unit_variants_lower)
        ).delete(synchronize_session=False)

        # D. Delete from ItemAuth
        ItemAuth.query.filter(
            func.lower(func.trim(ItemAuth.unit_name)).in_(unit_variants_lower)
        ).delete(synchronize_session=False)

        # E. Delete from ScmeIssuedItems
        ScmeIssuedItems.query.filter(
            func.lower(func.trim(ScmeIssuedItems.unit_name)).in_(unit_variants_lower)
        ).delete(synchronize_session=False)

        # F. Delete from Strength (unit_strength)
        Strength.query.filter(
            func.lower(func.trim(Strength.unit_name)).in_(unit_variants_lower)
        ).delete(synchronize_session=False)

        # G. Delete from ArmyPersonnel
        ArmyPersonnel.query.filter(
            func.lower(func.trim(ArmyPersonnel.unit_name)).in_(unit_variants_lower)
        ).delete(synchronize_session=False)

        # H. Delete from CondemnationRequest
        CondemnationRequest.query.filter(
            func.lower(func.trim(CondemnationRequest.unit_name)).in_(unit_variants_lower)
        ).delete(synchronize_session=False)

        # I. Delete from Transactions (where unit was receiver or issuer)
        Transactions.query.filter(
            (func.lower(func.trim(Transactions.received_by)).in_(unit_variants_lower)) |
            (func.lower(func.trim(Transactions.issued_by)).in_(unit_variants_lower))
        ).delete(synchronize_session=False)

        # J. Log audit trail
        try:
            log_entry = ActionLog(
                user_id=session.get("user_id"),
                username=session.get("username", "Unknown"),
                role=session.get("role", "scme"),
                action_type="DELETE",
                module="Unit Management",
                details=f"Permanently deleted unit '{unit_name}' and all associated records from system."
            )
            db.session.add(log_entry)
        except Exception:
            pass

        db.session.commit()

        return jsonify({
            "success": True,
            "unit_name": unit_name,
            "message": f"Unit '{unit_name.replace('_', ' ').upper()}' has been completely removed from everywhere!"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error deleting unit: {str(e)}"}), 500


@scme_bp.route('/api/delete-dou', methods=['POST'])
def api_delete_dou():
    user_role = session.get("role")
    if "user_id" not in session or user_role not in ["scme", "super_admin", "brigade_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    dou_name = (data.get('dou_name') or '').strip()
    if not dou_name:
        return jsonify({"success": False, "message": "DOU name is required"}), 400

    dou_variants = [
        dou_name,
        dou_name.lower(),
        dou_name.upper(),
        dou_name.replace(' ', '_'),
        dou_name.replace('_', ' '),
        dou_name.lower().replace(' ', '_'),
        dou_name.lower().replace('_', ' ')
    ]
    dou_variants_lower = list(set([v.lower().strip() for v in dou_variants]))

    # 1. STRICT SAFETY CHECK: Verify DOU has 0 child units
    all_orgs = OrgLadder.query.all()
    dou_orgs = [o for o in all_orgs if o.name and o.name.strip().lower() in dou_variants_lower]
    dou_org_ids = [o.id for o in dou_orgs]

    child_units = set()
    for o in all_orgs:
        if o.parent_id in dou_org_ids and (o.type or '').lower() == 'unit' and o.name:
            child_units.add(o.name.strip())

    all_users = LoginUser.query.all()
    user_org_map = {u.username.strip().lower(): u.org_id for u in all_users if u.username and u.org_id}
    unit_users = [u for u in all_users if (u.role or '').lower() in ['unit', 'unit_admin']]
    for u in unit_users:
        u_name = u.username.strip()
        parent = resolve_parent_dou_global(u_name, all_orgs=all_orgs, user_org_map=user_org_map)
        if parent and parent.lower().replace('_', ' ') in [v.replace('_', ' ') for v in dou_variants_lower]:
            child_units.add(u_name)

    if child_units:
        return jsonify({
            "success": False,
            "message": f"Deletion blocked: DOU '{dou_name}' still has {len(child_units)} child unit(s). All child units must be deleted first."
        }), 400

    # 2. Check if DOU holds any equipment
    dou_track = TrackUnitItems.query.filter(
        func.lower(func.trim(TrackUnitItems.unit_name)).in_(dou_variants_lower)
    ).all()
    total_held = sum((tr.held or 0) + (tr.ser or 0) + (tr.pws or 0) for tr in dou_track)

    dou_tps = UnitTpsStock.query.filter(
        func.lower(func.trim(UnitTpsStock.unit_name)).in_(dou_variants_lower)
    ).all()
    total_held += sum((t.tps_ser or 0) + (t.tps_pws or 0) for t in dou_tps)

    dou_issued = ScmeIssuedItems.query.filter(
        func.lower(func.trim(ScmeIssuedItems.unit_name)).in_(dou_variants_lower)
    ).all()
    total_held += sum((ir.held or 0) for ir in dou_issued)

    if total_held > 0:
        return jsonify({
            "success": False,
            "message": f"Deletion blocked: DOU '{dou_name}' holds {total_held} equipment in stock. Return or transfer stock first."
        }), 400

    # 3. REMOVE DOU FROM EVERYWHERE
    try:
        # A. Delete from Divs (Units table)
        Divs.query.filter(
            func.lower(func.trim(Divs.name)).in_(dou_variants_lower)
        ).delete(synchronize_session=False)

        # B. Delete OrgLadder entries and associated LoginUsers
        users_to_del = LoginUser.query.filter(
            (func.lower(func.trim(LoginUser.username)).in_(dou_variants_lower)) |
            (LoginUser.org_id.in_(dou_org_ids) if dou_org_ids else False) |
            ((LoginUser.role.in_(['dou', 'dou_admin', 'div_admin', 'division_admin'])) & 
             (func.lower(func.trim(LoginUser.username)).in_(dou_variants_lower)))
        ).all()
        for u in users_to_del:
            Notification.query.filter(Notification.target_user == u.username).delete(synchronize_session=False)
            db.session.delete(u)

        for o in dou_orgs:
            db.session.delete(o)

        # C. Delete from TrackUnitItems
        TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)).in_(dou_variants_lower)
        ).delete(synchronize_session=False)

        # D. Delete from UnitTpsStock
        UnitTpsStock.query.filter(
            func.lower(func.trim(UnitTpsStock.unit_name)).in_(dou_variants_lower)
        ).delete(synchronize_session=False)

        # E. Delete from ItemAuth
        ItemAuth.query.filter(
            func.lower(func.trim(ItemAuth.unit_name)).in_(dou_variants_lower)
        ).delete(synchronize_session=False)

        # F. Delete from ScmeIssuedItems
        ScmeIssuedItems.query.filter(
            func.lower(func.trim(ScmeIssuedItems.unit_name)).in_(dou_variants_lower)
        ).delete(synchronize_session=False)

        # G. Delete from Strength
        Strength.query.filter(
            func.lower(func.trim(Strength.unit_name)).in_(dou_variants_lower)
        ).delete(synchronize_session=False)

        # H. Delete from ArmyPersonnel
        ArmyPersonnel.query.filter(
            func.lower(func.trim(ArmyPersonnel.unit_name)).in_(dou_variants_lower)
        ).delete(synchronize_session=False)

        # I. Delete from CondemnationRequest
        CondemnationRequest.query.filter(
            func.lower(func.trim(CondemnationRequest.unit_name)).in_(dou_variants_lower)
        ).delete(synchronize_session=False)

        # J. Delete from Transactions (where DOU was receiver or issuer)
        Transactions.query.filter(
            (func.lower(func.trim(Transactions.received_by)).in_(dou_variants_lower)) |
            (func.lower(func.trim(Transactions.issued_by)).in_(dou_variants_lower))
        ).delete(synchronize_session=False)

        # K. Log audit trail
        try:
            log_entry = ActionLog(
                user_id=session.get("user_id"),
                username=session.get("username", "Unknown"),
                role=session.get("role", "scme"),
                action_type="DELETE",
                module="DOU Management",
                details=f"Permanently deleted DOU '{dou_name}' and all associated records from system."
            )
            db.session.add(log_entry)
        except Exception:
            pass

        db.session.commit()

        return jsonify({
            "success": True,
            "dou_name": dou_name,
            "message": f"DOU '{dou_name.replace('_', ' ').upper()}' has been completely removed from everywhere!"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error deleting DOU: {str(e)}"}), 500