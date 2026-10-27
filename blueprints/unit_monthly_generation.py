from datetime import datetime
from sqlalchemy import func
from extensions import db
from models.our_items import (
    ScmeItems,
    TrackUnitItems,
    ItemAuth,
    Transactions,
    Strength,
    UnitTpsStock,
    ScmeIssuedItems
)
from models import LoginUser
from models.org_ladder import OrgLadder


def build_unit_monthly_report_payload(unit_username, month_param=None):
    """
    Generates report data for Unit Monthly Report (Unit Format).
    Calculates BBF (prior to selected month), Qty Recd, Qty Condemned,
    Stock held with Tps, and Surplus/Deficiency.
    Excludes UNSV columns as specified.
    """
    now_date = datetime.now()
    try:
        if month_param:
            parts = month_param.split("-")
            sel_year, sel_month = int(parts[0]), int(parts[1])
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

    # Generate name variations for DB filtering
    unit_names = set()
    if unit_username:
        u_clean = str(unit_username).strip()
        unit_names.add(u_clean)
        unit_names.add(u_clean.replace('_', ' '))
        unit_names.add(u_clean.replace(' ', '_'))
        u_user = LoginUser.query.filter(func.lower(func.trim(LoginUser.username)) == u_clean.lower()).first()
        if u_user and u_user.org and u_user.org.name:
            o_clean = u_user.org.name.strip()
            unit_names.add(o_clean)
            unit_names.add(o_clean.replace('_', ' '))
            unit_names.add(o_clean.replace(' ', '_'))

    unit_name_lowers = [u.lower().strip() for u in unit_names if u]

    # 1. Posted Strength
    posted_str = 0
    str_rec = Strength.query.filter(
        func.lower(func.trim(Strength.unit_name)).in_(unit_name_lowers)
    ).first()
    if str_rec:
        posted_str = str_rec.posted_strength or str_rec.authorized_strength or 0
    if not posted_str:
        from models.our_items import Units
        u_rec = Units.query.filter(
            func.lower(func.trim(Units.name)).in_(unit_name_lowers)
        ).first()
        if u_rec:
            posted_str = u_rec.posted_strength or u_rec.authorized_strength or 0

    # 2. Qty Recd during selected month (received_by == unit_name)
    recd_trans = Transactions.query.filter(
        func.lower(func.trim(Transactions.received_by)).in_(unit_name_lowers),
        Transactions.timestamp >= first_day_sel,
        Transactions.timestamp < first_day_next
    ).all()

    dou_recd_map = {}
    fod_recd_map = {}
    for t in recd_trans:
        iss_by = (t.issued_by or "").strip().lower()
        is_fod = iss_by in ['2 fod', '2_fod'] or '2 fod' in iss_by or '2_fod' in iss_by

        target_map = fod_recd_map if is_fod else dou_recd_map
        if t.item_id not in target_map:
            target_map[t.item_id] = {'ser': 0, 'pws': 0}
        target_map[t.item_id]['ser'] += (t.ser or 0)
        target_map[t.item_id]['pws'] += (t.pws or 0)

    # 3. Qty Issued during selected month (issued_by == unit_name)
    issd_trans = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)).in_(unit_name_lowers),
        Transactions.timestamp >= first_day_sel,
        Transactions.timestamp < first_day_next
    ).all()

    issd_map = {}
    for t in issd_trans:
        if t.item_id not in issd_map:
            issd_map[t.item_id] = {'ser': 0, 'pws': 0}
        issd_map[t.item_id]['ser'] += (t.ser or 0)
        issd_map[t.item_id]['pws'] += (t.pws or 0)

    # 4. BBF (prior to first_day_sel): Receipts minus Issuances prior to month
    bbf_recd = db.session.query(
        Transactions.item_id,
        func.sum(Transactions.ser).label('sum_ser'),
        func.sum(Transactions.pws).label('sum_pws')
    ).filter(
        func.lower(func.trim(Transactions.received_by)).in_(unit_name_lowers),
        Transactions.timestamp < first_day_sel
    ).group_by(Transactions.item_id).all()

    bbf_issd = db.session.query(
        Transactions.item_id,
        func.sum(Transactions.ser).label('sum_ser'),
        func.sum(Transactions.pws).label('sum_pws')
    ).filter(
        func.lower(func.trim(Transactions.issued_by)).in_(unit_name_lowers),
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

    # 5. Qty Condemned (Selected Month and All Months Cumulative)
    condemned_map = {}
    cond_trans_sel = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)).in_(unit_name_lowers),
        Transactions.timestamp >= first_day_sel,
        Transactions.timestamp < first_day_next,
        func.lower(Transactions.remarks).like('%condemn%')
    ).all()

    for c in cond_trans_sel:
        if c.item_id not in condemned_map:
            condemned_map[c.item_id] = {'unit': 0, 'fod': 0, 'ser': 0, 'pws': 0}
        qty = (c.ser or 0) + (c.pws or 0)
        condemned_map[c.item_id]['ser'] += (c.ser or 0)
        condemned_map[c.item_id]['pws'] += (c.pws or 0)
        if 'fod' in (c.received_by or '').lower() or 'fod' in (c.remarks or '').lower():
            condemned_map[c.item_id]['fod'] += qty
        else:
            condemned_map[c.item_id]['unit'] += qty

    condemned_all_map = {}
    cond_trans_all = Transactions.query.filter(
        func.lower(func.trim(Transactions.issued_by)).in_(unit_name_lowers),
        Transactions.timestamp < first_day_next,
        func.lower(Transactions.remarks).like('%condemn%')
    ).all()

    for c in cond_trans_all:
        if c.item_id not in condemned_all_map:
            condemned_all_map[c.item_id] = {'unit': 0, 'fod': 0, 'ser': 0, 'pws': 0}
        qty = (c.ser or 0) + (c.pws or 0)
        condemned_all_map[c.item_id]['ser'] += (c.ser or 0)
        condemned_all_map[c.item_id]['pws'] += (c.pws or 0)
        if 'fod' in (c.received_by or '').lower() or 'fod' in (c.remarks or '').lower():
            condemned_all_map[c.item_id]['fod'] += qty
        else:
            condemned_all_map[c.item_id]['unit'] += qty

    # 6. Current TrackUnitItems records
    track_items = TrackUnitItems.query.filter(
        func.lower(func.trim(TrackUnitItems.unit_name)).in_(unit_name_lowers)
    ).all()
    track_map = {t.item_id: t for t in track_items}

    # 7. Item Auth records
    auth_records = ItemAuth.query.filter(
        func.lower(func.trim(ItemAuth.unit_name)).in_(unit_name_lowers)
    ).all()
    auth_map = {a.item_id: a for a in auth_records}

    # 8. ScmeIssuedItems records
    scme_issued_records = ScmeIssuedItems.query.filter(
        func.lower(func.trim(ScmeIssuedItems.unit_name)).in_(unit_name_lowers)
    ).all()
    scme_issued_map = {s.item_id: s for s in scme_issued_records}

    # 9. Query Transactions issued to this unit from its parent DOU (Held Stock)
    parent_dou_names = set()
    user = LoginUser.query.filter(
        func.lower(func.trim(LoginUser.username)).in_(unit_name_lowers)
    ).first()
    if user and user.org and user.org.parent_id:
        parent_org = db.session.get(OrgLadder, user.org.parent_id)
        if parent_org and parent_org.name:
            p_clean = parent_org.name.strip()
            parent_dou_names.add(p_clean.lower())
            parent_dou_names.add(p_clean.replace('_', ' ').lower())
            parent_dou_names.add(p_clean.replace(' ', '_').lower())

    dou_trans_query = Transactions.query.filter(
        func.lower(func.trim(Transactions.received_by)).in_(unit_name_lowers)
    )
    if parent_dou_names:
        dou_trans_query = dou_trans_query.filter(
            func.lower(func.trim(Transactions.issued_by)).in_(list(parent_dou_names))
        )
    else:
        dou_trans_query = dou_trans_query.filter(
            func.lower(Transactions.issued_by).like('%dou%')
        )

    dou_issued_map = {}
    for t in dou_trans_query.all():
        if t.item_id not in dou_issued_map:
            dou_issued_map[t.item_id] = {"ser": 0, "pws": 0}
        dou_issued_map[t.item_id]["ser"] += (t.ser or 0)
        dou_issued_map[t.item_id]["pws"] += (t.pws or 0)

    # 10. ScmeItems catalog
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

    # Master ItemAuth scales (where unit_name is null or empty)
    master_auth_records = ItemAuth.query.filter(
        (ItemAuth.unit_name == None) | (ItemAuth.unit_name == '')
    ).all()
    master_auth_map = {ma.item_id: ma for ma in master_auth_records}

    # Any fallback TrackUnitItems scales across the table
    any_track_records = TrackUnitItems.query.filter(
        TrackUnitItems.scale != None,
        TrackUnitItems.scale != '',
        func.lower(func.trim(TrackUnitItems.scale)) != 'ecc'
    ).order_by(TrackUnitItems.id.desc()).all()
    any_track_map = {}
    for atr in any_track_records:
        if atr.item_id not in any_track_map:
            any_track_map[atr.item_id] = atr

    report_rows = []

    last_update_dt = None

    for item in all_items:
        auth_rec = auth_map.get(item.id)
        scme_rec = scme_issued_map.get(item.id)
        track_rec = track_map.get(item.id)
        master_auth = master_auth_map.get(item.id)
        any_track_rec = any_track_map.get(item.id)

        auth_val = 0
        if auth_rec and auth_rec.auth is not None:
            auth_val = auth_rec.auth
        elif scme_rec and scme_rec.unit_authorized is not None:
            auth_val = scme_rec.unit_authorized
        elif track_rec and track_rec.auth is not None:
            auth_val = track_rec.auth

        raw_scale = ""
        if track_rec and track_rec.scale and track_rec.scale.strip():
            raw_scale = track_rec.scale.strip()
        elif auth_rec and auth_rec.scale and auth_rec.scale.strip():
            raw_scale = auth_rec.scale.strip()
        elif scme_rec and scme_rec.scale and scme_rec.scale.strip():
            raw_scale = scme_rec.scale.strip()
        elif any_track_rec and any_track_rec.scale and any_track_rec.scale.strip():
            raw_scale = any_track_rec.scale.strip()
        elif master_auth and master_auth.scale and master_auth.scale.strip():
            raw_scale = master_auth.scale.strip()

        if raw_scale.upper() in ["ECC", ""]:
            scale_val = "N/A"
        else:
            scale_val = raw_scale.upper()

        au_val = "Nos"
        if scme_rec and scme_rec.a_u:
            au_val = scme_rec.a_u
        elif item.type and item.type in ["Nos", "Prs", "Pairs", "Sets"]:
            au_val = item.type

        item_posted_str = getattr(track_rec, 'posted_str', None)
        if item_posted_str is None or item_posted_str == 0:
            item_posted_str = posted_str

        b_ser = max(0, bbf_map.get(item.id, {}).get('ser', 0))
        b_pws = max(0, bbf_map.get(item.id, {}).get('pws', 0))
        b_total = b_ser + b_pws

        dou_ser = dou_recd_map.get(item.id, {}).get('ser', 0)
        dou_pws = dou_recd_map.get(item.id, {}).get('pws', 0)

        fod_ser = fod_recd_map.get(item.id, {}).get('ser', 0)
        fod_pws = fod_recd_map.get(item.id, {}).get('pws', 0)
        fod_total = fod_ser + fod_pws

        # Total items received during this month (DOU receipts + 2 FOD receipts)
        r_total = dou_ser + dou_pws + fod_total

        # Combined SER & PWS for calculating unit held stock
        total_r_ser = dou_ser + fod_ser
        total_r_pws = dou_pws + fod_pws

        # Condemned quantity during selected month (for column CONDEMNED THIS MONTH)
        tr_cond_date = getattr(track_rec, 'condemnation_date', None)
        tr_cond_ser = 0
        tr_cond_pws = 0
        if tr_cond_date and (first_day_sel <= tr_cond_date < first_day_next):
            tr_cond_ser = getattr(track_rec, 'condemned_ser', 0) or 0
            tr_cond_pws = getattr(track_rec, 'condemned_pws', 0) or 0
        elif not tr_cond_date and (sel_year == now_date.year and sel_month == now_date.month):
            tr_cond_ser = getattr(track_rec, 'condemned_ser', 0) or 0
            tr_cond_pws = getattr(track_rec, 'condemned_pws', 0) or 0
        tr_cond_total = tr_cond_ser + tr_cond_pws

        c_unit = condemned_map.get(item.id, {}).get('unit', 0)
        c_fod = condemned_map.get(item.id, {}).get('fod', 0)
        c_trans_total = c_unit + c_fod

        # Total condemned items for the selected month (shown in report column)
        c_total = max(tr_cond_total, c_trans_total) if tr_cond_total > 0 else c_trans_total

        # Cumulative condemned count up to the end of the selected month (for calculating STK HELD IN UNIT)
        all_tr_cond_ser = 0
        all_tr_cond_pws = 0
        if tr_cond_date and tr_cond_date < first_day_next:
            all_tr_cond_ser = getattr(track_rec, 'condemned_ser', 0) or 0
            all_tr_cond_pws = getattr(track_rec, 'condemned_pws', 0) or 0
        elif not tr_cond_date and (sel_year == now_date.year and sel_month == now_date.month):
            all_tr_cond_ser = getattr(track_rec, 'condemned_ser', 0) or 0
            all_tr_cond_pws = getattr(track_rec, 'condemned_pws', 0) or 0
        all_tr_cond_total = all_tr_cond_ser + all_tr_cond_pws

        all_c_trans_ser = condemned_all_map.get(item.id, {}).get('ser', 0)
        all_c_trans_pws = condemned_all_map.get(item.id, {}).get('pws', 0)
        all_c_trans_total = (condemned_all_map.get(item.id, {}).get('unit', 0) +
                             condemned_all_map.get(item.id, {}).get('fod', 0))

        if all_tr_cond_total > 0:
            cum_cond_ser = max(all_tr_cond_ser, all_c_trans_ser)
            cum_cond_pws = max(all_tr_cond_pws, all_c_trans_pws)
            cum_cond_total = max(all_tr_cond_total, all_c_trans_total)
        else:
            cum_cond_ser = all_c_trans_ser
            cum_cond_pws = all_c_trans_pws
            cum_cond_total = all_c_trans_total

        # Stock held in unit: cumulative stock received up to the end of selected month
        # (Receipts prior to and during selected month minus issuances)
        i_ser = issd_map.get(item.id, {}).get('ser', 0)
        i_pws = issd_map.get(item.id, {}).get('pws', 0)

        has_trans_upto_month = (
            (item.id in bbf_map) or
            (item.id in dou_recd_map) or
            (item.id in fod_recd_map) or
            (item.id in issd_map)
        )

        if has_trans_upto_month:
            stk_ser = max(0, b_ser + total_r_ser - i_ser)
            stk_pws = max(0, b_pws + total_r_pws - i_pws)
        else:
            # Fallback to TrackUnitItems: only if issued on or before selected month
            tr_issued_at = getattr(track_rec, 'issued_at', None)
            if tr_issued_at and tr_issued_at < first_day_next:
                held_ser = getattr(track_rec, 'available_ser', 0) or getattr(track_rec, 'ser', 0) or 0
                held_pws = getattr(track_rec, 'available_pws', 0) or getattr(track_rec, 'pws', 0) or 0
                if held_ser == 0 and held_pws == 0 and track_rec and getattr(track_rec, 'held', 0):
                    held_ser = track_rec.held
                stk_ser = held_ser
                stk_pws = held_pws
            elif not tr_issued_at and (sel_year == now_date.year and sel_month == now_date.month):
                held_ser = getattr(track_rec, 'available_ser', 0) or getattr(track_rec, 'ser', 0) or 0
                held_pws = getattr(track_rec, 'available_pws', 0) or getattr(track_rec, 'pws', 0) or 0
                if held_ser == 0 and held_pws == 0 and track_rec and getattr(track_rec, 'held', 0):
                    held_ser = track_rec.held
                stk_ser = held_ser
                stk_pws = held_pws
            else:
                stk_ser = 0
                stk_pws = 0

        # Deduct condemnation from stock held in unit:
        # Requirement: When calculating STK HELD IN UNIT, the condemnation count
        # must be the SUM OF ALL MONTHS for that item.
        if cum_cond_total > 0:
            sub_ser = min(stk_ser, cum_cond_ser)
            stk_ser -= sub_ser
            rem_c_ser = cum_cond_ser - sub_ser

            sub_pws = min(stk_pws, cum_cond_pws)
            stk_pws -= sub_pws
            rem_c_pws = cum_cond_pws - sub_pws

            rem_cond = (rem_c_ser + rem_c_pws) + max(0, cum_cond_total - (cum_cond_ser + cum_cond_pws))
            if rem_cond > 0:
                if stk_pws >= rem_cond:
                    stk_pws -= rem_cond
                else:
                    rem_cond -= stk_pws
                    stk_pws = 0
                    stk_ser = max(0, stk_ser - rem_cond)

        stk_total = stk_ser + stk_pws

        # If unit has adjusted PWS condition (via Unit Dashboard / api/update-held-pws),
        # reflect the custom PWS split in Stk Held With Units
        custom_held_pws = getattr(track_rec, 'held_pws', None)
        if custom_held_pws is None and track_rec and getattr(track_rec, 'pws', None) is not None:
            custom_held_pws = track_rec.pws
        if custom_held_pws is not None and stk_total > 0:
            stk_pws = max(0, min(stk_total, int(custom_held_pws)))
            stk_ser = max(0, stk_total - stk_pws)

        # defi = auth - held (updated with respect to deducted cumulative condemnation)
        defi = auth_val - stk_total

        upd_at = getattr(track_rec, 'issued_at', None)
        if upd_at:
            if not last_update_dt or upd_at > last_update_dt:
                last_update_dt = upd_at
        if tr_cond_date:
            if not last_update_dt or tr_cond_date > last_update_dt:
                last_update_dt = tr_cond_date

        report_rows.append({
            "item_id": item.id,
            "item_name": item.item_name,
            "au": au_val,
            "scale": scale_val,
            "posted_str": item_posted_str if item_posted_str > 0 else "",
            "auth": auth_val,
            "bbf_ser": b_ser,
            "bbf_pws": b_pws,
            "bbf_total": b_total,
            "recd_ser": dou_ser,
            "recd_pws": dou_pws,
            "recd_fod_ser": fod_ser,
            "recd_fod_pws": fod_pws,
            "recd_2fod": fod_total,
            "recd_total": r_total,
            "cond_unit": c_unit,
            "cond_fod": c_fod,
            "cond_total": c_total,
            "stk_ser": stk_ser,
            "stk_pws": stk_pws,
            "stk_total": stk_total,
            "sur_defi": defi,
            "defi": defi
        })

    date_updated_str = ""

    return {
        "report_rows": report_rows,
        "selected_month_str": selected_month_str,
        "selected_period_label": selected_period_label,
        "unit_username": unit_username,
        "posted_strength": posted_str,
        "date_updated_str": date_updated_str
    }
