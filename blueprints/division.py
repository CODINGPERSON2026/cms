from imports import *
from extensions import db, csrf
from models import LoginUser, Notification
from models.our_items import OurItems, ItemRequestTable, Strength, ScmeItems, ScmeIssuedItems, Units, Divs, TrackUnitItems, Transactions, UnitTpsStock, ItemAuth, CondemnationRequest
from models.org_ladder import OrgLadder
from validation import get_parent_admin,has_special_characters
from datetime import datetime, timezone, timedelta
from sqlalchemy import text, func

div_bp = Blueprint("div",__name__,url_prefix='/division_admin')


def _ensure_track_unit_items_migrated():
    """Ensure track_unit_items table exists, add ser/pws columns if missing, and drop legacy columns from unit_strength table."""
    try:
        db.create_all()
        # Ensure ser and pws columns exist in track_unit_items table
        track_cols = [c[0] for c in db.session.execute(text("DESCRIBE `track_unit_items`;")).fetchall()]
        if "ser" not in track_cols:
            try:
                db.session.execute(text("ALTER TABLE `track_unit_items` ADD COLUMN `ser` INT DEFAULT 0 NOT NULL;"))
            except Exception:
                pass
        if "pws" not in track_cols:
            try:
                db.session.execute(text("ALTER TABLE `track_unit_items` ADD COLUMN `pws` INT DEFAULT 0 NOT NULL;"))
            except Exception:
                pass

        # Ensure salvage_rv and destruction_certificate exist in condemnation_requests table
        try:
            cond_cols = [c[0] for c in db.session.execute(text("DESCRIBE `condemnation_requests`;")).fetchall()]
            if "salvage_rv" not in cond_cols:
                try:
                    db.session.execute(text("ALTER TABLE `condemnation_requests` ADD COLUMN `salvage_rv` TINYINT(1) DEFAULT 0 NOT NULL;"))
                except Exception:
                    pass
            if "destruction_certificate" not in cond_cols:
                try:
                    db.session.execute(text("ALTER TABLE `condemnation_requests` ADD COLUMN `destruction_certificate` TINYINT(1) DEFAULT 0 NOT NULL;"))
                except Exception:
                    pass
        except Exception:
            pass

        # Drop legacy item columns from unit_strength table in MySQL if present
        cols = [c[0] for c in db.session.execute(text("DESCRIBE `unit_strength`;")).fetchall()]
        cols_to_drop = [col for col in ["item_id", "held", "issued_at"] if col in cols]
        if cols_to_drop:
            # Drop foreign key constraint if item_id FK exists
            fk_rows = db.session.execute(text(
                "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
                "WHERE TABLE_NAME = 'unit_strength' AND COLUMN_NAME = 'item_id' "
                "AND CONSTRAINT_NAME != 'PRIMARY';"
            )).fetchall()
            for fk in fk_rows:
                try:
                    db.session.execute(text(f"ALTER TABLE `unit_strength` DROP FOREIGN KEY `{fk[0]}`;"))
                except Exception:
                    pass

            for col in cols_to_drop:
                try:
                    db.session.execute(text(f"ALTER TABLE `unit_strength` DROP COLUMN `{col}`;"))
                except Exception:
                    pass

        db.session.commit()
    except Exception as e:
        db.session.rollback()


def _calculate_sub_unit_stock(track_rec, trans_recd_list=None, trans_issd_list=None, auth_val=0):
    """
    Calculates exact held stock (total, ser, pws) and auth/defi for a subordinate unit,
    matching blueprints/unit.py calculation identically.
    Regardless of whether unit received equipment from DOU or direct from 2_FOD.
    """
    recd_ser = sum(t.ser or 0 for t in trans_recd_list) if trans_recd_list else 0
    recd_pws = sum(t.pws or 0 for t in trans_recd_list) if trans_recd_list else 0
    issd_ser = sum(t.ser or 0 for t in trans_issd_list) if trans_issd_list else 0
    issd_pws = sum(t.pws or 0 for t in trans_issd_list) if trans_issd_list else 0

    net_t_ser = max(0, recd_ser - issd_ser)
    net_t_pws = max(0, recd_pws - issd_pws)

    if (net_t_ser + net_t_pws) > 0:
        orig_ser = net_t_ser
        orig_pws = net_t_pws
    elif track_rec:
        avail_s = getattr(track_rec, 'available_ser', 0) or 0
        avail_p = getattr(track_rec, 'available_pws', 0) or 0
        if avail_s > 0 or avail_p > 0:
            orig_ser = avail_s
            orig_pws = avail_p
        else:
            raw_s = getattr(track_rec, 'ser', 0) or 0
            raw_p = getattr(track_rec, 'pws', 0) or 0
            if raw_s > 0 or raw_p > 0:
                orig_ser = raw_s
                orig_pws = raw_p
            elif (getattr(track_rec, 'held', 0) or 0) > 0:
                c_s = getattr(track_rec, 'condemned_ser', 0) or 0
                c_p = getattr(track_rec, 'condemned_pws', 0) or 0
                orig_ser = (getattr(track_rec, 'held', 0) or 0) + c_s + c_p
                orig_pws = 0
            else:
                orig_ser = 0
                orig_pws = 0
    else:
        orig_ser = 0
        orig_pws = 0

    cond_ser = (getattr(track_rec, 'condemned_ser', 0) or 0) if track_rec else 0
    cond_pws = (getattr(track_rec, 'condemned_pws', 0) or 0) if track_rec else 0
    total_condemned = cond_ser + cond_pws

    orig_held_total = orig_ser + orig_pws
    total_stock = max(0, orig_held_total - total_condemned)

    # Fallback if orig_held_total was 0, but track_rec has held
    if orig_held_total == 0 and track_rec and (getattr(track_rec, 'held', 0) or 0) > 0:
        total_stock = getattr(track_rec, 'held', 0) or 0

    # Ledger-based condition counts from receipts minus condemnations
    rem_ser = max(0, orig_ser - cond_ser)
    rem_pws = max(0, orig_pws - cond_pws)
    if rem_ser + rem_pws > total_stock:
        if cond_pws > orig_pws:
            rem_ser = max(0, rem_ser - (cond_pws - orig_pws))
        if cond_ser > orig_ser:
            rem_pws = max(0, rem_pws - (cond_ser - orig_ser))

    # If transaction records exist, the transaction ledger is the primary source of truth for SER and PWS
    custom_held_pws = getattr(track_rec, 'held_pws', None) if track_rec else None
    if (orig_ser + orig_pws) > 0:
        dou_ser = rem_ser
        dou_pws = max(0, total_stock - dou_ser)
    elif custom_held_pws is not None and total_stock > 0:
        dou_pws = max(0, min(total_stock, int(custom_held_pws)))
        dou_ser = total_stock - dou_pws
    elif total_stock > 0:
        dou_ser = total_stock
        dou_pws = 0
    else:
        dou_ser = 0
        dou_pws = 0

    auth = auth_val if auth_val is not None else 0
    defi = auth - total_stock

    return {
        "held": total_stock,
        "ser": dou_ser,
        "pws": dou_pws,
        "cond_ser": cond_ser,
        "cond_pws": cond_pws,
        "auth": auth,
        "defi": defi
    }


@div_bp.route('/monthly-reports')
def dou_monthly_reports():
    if "user_id" not in session:
        return redirect('/')

    user = LoginUser.query.get(session["user_id"])
    if not user:
        return redirect('/')

    user_div_name = (user.org.name if (user and user.org and user.org.name) else (session.get("username") or user.username or "DOU")).strip()
    month_param = request.args.get('month')

    now_date = datetime.now()
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

    selected_period_label = first_day_sel.strftime('%b %Y').upper()
    selected_month_str = f"{sel_year:04d}-{sel_month:02d}"

    # 1. QTY RECD: Transactions where received_by matches user_div_name during selected month
    recd_trans = Transactions.query.filter(
        func.lower(func.trim(Transactions.received_by)) == user_div_name.lower(),
        Transactions.timestamp >= first_day_sel,
        Transactions.timestamp < first_day_next
    ).all()
    recd_map = {}
    for t in recd_trans:
        if t.item_id not in recd_map:
            recd_map[t.item_id] = {'ser': 0, 'pws': 0}
        recd_map[t.item_id]['ser'] += (t.ser or 0)
        recd_map[t.item_id]['pws'] += (t.pws or 0)

    # 2. QTY ISSUED: Transactions where issued_by matches user_div_name during selected month
    issd_trans = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)) == user_div_name.lower(),
        Transactions.timestamp >= first_day_sel,
        Transactions.timestamp < first_day_next
    ).all()
    issd_map = {}
    for t in issd_trans:
        if t.item_id not in issd_map:
            issd_map[t.item_id] = {'ser': 0, 'pws': 0}
        issd_map[t.item_id]['ser'] += (t.ser or 0)
        issd_map[t.item_id]['pws'] += (t.pws or 0)

    # 3. BBF (prior to first_day_sel): Receipts minus Issuances prior to month
    bbf_recd = db.session.query(
        Transactions.item_id,
        func.sum(Transactions.ser).label('sum_ser'),
        func.sum(Transactions.pws).label('sum_pws')
    ).filter(
        func.lower(func.trim(Transactions.received_by)) == user_div_name.lower(),
        Transactions.timestamp < first_day_sel
    ).group_by(Transactions.item_id).all()

    bbf_issd = db.session.query(
        Transactions.item_id,
        func.sum(Transactions.ser).label('sum_ser'),
        func.sum(Transactions.pws).label('sum_pws')
    ).filter(
        func.lower(func.trim(Transactions.issued_by)) == user_div_name.lower(),
        Transactions.timestamp < first_day_sel
    ).group_by(Transactions.item_id).all()

    bbf_map = {}
    for r in bbf_recd:
        bbf_map[r.item_id] = {'ser': int(r.sum_ser or 0), 'pws': int(r.sum_pws or 0)}
    for r in bbf_issd:
        if r.item_id not in bbf_map:
            bbf_map[r.item_id] = {'ser': 0, 'pws': 0}
        bbf_map[r.item_id]['ser'] -= int(r.sum_ser or 0)
        bbf_map[r.item_id]['pws'] -= int(r.sum_pws or 0)

    # 4. Items and Authorizations (Posted strength fetched from divs/strength tables)
    div_names_set = {
        user_div_name.lower().strip(),
        user_div_name.replace('_', ' ').lower().strip(),
        user_div_name.replace(' ', '_').lower().strip()
    }
    if user and user.org and user.org.name:
        div_names_set.add(user.org.name.lower().strip())
        div_names_set.add(user.org.name.replace('_', ' ').lower().strip())
        div_names_set.add(user.org.name.replace(' ', '_').lower().strip())
    possible_div_names = [n for n in div_names_set if n]

    div_rec = Divs.query.filter(
        func.lower(func.trim(Divs.name)).in_(possible_div_names)
    ).first()
    div_posted_str = (div_rec.posted_strength or div_rec.authorized_strength or 0) if div_rec else 0
    if not div_posted_str:
        str_rec = Strength.query.filter(
            func.lower(func.trim(Strength.unit_name)).in_(possible_div_names)
        ).first()
        if str_rec:
            div_posted_str = str_rec.posted_strength or str_rec.authorized_strength or 0
    if not div_posted_str and hasattr(TrackUnitItems, 'posted_str'):
        tr_rec = TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)).in_(possible_div_names),
            getattr(TrackUnitItems, 'posted_str') > 0
        ).first()
        if tr_rec:
            div_posted_str = getattr(tr_rec, 'posted_str', 0)

    all_items = ScmeItems.query.filter(func.lower(ScmeItems.type) == 'ecc').all()

    def cat_sort_key(item):
        cat = (item.category or "").upper().replace(" ", "").replace("-", "")
        if "CAT1" in cat or ("CATI" in cat and "CATII" not in cat):
            cat_rank = 1
        elif "CAT2" in cat or "CATII" in cat:
            cat_rank = 2
        else:
            cat_rank = 3
        return (cat_rank, (item.item_name or "").lower())

    all_items.sort(key=cat_sort_key)
    div_names = [
        user_div_name.lower().strip(),
        user_div_name.replace('_', ' ').lower().strip(),
        user_div_name.replace(' ', '_').lower().strip()
    ]

    # Pre-fetch TrackUnitItems records for this division
    track_records = TrackUnitItems.query.filter(
        func.lower(func.trim(TrackUnitItems.unit_name)).in_(div_names)
    ).order_by(TrackUnitItems.id.desc()).all()
    track_map = {}
    for tr in track_records:
        if tr.item_id not in track_map:
            track_map[tr.item_id] = tr

    # Pre-fetch ItemAuth records for this division
    auth_records = ItemAuth.query.filter(
        func.lower(func.trim(ItemAuth.unit_name)).in_(div_names)
    ).all()
    auth_map = {ar.item_id: ar for ar in auth_records}

    # Pre-fetch master ItemAuth scales (where unit_name is null or empty)
    master_auth_records = ItemAuth.query.filter(
        (ItemAuth.unit_name == None) | (ItemAuth.unit_name == '')
    ).all()
    master_auth_map = {ma.item_id: ma for ma in master_auth_records}

    # Pre-fetch any fallback TrackUnitItems scales across the table
    any_track_records = TrackUnitItems.query.filter(
        TrackUnitItems.scale != None,
        TrackUnitItems.scale != '',
        func.lower(func.trim(TrackUnitItems.scale)) != 'ecc'
    ).order_by(TrackUnitItems.id.desc()).all()
    any_track_map = {}
    for atr in any_track_records:
        if atr.item_id not in any_track_map:
            any_track_map[atr.item_id] = atr

    # 5. TOTAL CONDEMNATION: Sum condemned_ser + condemned_pws from all child units of this division
    # Collect child unit names via the org tree
    child_unit_names = []
    if user and user.org:
        def collect_child_unit_names(node):
            names = []
            for child in node.children:
                if child.type and child.type.lower() == 'unit':
                    names.append(child.name.lower().strip())
                    names.append(child.name.replace('_', ' ').lower().strip())
                    names.append(child.name.replace(' ', '_').lower().strip())
                else:
                    names.extend(collect_child_unit_names(child))
            return names
        child_unit_names = list(set(collect_child_unit_names(user.org)))

    # Also include any unit that received items from this DOU in transactions
    dou_issued_targets = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)).in_(possible_div_names)
    ).with_entities(Transactions.received_by).distinct().all()
    for row_t in dou_issued_targets:
        if row_t[0]:
            c_val = row_t[0].strip().lower()
            child_unit_names.append(c_val)
            child_unit_names.append(c_val.replace('_', ' '))
            child_unit_names.append(c_val.replace(' ', '_'))
    child_unit_names = list(set([n for n in child_unit_names if n]))

    # STK HELD BY UNITS: Sum of ser and pws held by child units of current logged-in DOU up to selected month (timestamp < first_day_next)
    unit_stk_map = {}
    if child_unit_names:
        child_recd_trans = Transactions.query.filter(
            func.lower(func.trim(Transactions.received_by)).in_(child_unit_names),
            Transactions.timestamp < first_day_next
        ).all()
        for t in child_recd_trans:
            if t.item_id not in unit_stk_map:
                unit_stk_map[t.item_id] = {'ser': 0, 'pws': 0}
            unit_stk_map[t.item_id]['ser'] += (t.ser or 0)
            unit_stk_map[t.item_id]['pws'] += (t.pws or 0)

        # Subtract any issuances or condemnations made by those child units up to first_day_next
        child_issd_trans = Transactions.query.filter(
            func.lower(func.trim(Transactions.issued_by)).in_(child_unit_names),
            Transactions.timestamp < first_day_next
        ).all()
        for t in child_issd_trans:
            if t.item_id in unit_stk_map:
                unit_stk_map[t.item_id]['ser'] = max(0, unit_stk_map[t.item_id]['ser'] - (t.ser or 0))
                unit_stk_map[t.item_id]['pws'] = max(0, unit_stk_map[t.item_id]['pws'] - (t.pws or 0))

    cond_ser_map = {}
    cond_pws_map = {}
    condemned_map = {}
    if child_unit_names:
        child_track_records = TrackUnitItems.query.filter(
            func.lower(func.trim(TrackUnitItems.unit_name)).in_(child_unit_names)
        ).all()
        for ctr in child_track_records:
            c_date = getattr(ctr, 'condemnation_date', None)
            if c_date and c_date >= first_day_next:
                continue
            iid = ctr.item_id
            c_ser = ctr.condemned_ser or 0
            c_pws = ctr.condemned_pws or 0
            cond_ser_map[iid] = cond_ser_map.get(iid, 0) + c_ser
            cond_pws_map[iid] = cond_pws_map.get(iid, 0) + c_pws
            condemned_map[iid] = condemned_map.get(iid, 0) + c_ser + c_pws

    report_rows = []

    for item in all_items:
        track_rec = track_map.get(item.id)
        auth_rec = auth_map.get(item.id)
        master_auth = master_auth_map.get(item.id)
        any_track_rec = any_track_map.get(item.id)

        # Scale resolution: TrackUnitItems (division-specific) -> ItemAuth (division-specific) -> TrackUnitItems (catalog) -> ItemAuth (master)
        raw_scale = ""
        if track_rec and track_rec.scale and track_rec.scale.strip():
            raw_scale = track_rec.scale.strip()
        elif auth_rec and auth_rec.scale and auth_rec.scale.strip():
            raw_scale = auth_rec.scale.strip()
        elif any_track_rec and any_track_rec.scale and any_track_rec.scale.strip():
            raw_scale = any_track_rec.scale.strip()
        elif master_auth and master_auth.scale and master_auth.scale.strip():
            raw_scale = master_auth.scale.strip()

        if raw_scale.upper() in ["ECC", ""]:
            scale_val = "N/A"
        else:
            scale_val = raw_scale.upper()

        # Auth resolution: ItemAuth -> TrackUnitItems -> 0
        if auth_rec and auth_rec.auth is not None and auth_rec.auth > 0:
            auth_val = auth_rec.auth
        elif track_rec and track_rec.auth is not None and track_rec.auth > 0:
            auth_val = track_rec.auth
        elif auth_rec and auth_rec.auth is not None:
            auth_val = auth_rec.auth
        elif track_rec and track_rec.auth is not None:
            auth_val = track_rec.auth
        else:
            auth_val = 0

        posted_str = div_posted_str

        b_ser = max(0, bbf_map.get(item.id, {}).get('ser', 0))
        b_pws = max(0, bbf_map.get(item.id, {}).get('pws', 0))

        r_ser = recd_map.get(item.id, {}).get('ser', 0)
        r_pws = recd_map.get(item.id, {}).get('pws', 0)

        i_ser = issd_map.get(item.id, {}).get('ser', 0)
        i_pws = issd_map.get(item.id, {}).get('pws', 0)

        stk_ser = b_ser + r_ser - i_ser
        stk_pws = b_pws + r_pws - i_pws
        if stk_ser < 0: stk_ser = 0
        if stk_pws < 0: stk_pws = 0

        u_cond_ser = cond_ser_map.get(item.id, 0)
        u_cond_pws = cond_pws_map.get(item.id, 0)
        total_condemnation = u_cond_ser + u_cond_pws

        u_info = unit_stk_map.get(item.id, {'ser': 0, 'pws': 0})
        orig_u_ser = u_info.get('ser', 0)
        orig_u_pws = u_info.get('pws', 0)

        # STK HELD WITH UNITS: Calculated directly from transaction ledger (receipts - condemnations)
        orig_u_total = orig_u_ser + orig_u_pws
        u_total = max(0, orig_u_total - total_condemnation)

        rem_s = max(0, orig_u_ser - u_cond_ser)
        rem_p = max(0, orig_u_pws - u_cond_pws)
        if rem_s + rem_p > u_total:
            if u_cond_pws > orig_u_pws:
                rem_s = max(0, rem_s - (u_cond_pws - orig_u_pws))
            if u_cond_ser > orig_u_ser:
                rem_p = max(0, rem_p - (u_cond_ser - orig_u_ser))

        if (orig_u_ser + orig_u_pws) > 0:
            u_ser = rem_s
            u_pws = max(0, u_total - u_ser)
        else:
            cust_pws = sum((getattr(ctr, 'held_pws', 0) or 0) for ctr in child_track_records if ctr.item_id == item.id and getattr(ctr, 'held_pws', None) is not None)
            if cust_pws > 0 and u_total > 0:
                u_pws = max(0, min(u_total, cust_pws))
                u_ser = u_total - u_pws
            elif u_total > 0:
                u_ser = u_total
                u_pws = 0
            else:
                u_ser = 0
                u_pws = 0

        tot_stk_ser = u_ser + stk_ser
        tot_stk_pws = u_pws + stk_pws
        tot_stk_total = tot_stk_ser + tot_stk_pws

        total_stk = stk_ser + stk_pws
        # SUR/DEFI = AUTH - TOTAL STOCK (where TOTAL STOCK has condemned items subtracted)
        sur_defi = auth_val - tot_stk_total

        report_rows.append({
            "item_name": item.item_name,
            "au": getattr(item, 'a_u', 'Nos') or 'Nos',
            "scale": scale_val,
            "posted_str": posted_str,
            "auth": auth_val,
            "bbf_ser": b_ser,
            "bbf_pws": b_pws,
            "recd_ser": r_ser,
            "recd_pws": r_pws,
            "issd_ser": i_ser,
            "issd_pws": i_pws,
            "stk_ser": stk_ser,
            "stk_pws": stk_pws,
            "stk_total": total_stk,
            "unit_stk_ser": u_ser,
            "unit_stk_pws": u_pws,
            "unit_stk_total": u_total,
            "tot_stk_ser": tot_stk_ser,
            "tot_stk_pws": tot_stk_pws,
            "tot_stk_total": tot_stk_total,
            "sur_defi": sur_defi,
            "total_condemnation": total_condemnation
        })

    return render_template(
        'Div_Dashboard/dou_monthly_reports.html',
        report_rows=report_rows,
        selected_month_str=selected_month_str,
        selected_period_label=selected_period_label,
        user_div_name=user_div_name,
        posted_strength=div_posted_str
    )


@div_bp.route('/')
def div_home():
    if "user_id" not in session:
        return redirect('/')

    _ensure_track_unit_items_migrated()

    user = LoginUser.query.get(session["user_id"])
    subordinate_units = []

    # Map unit_name to posted/authorized personnel strength from Strength & Units tables
    strength_map = {}
    for s in Strength.query.all():
        if s.unit_name:
            val = s.posted_strength or s.authorized_strength or 0
            k = s.unit_name.lower().strip()
            if val > 0 or k not in strength_map:
                strength_map[k] = val

    for u in Units.query.all():
        if u.name:
            val = u.posted_strength or u.authorized_strength or 0
            k = u.name.lower().strip()
            if val > 0 or k not in strength_map:
                strength_map[k] = val

    if user and user.org:
        def collect_units(node):
            res = []
            for child in node.children:
                if child.type and child.type.lower() == 'unit':
                    k = child.name.lower().strip()
                    auth = strength_map.get(k)
                    if auth is None:
                        auth = strength_map.get(k.replace('_', ' '))
                    if auth is None:
                        auth = strength_map.get(k.replace(' ', '_'))
                    if auth is None:
                        auth = 0
                    res.append({
                        "id": child.id,
                        "name": child.name,
                        "authorized_strength": auth
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

    # Sum stock_total from ecc_monthly_state for this division / username
    possible_names = set()
    if user:
        if user.username:
            possible_names.add(user.username.strip())
            possible_names.add(user.username.replace('_', ' ').strip())
            possible_names.add(user.username.replace(' ', '_').strip())
        if user.org and user.org.name:
            possible_names.add(user.org.name.strip())
            possible_names.add(user.org.name.replace('_', ' ').strip())
            possible_names.add(user.org.name.replace(' ', '_').strip())

    # Pre-calculate Received During this year (strictly for the Division itself)
    div_scope_names = list(possible_names)

    now_dt_curr = datetime.now()
    first_day_of_current_year = datetime(now_dt_curr.year, 1, 1)

    recd_year_map = {}
    if div_scope_names:
        # 1. Primary Ledger Source: transactions table for received_by == Division
        trans_records = Transactions.query.filter(
            db.func.lower(Transactions.received_by).in_([n.lower().strip() for n in div_scope_names if n]),
            Transactions.timestamp >= first_day_of_current_year
        ).all()

        for t in trans_records:
            iid = t.item_id
            if iid not in recd_year_map:
                recd_year_map[iid] = {"ser": 0, "pws": 0}
            recd_year_map[iid]["ser"] += (t.ser or 0)
            recd_year_map[iid]["pws"] += (t.pws or 0)

        # 2. Fallback for baseline items where transactions ledger has no entries yet
        scope_records = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_([n.lower().strip() for n in div_scope_names if n])
        ).all()
        for r in scope_records:
            rec_dt = r.issued_at
            if rec_dt:
                rec_naive = rec_dt.astimezone(timezone.utc).replace(tzinfo=None) if rec_dt.tzinfo else rec_dt
                if rec_naive < first_day_of_current_year:
                    continue

            iid = r.item_id
            if iid not in recd_year_map:
                recd_year_map[iid] = {"ser": 0, "pws": 0}
                a_ser = getattr(r, 'available_ser', 0) or 0
                a_pws = getattr(r, 'available_pws', 0) or 0
                a_res = getattr(r, 'available_res', 0) or 0
                if a_ser == 0 and a_pws == 0 and a_res > 0:
                    a_ser = a_res
                recd_year_map[iid]["ser"] += a_ser
                recd_year_map[iid]["pws"] += a_pws

    # Pre-calculate Issued During this year using transactions table (strictly for the Division itself)
    issd_year_map = {}
    if div_scope_names:
        issd_trans_records = Transactions.query.filter(
            db.func.lower(Transactions.issued_by).in_([n.lower().strip() for n in div_scope_names if n]),
            Transactions.timestamp >= first_day_of_current_year
        ).all()

        for t in issd_trans_records:
            iid = t.item_id
            if iid not in issd_year_map:
                issd_year_map[iid] = {"ser": 0, "pws": 0}
            issd_year_map[iid]["ser"] += (t.ser or 0)
            issd_year_map[iid]["pws"] += (t.pws or 0)

    # Calculate Stock with TPS (sum of all subordinate units under this division)
    tps_stock_map = {}
    all_sub_names = list(set([u["name"].strip() for u in subordinate_units if u.get("name")] + list(possible_names)))

    if all_sub_names:
        tps_records = db.session.query(
            UnitTpsStock.item_id,
            db.func.sum(UnitTpsStock.tps_ser).label("total_tps_ser"),
            db.func.sum(UnitTpsStock.tps_pws).label("total_tps_pws")
        ).filter(
            db.func.lower(UnitTpsStock.unit_name).in_([n.lower().strip() for n in all_sub_names if n])
        ).group_by(UnitTpsStock.item_id).all()

        for t in tps_records:
            tps_stock_map[t.item_id] = {
                "tps_ser": int(t.total_tps_ser or 0),
                "tps_pws": int(t.total_tps_pws or 0)
            }

    # Fetch all ECC catalog items from ScmeItems
    all_ecc_items = ScmeItems.query.filter(
        db.func.lower(ScmeItems.type) == 'ecc'
    ).order_by(ScmeItems.item_name).all()
    if not all_ecc_items:
        all_ecc_items = OurItems.query.order_by(OurItems.item_name).all()

    ecc_item_map = {item.id: item for item in all_ecc_items}

    # Map scale and auth values from ItemAuth (primary source for unit/division auth) and TrackUnitItems
    dou_item_auth_map = {}
    dou_item_scale_map = {}
    if possible_names:
        clean_possible = [n.lower().strip() for n in possible_names if n]
        norm_possible = [n.lower().strip().replace('_', ' ') for n in possible_names if n]
        all_ia_for_div = ItemAuth.query.filter(
            ItemAuth.item_id.isnot(None),
            ItemAuth.unit_name.isnot(None)
        ).all()
        for ia in all_ia_for_div:
            norm_ia_u = ia.unit_name.lower().strip().replace('_', ' ')
            if norm_ia_u in norm_possible or ia.unit_name.lower().strip() in clean_possible:
                if ia.auth is not None:
                    dou_item_auth_map[ia.item_id] = ia.auth
                if ia.scale and ia.scale.strip():
                    dou_item_scale_map[ia.item_id] = ia.scale.strip()

    track_scale_map = {}
    track_auth_map = {}
    track_unit_recs = TrackUnitItems.query.filter(
        TrackUnitItems.item_id.isnot(None)
    ).order_by(TrackUnitItems.issued_at.desc(), TrackUnitItems.id.desc()).all()

    for tr in track_unit_recs:
        if tr.item_id:
            if tr.scale and tr.item_id not in track_scale_map:
                track_scale_map[tr.item_id] = tr.scale
            if tr.auth is not None and tr.item_id not in track_auth_map:
                track_auth_map[tr.item_id] = tr.auth

    # Pre-populate item_records_map for ALL ECC items with 0 stock defaults
    item_records_map = {}
    for item in all_ecc_items:
        auth_for_item = dou_item_auth_map.get(item.id)
        if auth_for_item is None:
            auth_for_item = track_auth_map.get(item.id) or getattr(item, 'auth', 0) or 0
        scale_for_item = dou_item_scale_map.get(item.id) or track_scale_map.get(item.id) or getattr(item, 'scale', None) or "N/A"

        item_records_map[item.id] = {
            "id": None,
            "item_id": item.id,
            "item_name": item.item_name,
            "category": getattr(item, 'category', '') or '',
            "scale": scale_for_item,
            "auth": auth_for_item,
            "auth_res": 0,
            "auth_total": auth_for_item,
            "available_res": 0,
            "available_ser": 0,
            "available_pws": 0,
            "stock_ser": 0,
            "stock_pws": 0,
            "stock_total": 0,
        }

    dou_own_issued_map = {}
    if possible_names:
        records = TrackUnitItems.query.filter(
            db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_([n.lower().strip() for n in possible_names if n])
        ).order_by(TrackUnitItems.issued_at.desc(), TrackUnitItems.id.desc()).all()

        for rec in records:
            iid = rec.item_id
            if iid not in ecc_item_map:
                continue

            r_entry = item_records_map[iid]
            if dou_item_scale_map.get(iid):
                r_entry["scale"] = dou_item_scale_map[iid]
            elif rec.scale:
                r_entry["scale"] = rec.scale

            if dou_item_auth_map.get(iid) is not None:
                r_entry["auth"] = dou_item_auth_map[iid]
                r_entry["auth_total"] = dou_item_auth_map[iid]
            elif rec.auth is not None:
                r_entry["auth"] = rec.auth
                r_entry["auth_total"] = rec.auth

            if r_entry["id"] is None:
                r_entry["id"] = rec.id

            avail_ser_val = getattr(rec, 'available_ser', 0) or 0
            avail_pws_val = getattr(rec, 'available_pws', 0) or 0
            avail_res_val = avail_ser_val + avail_pws_val

            r_entry["available_res"] += avail_res_val
            r_entry["available_ser"] += avail_ser_val
            r_entry["available_pws"] += avail_pws_val

            if iid not in dou_own_issued_map:
                dou_own_issued_map[iid] = {"ser": 0, "pws": 0}
            dou_own_issued_map[iid]["ser"] += (getattr(rec, 'ser', 0) or 0)
            dou_own_issued_map[iid]["pws"] += (getattr(rec, 'pws', 0) or 0)

    # Collect all subordinate unit names under this division
    child_unit_names = []
    if user and user.org:
        def collect_child_unit_names(node):
            names = []
            for child in node.children:
                if child.type and child.type.lower() == 'unit':
                    names.append(child.name.lower().strip())
                    names.append(child.name.replace('_', ' ').lower().strip())
                    names.append(child.name.replace(' ', '_').lower().strip())
                else:
                    names.extend(collect_child_unit_names(child))
            return names
        child_unit_names = collect_child_unit_names(user.org)

    if subordinate_units:
        for u in subordinate_units:
            if u.get("name"):
                n_val = u["name"].lower().strip()
                child_unit_names.extend([n_val, n_val.replace('_', ' '), n_val.replace(' ', '_')])

    dou_issued_targets = Transactions.query.filter(
        db.func.lower(db.func.trim(Transactions.issued_by)).in_([n.lower().strip() for n in possible_names if n])
    ).with_entities(Transactions.received_by).distinct().all()
    for row_t in dou_issued_targets:
        if row_t[0]:
            c_val = row_t[0].strip().lower()
            child_unit_names.extend([c_val, c_val.replace('_', ' '), c_val.replace(' ', '_')])

    div_name_lowers = set([n.lower().strip() for n in possible_names if n])
    clean_sub_names = list(set([n for n in child_unit_names if n and n not in div_name_lowers and 'fod' not in n]))

    # ---------------------------------------------------------
    # Build unit_equipment_map and sub_held_map for subordinate units
    # (Matches blueprints/unit.py calculation identically)
    # ---------------------------------------------------------
    unit_equipment_map = {}
    sub_held_map = {}

    sub_names_list = []
    seen_norm_subs = set()
    if subordinate_units:
        for u in subordinate_units:
            n_val = u.get("name")
            if n_val:
                norm_n = n_val.lower().strip().replace('_', ' ')
                if norm_n not in seen_norm_subs:
                    seen_norm_subs.add(norm_n)
                    sub_names_list.append(n_val)

    for n in clean_sub_names:
        if n:
            norm_n = n.lower().strip().replace('_', ' ')
            if norm_n not in seen_norm_subs:
                seen_norm_subs.add(norm_n)
                sub_names_list.append(n.replace('_', ' ').title())

    if clean_sub_names:
        # Pre-load transactions received and issued by subordinate units
        child_recd_trans = Transactions.query.filter(
            db.func.lower(db.func.trim(Transactions.received_by)).in_(clean_sub_names)
        ).all()
        sub_trans_recd_map = {}
        for t in child_recd_trans:
            uk = t.received_by.lower().strip().replace('_', ' ')
            k = (uk, t.item_id)
            if k not in sub_trans_recd_map:
                sub_trans_recd_map[k] = []
            sub_trans_recd_map[k].append(t)

        child_issd_trans = Transactions.query.filter(
            db.func.lower(db.func.trim(Transactions.issued_by)).in_(clean_sub_names)
        ).all()
        sub_trans_issd_map = {}
        for t in child_issd_trans:
            uk = t.issued_by.lower().strip().replace('_', ' ')
            k = (uk, t.item_id)
            if k not in sub_trans_issd_map:
                sub_trans_issd_map[k] = []
            sub_trans_issd_map[k].append(t)

        # Pre-load TrackUnitItems for subordinate units
        all_sub_tracks = TrackUnitItems.query.filter(
            db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_(clean_sub_names)
        ).order_by(TrackUnitItems.issued_at.desc(), TrackUnitItems.id.desc()).all()
        sub_track_map = {}
        for ctr in all_sub_tracks:
            uk = ctr.unit_name.lower().strip().replace('_', ' ')
            k = (uk, ctr.item_id)
            if k not in sub_track_map:
                sub_track_map[k] = ctr

        # Pre-load ItemAuth for all subordinate units
        sub_auth_map = {}
        all_ia_sub = ItemAuth.query.filter(
            ItemAuth.item_id.isnot(None),
            ItemAuth.unit_name.isnot(None)
        ).all()
        for ar in all_ia_sub:
            if ar.unit_name and ar.auth is not None:
                sub_auth_map[(ar.unit_name.lower().strip().replace('_', ' '), ar.item_id)] = ar.auth

        # Pre-load ScmeIssuedItems as secondary fallback
        sub_issued_auth_map = {}
        all_scme_issued = ScmeIssuedItems.query.filter(
            db.func.lower(db.func.trim(ScmeIssuedItems.unit_name)).in_(clean_sub_names)
        ).all()
        for si in all_scme_issued:
            if si.unit_name and si.unit_authorized is not None:
                sub_issued_auth_map[(si.unit_name.lower().strip().replace('_', ' '), si.item_id)] = si.unit_authorized

        # Iterate through each subordinate unit and catalog item
        for u_name in sub_names_list:
            if not u_name:
                continue
            if u_name not in unit_equipment_map:
                unit_equipment_map[u_name] = []

            norm_u = u_name.lower().strip().replace('_', ' ')
            seen_ids = set()

            for it in all_ecc_items:
                iid = it.id
                seen_ids.add(iid)
                track_rec = sub_track_map.get((norm_u, iid))
                recd_list = sub_trans_recd_map.get((norm_u, iid), [])
                issd_list = sub_trans_issd_map.get((norm_u, iid), [])

                if (norm_u, iid) in sub_auth_map:
                    auth = sub_auth_map[(norm_u, iid)]
                elif track_rec and (track_rec.auth or 0) > 0:
                    auth = track_rec.auth
                elif (norm_u, iid) in sub_issued_auth_map:
                    auth = sub_issued_auth_map[(norm_u, iid)]
                else:
                    auth = (track_rec.auth if track_rec else 0) or 0

                stk_info = _calculate_sub_unit_stock(track_rec, recd_list, issd_list, auth)

                unit_equipment_map[u_name].append({
                    "id": track_rec.id if track_rec else None,
                    "item_id": iid,
                    "item_name": it.item_name,
                    "authorized": stk_info["auth"],
                    "held": stk_info["held"],
                    "ser": stk_info["ser"],
                    "pws": stk_info["pws"],
                    "condemned_ser": stk_info["cond_ser"],
                    "condemned_pws": stk_info["cond_pws"],
                    "deficiency": stk_info["defi"],
                    "issued_at": track_rec.issued_at.strftime('%d %b %Y') if (track_rec and track_rec.issued_at) else None
                })

                if stk_info["held"] > 0 or stk_info["ser"] > 0 or stk_info["pws"] > 0:
                    if iid not in sub_held_map:
                        sub_held_map[iid] = {'ser': 0, 'pws': 0, 'total': 0}
                    sub_held_map[iid]['ser'] += stk_info['ser']
                    sub_held_map[iid]['pws'] += stk_info['pws']
                    sub_held_map[iid]['total'] += stk_info['held']

            # Also check any items with track records not in all_ecc_items
            for (u_key, iid), tr in sub_track_map.items():
                if u_key == norm_u and iid not in seen_ids:
                    seen_ids.add(iid)
                    it_obj = ecc_item_map.get(iid) or ScmeItems.query.get(iid) or OurItems.query.get(iid)
                    i_name = it_obj.item_name if it_obj else f"Item #{iid}"
                    recd_list = sub_trans_recd_map.get((norm_u, iid), [])
                    issd_list = sub_trans_issd_map.get((norm_u, iid), [])
                    auth = sub_auth_map.get((norm_u, iid), tr.auth or 0)
                    stk_info = _calculate_sub_unit_stock(tr, recd_list, issd_list, auth)
                    unit_equipment_map[u_name].append({
                        "id": tr.id,
                        "item_id": iid,
                        "item_name": i_name,
                        "authorized": stk_info["auth"],
                        "held": stk_info["held"],
                        "ser": stk_info["ser"],
                        "pws": stk_info["pws"],
                        "condemned_ser": stk_info["cond_ser"],
                        "condemned_pws": stk_info["cond_pws"],
                        "deficiency": stk_info["defi"],
                        "issued_at": tr.issued_at.strftime('%d %b %Y') if tr.issued_at else None
                    })
                    if stk_info["held"] > 0 or stk_info["ser"] > 0 or stk_info["pws"] > 0:
                        if iid not in sub_held_map:
                            sub_held_map[iid] = {'ser': 0, 'pws': 0, 'total': 0}
                        sub_held_map[iid]['ser'] += stk_info['ser']
                        sub_held_map[iid]['pws'] += stk_info['pws']
                        sub_held_map[iid]['total'] += stk_info['held']

    # Fallback to DOU's own legacy issue records if no unit records held this item
    for iid_c, dou_iss in dou_own_issued_map.items():
        if iid_c not in sub_held_map:
            sub_held_map[iid_c] = {'ser': 0, 'pws': 0, 'total': 0}
        if sub_held_map[iid_c]['total'] == 0:
            sub_held_map[iid_c]['ser'] = dou_iss['ser']
            sub_held_map[iid_c]['pws'] = dou_iss['pws']
            sub_held_map[iid_c]['total'] = dou_iss['ser'] + dou_iss['pws']

    stock_records = []
    for iid, r in item_records_map.items():
        # STK HELD WITH UNITS: Includes both DOU issues and direct issues from 2 FOD to units
        if iid in sub_held_map:
            r["stock_ser"] = sub_held_map[iid]['ser']
            r["stock_pws"] = sub_held_map[iid]['pws']
            r["stock_total"] = sub_held_map[iid]['total']
        else:
            r["stock_ser"] = 0
            r["stock_pws"] = 0
            r["stock_total"] = 0

        r_info = recd_year_map.get(iid, {"ser": r["available_ser"], "pws": r["available_pws"]})
        i_info = issd_year_map.get(iid, {"ser": 0, "pws": 0})
        t_info = tps_stock_map.get(iid, {"tps_ser": 0, "tps_pws": 0})

        r["recd_year_ser"] = r_info["ser"]
        r["recd_year_pws"] = r_info["pws"]
        r["issd_year_ser"] = i_info["ser"]
        r["issd_year_pws"] = i_info["pws"]
        r["tps_ser"] = t_info["tps_ser"]
        r["tps_pws"] = t_info["tps_pws"]

        # Calculate Reserve (RES) held at Division:
        if iid in recd_year_map or iid in issd_year_map:
            r["available_ser"] = max(0, r["recd_year_ser"] - r["issd_year_ser"])
            r["available_pws"] = max(0, r["recd_year_pws"] - r["issd_year_pws"])
            r["available_res"] = r["available_ser"] + r["available_pws"]
        elif r["available_ser"] == 0 and r["available_res"] > 0:
            if r["available_pws"] < r["available_res"]:
                r["available_ser"] = r["available_res"] - r["available_pws"]

        stock_records.append(r)

    # Sort stock_records strictly by Fixed Category Order (CAT-I first, then CAT-II)
    def stock_sort_key(r):
        cat = (r.get("category", "") or "").upper().replace(" ", "").replace("-", "")
        if "CAT1" in cat or ("CATI" in cat and "CATII" not in cat):
            cat_rank = 1
        elif "CAT2" in cat or "CATII" in cat:
            cat_rank = 2
        else:
            cat_rank = 3
        return (cat_rank, (r.get("item_name", "") or "").lower())

    stock_records.sort(key=stock_sort_key)

    total_stock_held = sum(r["stock_total"] for r in stock_records) or 0

    # Collect items that are held/issued to at least one subordinate unit under this division
    issued_unit_items = []
    seen_item_names = set()
    for u_name, items_list in unit_equipment_map.items():
        for it in items_list:
            i_name = it.get("item_name")
            if i_name and i_name not in seen_item_names:
                seen_item_names.add(i_name)
                issued_unit_items.append({"item_id": it["item_id"], "item_name": i_name})

    issued_unit_items.sort(key=lambda x: x["item_name"])

    # Build Day-Wise Dual Trend Data (Received vs Issued) from transactions table
    daily_recd_totals = {}
    daily_issd_totals = {}
    div_scope_names = list(possible_names)

    if div_scope_names:
        div_scope_lower = [n.lower().strip() for n in div_scope_names if n]
        
        # 1. Received transactions
        recd_trans = Transactions.query.filter(
            db.func.lower(Transactions.received_by).in_(div_scope_lower)
        ).all()
        for t in recd_trans:
            if t.timestamp:
                dt_str = t.timestamp.strftime("%Y-%m-%d")
                qty = (t.ser or 0) + (t.pws or 0)
                daily_recd_totals[dt_str] = daily_recd_totals.get(dt_str, 0) + qty

        # 2. Issued transactions
        issd_trans = Transactions.query.filter(
            db.func.lower(Transactions.issued_by).in_(div_scope_lower)
        ).all()
        for t in issd_trans:
            if t.timestamp:
                dt_str = t.timestamp.strftime("%Y-%m-%d")
                qty = (t.ser or 0) + (t.pws or 0)
                daily_issd_totals[dt_str] = daily_issd_totals.get(dt_str, 0) + qty

    all_dates = set(daily_recd_totals.keys()).union(set(daily_issd_totals.keys()))
    sorted_dates = sorted(all_dates)

    if not sorted_dates:
        today = datetime.now()
        sorted_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    daily_trend_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%d %b") for d in sorted_dates]
    daily_recd_data = [daily_recd_totals.get(d, 0) for d in sorted_dates]
    daily_issd_data = [daily_issd_totals.get(d, 0) for d in sorted_dates]

    # SER vs PWS dataset from transactions table
    trans_records_all = Transactions.query.all()
    trans_ser_pws_data = []
    for t in trans_records_all:
        i_name = t.item.item_name if t.item else f"Item #{t.item_id}"
        trans_ser_pws_data.append({
            "issued_by": t.issued_by or "",
            "received_by": t.received_by or "",
            "item_name": i_name,
            "ser": t.ser or 0,
            "pws": t.pws or 0
        })

    # Aggregated TPS chart data per subordinate unit
    tps_chart_data = {}
    if subordinate_units:
        sub_names = [u["name"].strip() for u in subordinate_units if "name" in u]
        if sub_names:
            tps_query = db.session.query(
                UnitTpsStock.unit_name,
                db.func.sum(UnitTpsStock.tps_ser).label("total_ser"),
                db.func.sum(UnitTpsStock.tps_pws).label("total_pws")
            ).filter(
                db.func.lower(UnitTpsStock.unit_name).in_([n.lower() for n in sub_names])
            ).group_by(UnitTpsStock.unit_name).all()

            for row in tps_query:
                tps_chart_data[row.unit_name] = {
                    "ser": int(row.total_ser or 0),
                    "pws": int(row.total_pws or 0)
                }

        for u in subordinate_units:
            u_name = u.get("name")
            if u_name and u_name not in tps_chart_data:
                tps_chart_data[u_name] = {"ser": 0, "pws": 0}

    def category_sort_key(item):
        cat = (getattr(item, 'category', '') or '').upper().replace(" ", "").replace("-", "")
        if "CAT1" in cat or ("CATI" in cat and "CATII" not in cat):
            rank = 1
        elif "CAT2" in cat or "CATII" in cat:
            rank = 2
        else:
            rank = 3
        name = (getattr(item, 'item_name', '') or '').lower()
        return (rank, name)

    ecc_catalog_items = [i for i in catalog_items if getattr(i, 'type', None) and i.type.lower() == 'ecc']
    scme_catalog_items = [i for i in catalog_items if not getattr(i, 'type', None) or i.type.lower() != 'ecc']

    ecc_catalog_items.sort(key=category_sort_key)
    scme_catalog_items.sort(key=category_sort_key)

    critical_alert_items = []
    if unit_equipment_map:
        for u_name, items_list in unit_equipment_map.items():
            for it in items_list:
                auth = it.get("authorized", 0) or 0
                held = it.get("held", 0) or 0
                if auth > 0 and held < (auth / 2.0):
                    held_pct = round((held / auth) * 100, 1)
                    critical_alert_items.append({
                        "unit_name": u_name,
                        "item_name": it.get("item_name", ""),
                        "authorized": auth,
                        "held": held,
                        "held_pct": held_pct,
                        "deficiency": it.get("deficiency", max(0, auth - held))
                    })
    critical_alerts_count = len(critical_alert_items)
    current_dou_name = user.org.name if (user and user.org) else (session.get("username") or username)
    auth_units = [{"id": 0, "name": current_dou_name, "is_current": True}] + [
        {"id": u.get("id"), "name": u.get("name"), "is_current": False}
        for u in subordinate_units
        if u.get("name") != current_dou_name
    ]

    # Build Dataset for Overall Analysis Chart (AUTH vs HELD for Division Admin by Category)
    overall_analysis_data = []
    for r in stock_records:
        auth_val = int(r.get("auth", 0) or 0)
        held_val = int(r.get("stock_total", 0) or 0)
        defi_val = max(0, auth_val - held_val)
        cat_str = (r.get("category") or "CAT-I").strip().upper()
        norm_cat = "CAT-II" if ("CAT-II" in cat_str or "CAT II" in cat_str or "CAT2" in cat_str) else "CAT-I"
        overall_analysis_data.append({
            "item_id": r.get("item_id"),
            "item_name": r.get("item_name"),
            "category": norm_cat,
            "auth": auth_val,
            "held": held_val,
            "defi": defi_val
        })

    return render_template(
        '/Div_Dashboard/div_dashboard.html',
        username=username,
        user_div_name=session.get("username") or username,
        units=subordinate_units,
        auth_units=auth_units,
        unit_count=len(subordinate_units),
        catalog_items=catalog_items,
        ecc_catalog_items=ecc_catalog_items,
        scme_catalog_items=scme_catalog_items,
        total_items=len(catalog_items),
        critical_alerts_count=critical_alerts_count,
        critical_alert_items=critical_alert_items,
        total_stock_held=total_stock_held,
        stock_records=stock_records,
        unit_equipment_map=unit_equipment_map,
        issued_unit_items=issued_unit_items,
        daily_trend_labels=daily_trend_labels,
        daily_recd_data=daily_recd_data,
        daily_issd_data=daily_issd_data,
        trans_ser_pws_data=trans_ser_pws_data,
        tps_chart_data=tps_chart_data,
        overall_analysis_data=overall_analysis_data
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
            val_u = int(u_strength) if (u_strength is not None and u_strength != "") else None
            val_a = int(a_strength) if (a_strength is not None and a_strength != "") else None

            new_val = 0
            if val_a is not None and val_a >= 0:
                new_val = val_a
            if val_u is not None and val_u > 0:
                new_val = val_u

            if new_val < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Strength must be a valid non-negative integer."}), 400

        possible_names = {
            unit_name.lower().strip(),
            unit_name.replace('_', ' ').lower().strip(),
            unit_name.replace(' ', '_').lower().strip()
        }

        # Update personnel strength in Strength table (unit_strength)
        records = Strength.query.filter(
            db.func.lower(Strength.unit_name).in_(list(possible_names))
        ).all()

        if records:
            for record in records:
                record.posted_strength = new_val
                record.authorized_strength = new_val
        else:
            record = Strength(unit_name=unit_name, posted_strength=new_val, authorized_strength=new_val)
            db.session.add(record)

        # Also update Units table if record exists
        unit_objs = Units.query.filter(
            db.func.lower(Units.name).in_(list(possible_names))
        ).all()
        for u_obj in unit_objs:
            u_obj.posted_strength = new_val
            u_obj.authorized_strength = new_val

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Successfully updated posted personnel strength to {new_val} for {unit_name}.",
            "unit_name": unit_name,
            "unit_strength": new_val,
            "authorized_strength": new_val
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@div_bp.route('/api/set-unit-auth', methods=['POST'])
@csrf.exempt
def api_set_unit_auth():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json() or {}
        unit_name = (data.get("unit_name") or "").strip()
        item_id = data.get("item_id")
        auth_val = data.get("auth")

        if not unit_name or not item_id or auth_val is None:
            return jsonify({"success": False, "message": "Unit name, Item, and AUTH quantity are required."}), 400

        try:
            auth_int = int(auth_val)
            item_id_int = int(item_id)
            if auth_int < 0:
                return jsonify({"success": False, "message": "AUTH cannot be negative."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "AUTH must be a valid integer."}), 400

        item_exists = ScmeItems.query.get(item_id_int)
        if not item_exists:
            item_exists = OurItems.query.get(item_id_int)
        if not item_exists:
            return jsonify({"success": False, "message": "Selected Item does not exist."}), 400

        possible_names = {
            unit_name.lower().strip(),
            unit_name.replace('_', ' ').lower().strip(),
            unit_name.replace(' ', '_').lower().strip()
        }
        norm_unit = unit_name.lower().strip().replace('_', ' ')
        scale_val = getattr(item_exists, 'scale', None) or "1 PER INDL"

        # 1. Update/Insert into ItemAuth table (all records matching unit and item)
        all_recs_for_item = ItemAuth.query.filter(ItemAuth.item_id == item_id_int).all()
        matched_auth_recs = []
        for rec in all_recs_for_item:
            if rec.unit_name:
                rec_unit_norm = rec.unit_name.lower().strip().replace('_', ' ')
                if rec_unit_norm == norm_unit or rec.unit_name.lower().strip() in possible_names:
                    matched_auth_recs.append(rec)

        if matched_auth_recs:
            for rec in matched_auth_recs:
                rec.auth = auth_int
                rec.unit_name = unit_name
                if not rec.scale:
                    rec.scale = scale_val
        else:
            item_auth_rec = ItemAuth(
                unit_name=unit_name,
                item_id=item_id_int,
                auth=auth_int,
                scale=scale_val
            )
            db.session.add(item_auth_rec)

        # 2. Update/Insert into TrackUnitItems table
        track_recs = TrackUnitItems.query.filter(
            db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_(list(possible_names)),
            TrackUnitItems.item_id == item_id_int
        ).all()

        if track_recs:
            for tr in track_recs:
                tr.auth = auth_int
                tr.unit_name = unit_name
                if not tr.scale:
                    tr.scale = scale_val
        else:
            new_tr = TrackUnitItems(
                unit_name=unit_name,
                item_id=item_id_int,
                scale=scale_val,
                auth=auth_int,
                held=0,
                ser=0,
                pws=0,
                available_ser=0,
                available_pws=0,
                available_res=0,
                issued_at=datetime.now()
            )
            db.session.add(new_tr)

        # 3. Update/Insert into ScmeIssuedItems table
        issued_recs = ScmeIssuedItems.query.filter(
            db.func.lower(db.func.trim(ScmeIssuedItems.unit_name)).in_(list(possible_names)),
            ScmeIssuedItems.item_id == item_id_int
        ).all()

        if issued_recs:
            for ir in issued_recs:
                ir.unit_authorized = auth_int
                ir.unit_name = unit_name
                ir.deficiency = max(0, auth_int - (ir.held or 0))
                if not ir.scale:
                    ir.scale = scale_val
        else:
            new_ir = ScmeIssuedItems(
                unit_name=unit_name,
                item_id=item_id_int,
                a_u="Nos",
                unit_authorized=auth_int,
                scale=scale_val,
                held=0,
                deficiency=auth_int
            )
            db.session.add(new_ir)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Successfully set AUTH = {auth_int} for unit '{unit_name}' on item '{item_exists.item_name}'.",
            "unit_name": unit_name,
            "item_id": item_id_int,
            "auth": auth_int
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@div_bp.route('/api/unit-breakdown')
def api_unit_breakdown():
    try:
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Not authenticated."}), 401

        _ensure_track_unit_items_migrated()

        unit_name = request.args.get("unit_name", "").strip()
        if not unit_name:
            return jsonify({"success": False, "message": "Unit name is required."}), 400

        possible_names = {
            unit_name.lower().strip(),
            unit_name.replace('_', ' ').lower().strip(),
            unit_name.replace(' ', '_').lower().strip()
        }
        norm_unit = unit_name.lower().strip().replace('_', ' ')

        # Fetch ItemAuth for unit
        unit_item_auth_map = {}
        all_ia_for_unit = ItemAuth.query.filter(
            ItemAuth.item_id.isnot(None),
            ItemAuth.unit_name.isnot(None)
        ).all()
        for ia in all_ia_for_unit:
            if ia.unit_name.lower().strip().replace('_', ' ') == norm_unit or ia.unit_name.lower().strip() in possible_names:
                if ia.auth is not None:
                    unit_item_auth_map[ia.item_id] = ia.auth

        # Query track_unit_items table for item breakdown
        track_records = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_(list(possible_names))
        ).all()

        unit_recd_trans = Transactions.query.filter(
            db.func.lower(db.func.trim(Transactions.received_by)).in_(list(possible_names))
        ).all()
        sub_trans_recd = {}
        for t in unit_recd_trans:
            if t.item_id not in sub_trans_recd:
                sub_trans_recd[t.item_id] = []
            sub_trans_recd[t.item_id].append(t)

        unit_issd_trans = Transactions.query.filter(
            db.func.lower(db.func.trim(Transactions.issued_by)).in_(list(possible_names))
        ).all()
        sub_trans_issd = {}
        for t in unit_issd_trans:
            if t.item_id not in sub_trans_issd:
                sub_trans_issd[t.item_id] = []
            sub_trans_issd[t.item_id].append(t)

        breakdown = []
        seen_items = set()

        for rec in track_records:
            item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
            seen_items.add(rec.item_id)
            auth = unit_item_auth_map.get(rec.item_id, rec.auth or 0)
            stk_info = _calculate_sub_unit_stock(
                rec,
                sub_trans_recd.get(rec.item_id, []),
                sub_trans_issd.get(rec.item_id, []),
                auth
            )
            breakdown.append({
                "id": rec.id,
                "item_id": rec.item_id,
                "item_name": item_name,
                "authorized": stk_info["auth"],
                "held": stk_info["held"],
                "ser": stk_info["ser"],
                "pws": stk_info["pws"],
                "condemned_ser": stk_info["cond_ser"],
                "condemned_pws": stk_info["cond_pws"],
                "deficiency": stk_info["defi"],
                "issued_at": rec.issued_at.strftime('%d %b %Y') if rec.issued_at else None
            })

        # Append any items authorized in ItemAuth or received in Transactions that have no track record yet
        all_potential_ids = set(list(unit_item_auth_map.keys()) + list(sub_trans_recd.keys()))
        for iid in all_potential_ids:
            if iid not in seen_items:
                it_obj = ScmeItems.query.get(iid) or OurItems.query.get(iid)
                if it_obj:
                    seen_items.add(iid)
                    a_val = unit_item_auth_map.get(iid, 0)
                    stk_info = _calculate_sub_unit_stock(
                        None,
                        sub_trans_recd.get(iid, []),
                        sub_trans_issd.get(iid, []),
                        a_val
                    )
                    breakdown.append({
                        "id": None,
                        "item_id": iid,
                        "item_name": it_obj.item_name,
                        "authorized": stk_info["auth"],
                        "held": stk_info["held"],
                        "ser": stk_info["ser"],
                        "pws": stk_info["pws"],
                        "condemned_ser": stk_info["cond_ser"],
                        "condemned_pws": stk_info["cond_pws"],
                        "deficiency": stk_info["defi"],
                        "issued_at": None
                    })

        breakdown.sort(key=lambda x: (x.get("item_name") or "").lower())

        return jsonify({"success": True, "unit_name": unit_name, "records": breakdown}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@div_bp.route('/api/unit-item-auth')
def api_unit_item_auth():
    try:
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Not authenticated."}), 401

        unit_name = request.args.get("unit_name", "").strip()
        item_id_str = request.args.get("item_id", "").strip()

        if not unit_name or not item_id_str:
            return jsonify({"success": False, "message": "unit_name and item_id are required."}), 400

        try:
            item_id = int(item_id_str)
        except ValueError:
            return jsonify({"success": False, "message": "Invalid item_id."}), 400

        possible_names = {
            unit_name.lower().strip(),
            unit_name.replace('_', ' ').lower().strip(),
            unit_name.replace(' ', '_').lower().strip()
        }

        # 1. Primary Source: ItemAuth table for unit-specific authorization and scale
        norm_unit = unit_name.lower().strip().replace('_', ' ')
        item_auth_recs = ItemAuth.query.filter(ItemAuth.item_id == item_id).all()
        item_auth_val = None
        item_scale_val = None

        for rec in item_auth_recs:
            if rec.unit_name:
                rec_unit_norm = rec.unit_name.lower().strip().replace('_', ' ')
                if rec_unit_norm == norm_unit or rec.unit_name.lower().strip() in possible_names:
                    if rec.auth is not None:
                        item_auth_val = rec.auth
                    if rec.scale and rec.scale.strip():
                        item_scale_val = rec.scale.strip()
                    break

        # 2. TrackUnitItems & ScmeIssuedItems for stock details (held, ser, pws)
        track_rec = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_(list(possible_names)),
            TrackUnitItems.item_id == item_id
        ).order_by(TrackUnitItems.issued_at.desc(), TrackUnitItems.id.desc()).first()

        issued_rec = None
        if not track_rec:
            issued_rec = ScmeIssuedItems.query.filter(
                db.func.lower(ScmeIssuedItems.unit_name).in_(list(possible_names)),
                ScmeIssuedItems.item_id == item_id
            ).first()

        unit_recd_trans = Transactions.query.filter(
            db.func.lower(db.func.trim(Transactions.received_by)).in_(list(possible_names)),
            Transactions.item_id == item_id
        ).all()
        unit_issd_trans = Transactions.query.filter(
            db.func.lower(db.func.trim(Transactions.issued_by)).in_(list(possible_names)),
            Transactions.item_id == item_id
        ).all()

        has_record = bool(track_rec or issued_rec or unit_recd_trans)

        auth_val = item_auth_val
        if auth_val is None:
            if track_rec and track_rec.auth is not None:
                auth_val = track_rec.auth
            elif issued_rec and issued_rec.unit_authorized is not None:
                auth_val = issued_rec.unit_authorized

        scale_val = item_scale_val
        if not scale_val:
            if track_rec and track_rec.scale:
                scale_val = track_rec.scale.strip()
            elif issued_rec and issued_rec.scale:
                scale_val = issued_rec.scale.strip()

        stk_info = _calculate_sub_unit_stock(
            track_rec,
            unit_recd_trans,
            unit_issd_trans,
            auth_val or 0
        )
        held_val = stk_info["held"]
        ser_val = stk_info["ser"]
        pws_val = stk_info["pws"]

        # 3. Fallback to global ItemAuth scale (unit_name is null or empty)
        if not scale_val:
            global_auth = ItemAuth.query.filter(
                ItemAuth.item_id == item_id,
                db.or_(ItemAuth.unit_name == None, db.func.trim(ItemAuth.unit_name) == '')
            ).first()
            if global_auth and global_auth.scale and global_auth.scale.strip():
                scale_val = global_auth.scale.strip()

        if not scale_val:
            scale_val = "1 per indl"

        return jsonify({
            "success": True,
            "exists": (has_record or auth_val is not None),
            "scale": scale_val,
            "auth": auth_val if auth_val is not None else 0,
            "held": held_val,
            "ser": ser_val,
            "pws": pws_val
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@div_bp.route('/generate-request')
def gen_req():
    items = OurItems.query.order_by(OurItems.item_name).all()
    return render_template('/Div_Dashboard/request_item.html',items=items)


@div_bp.route('/issue-item', methods=['POST'])
def issue_item():
    try:
        _ensure_track_unit_items_migrated()

        data = request.get_json() or {}
        unit_name = data.get("unit_name")
        item_id = data.get("item_id")
        item_auth = data.get("item_auth")

        raw_ser = data.get("ser", data.get("ser_count"))
        raw_pws = data.get("pws", data.get("pws_count"))
        raw_issue_count = data.get("issue_count")

        try:
            val_ser = int(raw_ser) if (raw_ser is not None and str(raw_ser).strip() != "") else 0
            val_pws = int(raw_pws) if (raw_pws is not None and str(raw_pws).strip() != "") else 0
            if val_ser < 0 or val_pws < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "SER and PWS counts must be non-negative integers."}), 400

        val_qty = val_ser + val_pws
        if val_qty == 0 and raw_issue_count is not None:
            try:
                val_qty = int(raw_issue_count)
                val_ser = val_qty
            except (ValueError, TypeError):
                pass

        if not unit_name or not item_id or val_qty <= 0:
            return jsonify({"success": False, "message": "Unit name, item ID, and a positive quantity to issue (SER or PWS) are required."}), 400

        try:
            item_id = int(item_id)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid item ID."}), 400

        val_auth = None
        if item_auth is not None and str(item_auth).strip() != "":
            try:
                val_auth = int(item_auth)
                if val_auth < 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": "Item AUTH must be a valid non-negative integer."}), 400

        user = LoginUser.query.get(session.get("user_id"))
        if not user:
            return jsonify({"success": False, "message": "User not authenticated."}), 401

        # Locate division names for logged in user
        possible_names = set()
        if user.username:
            possible_names.add(user.username.strip())
            possible_names.add(user.username.replace('_', ' ').strip())
            possible_names.add(user.username.replace(' ', '_').strip())
        if user.org and user.org.name:
            possible_names.add(user.org.name.strip())
            possible_names.add(user.org.name.replace('_', ' ').strip())
            possible_names.add(user.org.name.replace(' ', '_').strip())

        # Target unit possible names for case-insensitive matching
        target_names = [
            unit_name.lower().strip(),
            unit_name.replace('_', ' ').lower().strip(),
            unit_name.replace(' ', '_').lower().strip()
        ]

        val_scale = (data.get("scale") or "").strip()

        # Add or update ScmeIssuedItems for the target unit (update auth, leave held untouched for later issue by subordinate unit)
        issued_rec = ScmeIssuedItems.query.filter(
            db.func.lower(ScmeIssuedItems.unit_name).in_(target_names),
            ScmeIssuedItems.item_id == item_id
        ).first()

        if issued_rec:
            if val_auth is not None:
                issued_rec.unit_authorized = val_auth
            if val_scale:
                issued_rec.scale = val_scale
            issued_rec.deficiency = max(0, (issued_rec.unit_authorized or 0) - (issued_rec.held or 0))
        else:
            initial_auth = val_auth if val_auth is not None else 0
            issued_rec = ScmeIssuedItems(
                unit_name=unit_name,
                item_id=item_id,
                a_u="Nos",
                unit_authorized=initial_auth,
                scale=val_scale or "100%",
                held=0,
                deficiency=initial_auth
            )
            db.session.add(issued_rec)

        # Update item in TrackUnitItems table for the target unit (update available reserve and auth, leave ser/pws/held untouched)
        now_dt = datetime.now()
        track_rec = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_(target_names),
            TrackUnitItems.item_id == item_id
        ).first()

        if track_rec:
            # Update subordinate unit's available reserve columns
            track_rec.available_ser = (track_rec.available_ser or 0) + val_ser
            track_rec.available_pws = (track_rec.available_pws or 0) + val_pws
            track_rec.available_res = (track_rec.available_ser or 0) + (track_rec.available_pws or 0)
            track_rec.held = track_rec.calc_held()
            track_rec.ser = (track_rec.ser or 0) + val_ser
            track_rec.pws = (track_rec.pws or 0) + val_pws
            if track_rec.held_pws is not None:
                track_rec.held_pws = (track_rec.held_pws or 0) + val_pws

            if val_auth is not None:
                track_rec.auth = val_auth
            if val_scale:
                track_rec.scale = val_scale
            track_rec.issued_at = now_dt
        else:
            initial_auth = val_auth if val_auth is not None else 0
            track_rec = TrackUnitItems(
                unit_name=unit_name,
                item_id=item_id,
                scale=val_scale,
                auth=initial_auth,
                held=(val_ser + val_pws),
                ser=val_ser,
                pws=val_pws,
                held_pws=val_pws,
                available_ser=val_ser,
                available_pws=val_pws,
                available_res=val_qty,
                issued_at=now_dt
            )
            track_rec.held = track_rec.calc_held()
            db.session.add(track_rec)

        # Update the DOU (issuing division) stock record across all entries
        dou_recs = TrackUnitItems.query.filter(
            db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_([n.lower().strip() for n in possible_names if n]),
            TrackUnitItems.item_id == item_id
        ).order_by(TrackUnitItems.issued_at.desc(), TrackUnitItems.id.desc()).all()

        if dou_recs:
            avail_ser = sum((r.available_ser or 0) for r in dou_recs)
            avail_pws = sum((r.available_pws or 0) for r in dou_recs)
            if val_ser > avail_ser:
                return jsonify({
                    "success": False,
                    "message": f"Issued SER count ({val_ser}) cannot exceed available SER stock ({avail_ser})."
                }), 400
            if val_pws > avail_pws:
                return jsonify({
                    "success": False,
                    "message": f"Issued PWS count ({val_pws}) cannot exceed available PWS stock ({avail_pws})."
                }), 400

            rem_s = val_ser
            rem_p = val_pws
            for r in dou_recs:
                if rem_s > 0 and (r.available_ser or 0) > 0:
                    ded = min(r.available_ser, rem_s)
                    r.available_ser -= ded
                    r.ser = (r.ser or 0) + ded
                    r.held = (r.held or 0) + ded
                    rem_s -= ded
                if rem_p > 0 and (r.available_pws or 0) > 0:
                    ded = min(r.available_pws, rem_p)
                    r.available_pws -= ded
                    r.pws = (r.pws or 0) + ded
                    r.held = (r.held or 0) + ded
                    rem_p -= ded
                if rem_s <= 0 and rem_p <= 0:
                    break

        # Record transaction entry in transactions table
        trans_rec = Transactions(
            issued_by=user.username or "Division",
            received_by=unit_name,
            item_id=item_id,
            ser=val_ser,
            pws=val_pws,
            timestamp=now_dt
        )
        db.session.add(trans_rec)

        # Send Notification to target Unit
        try:
            sender_name = user.username or "Division"
            item_obj_notif = ScmeItems.query.get(item_id)
            item_name_str = item_obj_notif.item_name if item_obj_notif else f"Item #{item_id}"
            notif = Notification(
                title="New Stock Allocated to You",
                message=f"{sender_name} issued item '{item_name_str}' (SER: {val_ser}, PWS: {val_pws}) to you.",
                sender_name=sender_name,
                target_user=unit_name,
                target_role="unit",
                item_id=item_id
            )
            db.session.add(notif)
        except Exception as ne:
            print("Notification insert notice:", ne)

        db.session.commit()

        # Recalculate total stock held across division
        records = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_([n.lower() for n in possible_names])
        ).all()
        new_total_stock = sum(
            (r.available_ser or 0) + (r.available_pws or 0) + (r.ser or 0) + (r.pws or 0)
            for r in records
        )

        item_obj = ScmeItems.query.get(item_id)
        item_name = item_obj.item_name if item_obj else f"Item #{item_id}"

        res_ser_now = sum((r.available_ser or 0) for r in dou_recs)
        res_pws_now = sum((r.available_pws or 0) for r in dou_recs)
        held_ser_now = sum((r.ser or 0) for r in dou_recs)
        held_pws_now = sum((r.pws or 0) for r in dou_recs)

        return jsonify({
            "success": True,
            "message": f"Successfully issued {val_qty} unit(s) ({val_ser} SER, {val_pws} PWS) of '{item_name}' to {unit_name}.",
            "item_id": item_id,
            "new_total_stock": new_total_stock,
            "new_item_reserve": (res_ser_now + res_pws_now),
            "new_item_stock": (held_ser_now + held_pws_now),
            "new_item_stock_ser": held_ser_now,
            "new_item_stock_pws": held_pws_now
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ---------------------------------------------------------------------------
# CONDEMNATION REQUEST ROUTES (DOU SIDE)
# ---------------------------------------------------------------------------

@div_bp.route('/api/condemnation-requests', methods=['GET'])
def list_condemnation_requests():
    """DOU fetches all condemnation requests addressed to it (all statuses, newest first)."""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        _ensure_track_unit_items_migrated()
        user = LoginUser.query.get(session["user_id"])
        dou_name = (user.org.name if user.org else None) or user.username or ""
        dou_name = dou_name.strip()
        dou_name_lowers = [
            dou_name.lower(),
            dou_name.replace('_', ' ').lower(),
            dou_name.replace(' ', '_').lower()
        ]

        reqs = CondemnationRequest.query.filter(
            db.func.lower(db.func.trim(CondemnationRequest.parent_dou_name)).in_(dou_name_lowers)
        ).order_by(CondemnationRequest.created_at.desc()).all()

        result = []
        for r in reqs:
            item_name = r.item.item_name if r.item else f"Item #{r.item_id}"
            result.append({
                "id": r.id,
                "unit_name": r.unit_name,
                "item_id": r.item_id,
                "item_name": item_name,
                "condemnation_no": r.condemnation_no or "",
                "pdf_filename": r.pdf_filename or "",
                "pdf_original_name": r.pdf_original_name or "",
                "pdf_url": f"/condemnation/pdf/{r.pdf_filename}" if r.pdf_filename else "",
                "req_ser": r.req_ser,
                "req_pws": r.req_pws,
                "salvage_rv": bool(r.salvage_rv),
                "destruction_certificate": bool(r.destruction_certificate),
                "reason": r.reason or "",
                "status": r.status,
                "rejection_reason": r.rejection_reason or "",
                "reviewed_by": r.reviewed_by or "",
                "reviewed_at": r.reviewed_at.strftime("%d-%m-%Y %H:%M") if r.reviewed_at else "",
                "created_at": r.created_at.strftime("%d-%m-%Y") if r.created_at else ""
            })

        pending_count = sum(1 for r in result if r["status"] == "pending")
        return jsonify({"success": True, "requests": result, "pending_count": pending_count}), 200

    except Exception as e:
        print(f"Error listing condemnation requests: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@div_bp.route('/api/condemnation-requests/<int:req_id>/approve', methods=['POST'])
def approve_condemnation_request(req_id):
    """
    DOU approves a pending condemnation request.
    Accumulates req_ser/req_pws into TrackUnitItems.condemned_ser/pws for that unit+item.
    """
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        user = LoginUser.query.get(session["user_id"])
        reviewer_name = (user.org.name if user.org else None) or user.username or "DOU"

        cond_req = CondemnationRequest.query.get(req_id)
        if not cond_req:
            return jsonify({"success": False, "message": "Request not found."}), 404
        if cond_req.status != 'pending':
            return jsonify({"success": False, "message": f"Request is already {cond_req.status}."}), 409

        u_name = cond_req.unit_name.strip()
        unit_name_lowers = [
            u_name.lower(),
            u_name.replace('_', ' ').lower(),
            u_name.replace(' ', '_').lower()
        ]

        track_rec = TrackUnitItems.query.filter(
            db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_(unit_name_lowers),
            TrackUnitItems.item_id == cond_req.item_id
        ).first()

        if track_rec:
            # ACCUMULATE: add newly approved quantities to existing condemned amounts
            track_rec.condemned_ser = (track_rec.condemned_ser or 0) + cond_req.req_ser
            track_rec.condemned_pws = (track_rec.condemned_pws or 0) + cond_req.req_pws
            track_rec.condemnation_date = datetime.now()
        else:
            track_rec = TrackUnitItems(
                unit_name=u_name,
                item_id=cond_req.item_id,
                condemned_ser=cond_req.req_ser,
                condemned_pws=cond_req.req_pws,
                condemnation_date=datetime.now()
            )
            db.session.add(track_rec)

        cond_req.status = 'approved'
        cond_req.reviewed_by = reviewer_name
        cond_req.reviewed_at = datetime.now()

        db.session.commit()
        return jsonify({"success": True, "message": "Condemnation request approved and stock updated."}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error approving condemnation request: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@div_bp.route('/api/condemnation-requests/<int:req_id>/reject', methods=['POST'])
def reject_condemnation_request(req_id):
    """DOU rejects a pending condemnation request with an optional reason."""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        user = LoginUser.query.get(session["user_id"])
        reviewer_name = (user.org.name if user.org else None) or user.username or "DOU"

        data = request.get_json() or {}
        rejection_reason = (data.get("rejection_reason") or "").strip()[:500]

        cond_req = CondemnationRequest.query.get(req_id)
        if not cond_req:
            return jsonify({"success": False, "message": "Request not found."}), 404
        if cond_req.status != 'pending':
            return jsonify({"success": False, "message": f"Request is already {cond_req.status}."}), 409

        cond_req.status = 'rejected'
        cond_req.reviewed_by = reviewer_name
        cond_req.reviewed_at = datetime.now()
        cond_req.rejection_reason = rejection_reason

        db.session.commit()
        return jsonify({"success": True, "message": "Condemnation request rejected."}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error rejecting condemnation request: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
