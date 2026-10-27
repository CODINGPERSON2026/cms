from datetime import datetime, timezone, timedelta
from imports import *
from extensions import db
from validation import has_special_characters
from models import LoginUser, Notification
from models.our_items import OurItems, ItemRequestTable, ScmeItems, Units, Strength, TrackUnitItems, ArmyPersonnel, UnitTpsStock, Transactions, ItemAuth, ScmeIssuedItems, CondemnationRequest
from models.org_ladder import OrgLadder


import os
import json
import uuid
import re
from werkzeug.utils import secure_filename
from flask import current_app
from blueprints.unit_monthly_generation import build_unit_monthly_report_payload


unit_bp = Blueprint("unit",__name__,url_prefix='/unit')

_condemnation_cols_checked = False

def _ensure_condemnation_columns():
    """Auto-create salvage_rv, destruction_certificate, and other condemnation columns if missing."""
    global _condemnation_cols_checked
    if _condemnation_cols_checked:
        return
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'condemnation_requests' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('condemnation_requests')]
            new_cols = [
                ('salvage_rv', 'TINYINT(1) NOT NULL DEFAULT 0'),
                ('destruction_certificate', 'TINYINT(1) NOT NULL DEFAULT 0'),
                ('rejection_reason', 'VARCHAR(500) NULL'),
                ('reviewed_by', 'VARCHAR(255) NULL'),
                ('reviewed_at', 'DATETIME NULL'),
                ('requested_by_user_id', 'INT NULL'),
                ('condemnation_no', 'VARCHAR(100) NULL'),
                ('pdf_filename', 'VARCHAR(255) NULL'),
                ('pdf_original_name', 'VARCHAR(255) NULL'),
            ]
            altered = False
            for col, col_type in new_cols:
                if col not in columns:
                    try:
                        db.session.execute(text(f'ALTER TABLE condemnation_requests ADD COLUMN {col} {col_type}'))
                        altered = True
                    except Exception as err:
                        print(f"Notice: failed to add column {col} to condemnation_requests:", err)
            if altered:
                db.session.commit()
        _condemnation_cols_checked = True
    except Exception as e:
        db.session.rollback()
        print("Auto-migration condemnation_requests notice:", e)

@unit_bp.before_request
def _unit_before_request_migration():
    _ensure_condemnation_columns()

@unit_bp.route('/monthly-reports')
def unit_monthly_reports():
    if "user_id" not in session:
        return redirect('/')

    user = LoginUser.query.get(session["user_id"])
    if not user:
        return redirect('/')

    unit_username = session.get("username") or user.username or "Unit"
    month_param = request.args.get('month')

    payload = build_unit_monthly_report_payload(unit_username, month_param)

    return render_template(
        'Unit_Dashboard/unit_monthly_reports.html',
        **payload
    )


@unit_bp.route('/')
def unit_dashboard():
    if "user_id" not in session:
        return redirect('/')

    user = LoginUser.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect('/')

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

    unit_name_lowers = [name.lower().strip() for name in unit_names if name]
    unit_records = []
    if unit_names:

        # 1. Fetch all registered catalog items with type == 'ecc', ordered by CAT-I then CAT-II
        all_ecc_items = ScmeItems.query.filter(
            db.func.lower(ScmeItems.type) == 'ecc'
        ).all()

        def cat_sort_key(item):
            cat = (item.category or "").upper().replace(" ", "").replace("-", "")
            if "CAT1" in cat or ("CATI" in cat and "CATII" not in cat):
                cat_rank = 1
            elif "CAT2" in cat or "CATII" in cat:
                cat_rank = 2
            else:
                cat_rank = 3
            return (cat_rank, (item.item_name or "").lower())

        all_ecc_items.sort(key=cat_sort_key)

        # 2. Fetch ItemAuth records for this unit
        item_auth_map = {}
        auth_records = ItemAuth.query.filter(
            db.func.lower(db.func.trim(ItemAuth.unit_name)).in_(unit_name_lowers)
        ).all()
        for a in auth_records:
            item_auth_map[a.item_id] = a.auth or 0

        # 3. Fetch TrackUnitItems records for this unit
        track_items_map = {}
        records = TrackUnitItems.query.filter(
            db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_(unit_name_lowers)
        ).all()
        for rec in records:
            iid = rec.item_id
            rec_calc_held = rec.calc_held()
            if iid not in track_items_map:
                track_items_map[iid] = {
                    "id": rec.id,
                    "scale": (rec.scale or "").strip(),
                    "auth": rec.auth or 0,
                    "held": rec_calc_held,
                    "ser": getattr(rec, 'ser', 0) or 0,
                    "pws": getattr(rec, 'pws', 0) or 0,
                    "condemned_ser": getattr(rec, 'condemned_ser', 0) or 0,
                    "condemned_pws": getattr(rec, 'condemned_pws', 0) or 0,
                    "condemnation_date": getattr(rec, 'condemnation_date', None),
                    "held_pws": getattr(rec, 'held_pws', None),
                    "available_res": (getattr(rec, 'available_ser', 0) or 0) + (getattr(rec, 'available_pws', 0) or 0),
                    "available_ser": getattr(rec, 'available_ser', 0) or 0,
                    "available_pws": getattr(rec, 'available_pws', 0) or 0,
                    "issued_at": rec.issued_at
                }
            else:
                track_items_map[iid]["held"] += rec_calc_held
                track_items_map[iid]["ser"] += (getattr(rec, 'ser', 0) or 0)
                track_items_map[iid]["pws"] += (getattr(rec, 'pws', 0) or 0)
                track_items_map[iid]["condemned_ser"] += (getattr(rec, 'condemned_ser', 0) or 0)
                track_items_map[iid]["condemned_pws"] += (getattr(rec, 'condemned_pws', 0) or 0)
                if getattr(rec, 'condemnation_date', None):
                    track_items_map[iid]["condemnation_date"] = rec.condemnation_date
                if getattr(rec, 'held_pws', None) is not None:
                    track_items_map[iid]["held_pws"] = rec.held_pws
                avail_ser = getattr(rec, 'available_ser', 0) or 0
                avail_pws = getattr(rec, 'available_pws', 0) or 0
                track_items_map[iid]["available_ser"] += avail_ser
                track_items_map[iid]["available_pws"] += avail_pws
                track_items_map[iid]["available_res"] += (avail_ser + avail_pws)

        # 4. Query aggregated TPS stock per item for this unit
        tps_stock_map = {}
        tps_records = db.session.query(
            UnitTpsStock.item_id,
            db.func.sum(UnitTpsStock.tps_ser).label("total_ser"),
            db.func.sum(UnitTpsStock.tps_pws).label("total_pws")
        ).filter(
            db.func.lower(db.func.trim(UnitTpsStock.unit_name)).in_(unit_name_lowers)
        ).group_by(UnitTpsStock.item_id).all()

        for t in tps_records:
            tps_stock_map[t.item_id] = {
                "ser": int(t.total_ser or 0),
                "pws": int(t.total_pws or 0)
            }

        # 5. Query Transactions issued to this unit (from parent DOU and direct issue from 2_FOD)
        unit_trans_query = Transactions.query.filter(
            db.func.lower(db.func.trim(Transactions.received_by)).in_(unit_name_lowers)
        )

        dou_issued_map = {}
        for t in unit_trans_query.all():
            if t.item_id not in dou_issued_map:
                dou_issued_map[t.item_id] = {"ser": 0, "pws": 0}
            dou_issued_map[t.item_id]["ser"] += (t.ser or 0)
            dou_issued_map[t.item_id]["pws"] += (t.pws or 0)

        # 6. Query ScmeIssuedItems for unit authorization
        scme_issued_map = {}
        scme_auth_records = ScmeIssuedItems.query.filter(
            db.func.lower(db.func.trim(ScmeIssuedItems.unit_name)).in_(unit_name_lowers)
        ).all()
        for s_rec in scme_auth_records:
            scme_issued_map[s_rec.item_id] = s_rec.unit_authorized or 0

        # Build complete unit_records array for ALL registered catalog items
        for item in all_ecc_items:
            iid = item.id
            item_name = item.item_name
            
            # Auth prioritization: ItemAuth first, then TrackUnitItems, then ScmeIssuedItems, else 0
            if iid in item_auth_map:
                auth = item_auth_map[iid]
            elif iid in track_items_map and track_items_map[iid]["auth"] > 0:
                auth = track_items_map[iid]["auth"]
            elif iid in scme_issued_map:
                auth = scme_issued_map[iid]
            else:
                auth = 0

            tr_data = track_items_map.get(iid, {
                "id": None,
                "scale": "—",
                "auth": 0,
                "held": 0,
                "ser": 0,
                "pws": 0,
                "available_res": 0,
                "available_ser": 0,
                "available_pws": 0,
                "issued_at": None
            })

            tps_data = tps_stock_map.get(iid, {"ser": 0, "pws": 0})
            tps_ser = tps_data["ser"]
            tps_pws = tps_data["pws"]
            tps_total = tps_ser + tps_pws

            res_ser = tr_data.get("available_ser", 0) or 0
            res_pws = tr_data.get("available_pws", 0) or 0
            held_ser = tr_data.get("ser", 0) or 0
            held_pws = tr_data.get("pws", 0) or 0

            ser_val = res_ser + held_ser + tps_ser
            pws_val = res_pws + held_pws + tps_pws

            # Original stock issued to this unit from its parent DOU (with SER and PWS)
            if iid in dou_issued_map:
                orig_dou_ser = dou_issued_map[iid]["ser"]
                orig_dou_pws = dou_issued_map[iid]["pws"]
            else:
                orig_dou_ser = res_ser
                orig_dou_pws = res_pws
                if orig_dou_ser == 0 and orig_dou_pws == 0:
                    orig_dou_ser = held_ser
                    orig_dou_pws = held_pws
                if orig_dou_ser == 0 and orig_dou_pws == 0 and tr_data.get("held", 0) > 0:
                    orig_dou_ser = tr_data.get("held", 0)

            cond_ser = tr_data.get("condemned_ser", 0) or 0
            cond_pws = tr_data.get("condemned_pws", 0) or 0
            cond_date = tr_data.get("condemnation_date")

            # Total held stock = original total stock - total condemned
            orig_held_total = orig_dou_ser + orig_dou_pws
            total_condemned = cond_ser + cond_pws
            total_stock = max(0, orig_held_total - total_condemned)
            dou_held = total_stock

            # Ledger-based condition counts from receipts minus condemnations
            rem_ser = max(0, orig_dou_ser - cond_ser)
            rem_pws = max(0, orig_dou_pws - cond_pws)
            if rem_ser + rem_pws > total_stock:
                if cond_pws > orig_dou_pws:
                    rem_ser = max(0, rem_ser - (cond_pws - orig_dou_pws))
                if cond_ser > orig_dou_ser:
                    rem_pws = max(0, rem_pws - (cond_ser - orig_dou_ser))

            # Condition counts: if unit customized held_pws, respect custom condition split; else ledger balance
            custom_held_pws = tr_data.get("held_pws")
            if custom_held_pws is not None and total_stock > 0:
                dou_pws = max(0, min(total_stock, int(custom_held_pws)))
                dou_ser = total_stock - dou_pws
            elif (orig_dou_ser + orig_dou_pws) > 0 and total_stock > 0:
                dou_ser = rem_ser
                dou_pws = max(0, total_stock - dou_ser)
            elif total_stock > 0:
                dou_ser = total_stock
                dou_pws = 0
            else:
                dou_ser = 0
                dou_pws = 0

            u_rec = {
                "id": tr_data["id"] or iid,
                "item_id": iid,
                "item_name": item_name,
                "category": item.category or "General",
                "scale": tr_data["scale"],
                "authorized": auth,
                "held": dou_held,
                "dou_held": dou_held,
                "dou_ser": dou_ser,
                "dou_pws": dou_pws,
                "orig_dou_ser": orig_dou_ser,
                "orig_dou_pws": orig_dou_pws,
                "orig_held_total": orig_held_total,
                "condemned_ser": cond_ser,
                "condemned_pws": cond_pws,
                "total_stock": total_stock,
                "condemnation_date": cond_date.strftime("%d-%m-%Y") if cond_date else "",
                "ser": ser_val,
                "pws": pws_val,
                "available_res": tr_data["available_res"],
                "available_ser": tr_data["available_ser"],
                "available_pws": tr_data["available_pws"],
                "tps_ser": tps_ser,
                "tps_pws": tps_pws,
                "issued_at": tr_data["issued_at"]
            }
            
            # DEFI = AUTH - HELD (where HELD has condemned subtracted: AUTH - ORIG_HELD + COND)
            u_rec["deficiency"] = u_rec["authorized"] - u_rec["held"]

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

    if unit_names:
        # Check UnitTpsStock records for daily trend dates
        tps_daily_recs = UnitTpsStock.query.filter(
            db.func.lower(db.func.trim(UnitTpsStock.unit_name)).in_(unit_name_lowers)
        ).all()
        for tr in tps_daily_recs:
            dt = tr.updated_at
            if dt:
                item_name = tr.item.item_name if tr.item else f"Item #{tr.item_id}"
                t_total = (tr.tps_ser or 0) + (tr.tps_pws or 0)
                if t_total > 0:
                    dt_str = dt.strftime("%Y-%m-%d")
                    daily_issue_totals[dt_str] = daily_issue_totals.get(dt_str, 0) + t_total
                    if item_name not in daily_item_issue_map:
                        daily_item_issue_map[item_name] = {}
                    daily_item_issue_map[item_name][dt_str] = daily_item_issue_map[item_name].get(dt_str, 0) + t_total

        if records:
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

    # Filter active_unit_records for graphs (only items existing or held in stock)
    active_unit_records = [
        rec for rec in unit_records 
        if (rec.get("authorized", 0) > 0 or 
            rec.get("held", 0) > 0 or 
            (rec.get("tps_ser", 0) + rec.get("tps_pws", 0)) > 0 or
            (rec.get("ser", 0) + rec.get("pws", 0)) > 0)
    ]

    unit_tps_chart_data = {}
    if active_unit_records:
        for rec in active_unit_records:
            item_name = rec["item_name"]
            unit_tps_chart_data[item_name] = {
                "ser": rec.get("tps_ser", 0),
                "pws": rec.get("tps_pws", 0)
            }

    # Query Top Distributed Items strictly from unit_tps_stock
    top_distributed_items = []
    if unit_name_lowers:
        tps_top_recs = db.session.query(
            UnitTpsStock.item_id,
            db.func.sum(UnitTpsStock.tps_ser + UnitTpsStock.tps_pws).label("total_qty")
        ).filter(
            db.func.lower(db.func.trim(UnitTpsStock.unit_name)).in_(unit_name_lowers)
        ).group_by(UnitTpsStock.item_id).order_by(db.desc("total_qty")).limit(7).all()

        for r in tps_top_recs:
            if r.total_qty and int(r.total_qty) > 0:
                scme_item = ScmeItems.query.get(r.item_id)
                iname = scme_item.item_name if scme_item else f"Item #{r.item_id}"
                top_distributed_items.append({
                    "item_name": iname,
                    "quantity": int(r.total_qty)
                })

    # Fetch latest condemnation file for the unit to reuse across items
    latest_condemnation_file = None
    if unit_names:
        _ensure_condemnation_columns()
        last_cond_req = CondemnationRequest.query.filter(
            db.func.lower(db.func.trim(CondemnationRequest.unit_name)).in_(unit_name_lowers),
            CondemnationRequest.pdf_filename.isnot(None),
            CondemnationRequest.pdf_filename != ''
        ).order_by(CondemnationRequest.id.desc()).first()
        if last_cond_req and last_cond_req.pdf_filename:
            latest_condemnation_file = {
                "filename": last_cond_req.pdf_filename,
                "original_name": last_cond_req.pdf_original_name or last_cond_req.pdf_filename,
                "condemnation_no": last_cond_req.condemnation_no or ""
            }

    # Build Dataset for Overall Analysis Chart (AUTH vs DEFI for Unit Login by Category)
    overall_analysis_data = []
    if unit_records:
        for rec in unit_records:
            auth_val = int(rec.get("authorized", 0) or 0)
            held_val = int(rec.get("held", 0) or 0)
            defi_val = max(0, auth_val - held_val)
            cat_str = (rec.get("category") or "CAT-I").strip().upper()
            norm_cat = "CAT-II" if ("CAT-II" in cat_str or "CAT II" in cat_str or "CAT2" in cat_str) else "CAT-I"
            overall_analysis_data.append({
                "item_id": rec.get("item_id"),
                "item_name": rec.get("item_name"),
                "category": norm_cat,
                "auth": auth_val,
                "held": held_val,
                "defi": defi_val
            })
    else:
        ecc_items = ScmeItems.query.filter(db.func.lower(ScmeItems.type) == 'ecc').order_by(ScmeItems.id).all()
        for item in ecc_items:
            cat_str = (item.category or "CAT-I").strip().upper()
            norm_cat = "CAT-II" if ("CAT-II" in cat_str or "CAT II" in cat_str or "CAT2" in cat_str) else "CAT-I"
            overall_analysis_data.append({
                "item_id": item.id,
                "item_name": item.item_name,
                "category": norm_cat,
                "auth": 0,
                "held": 0,
                "defi": 0
            })

    return render_template(
        '/Unit_Dashboard/unit_dashboard.html',
        username=username,
        unit_records=unit_records,
        active_unit_records=active_unit_records,
        personnel_list=personnel_list,
        daily_trend_labels=daily_trend_labels,
        daily_trend_data=daily_trend_data,
        daily_item_trend_map=daily_item_trend_map,
        unit_tps_chart_data=unit_tps_chart_data,
        top_distributed_items=top_distributed_items,
        latest_condemnation_file=latest_condemnation_file,
        overall_analysis_data=overall_analysis_data
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


@unit_bp.route('/api/update-held-pws', methods=['POST'])
def api_update_held_pws():
    """Allows unit to adjust SER or PWS condition within constraint: SER + PWS = TOTAL STOCK."""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not authenticated."}), 401

    try:
        user = LoginUser.query.get(session["user_id"])
        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404

        unit_name = (user.org.name if user.org else None) or user.username or ""
        unit_name = unit_name.strip()
        unit_name_lowers = [
            unit_name.lower(),
            unit_name.replace('_', ' ').lower(),
            unit_name.replace(' ', '_').lower()
        ]

        data = request.get_json() or {}
        item_id = data.get("item_id")
        new_pws = data.get("pws")
        new_ser = data.get("ser")
        total_stock = data.get("total_stock")

        if item_id is None or (new_pws is None and new_ser is None):
            return jsonify({"success": False, "message": "Item ID and at least one of SER or PWS are required."}), 400

        try:
            item_id = int(item_id)
            if new_pws is not None:
                new_pws = max(0, int(new_pws))
            if new_ser is not None:
                new_ser = max(0, int(new_ser))
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "SER and PWS must be integers."}), 400

        track_rec = TrackUnitItems.query.filter(
            db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_(unit_name_lowers),
            TrackUnitItems.item_id == item_id
        ).first()

        # If total_stock provided by frontend or compute from DB
        if total_stock is not None:
            try:
                total_stock = max(0, int(total_stock))
            except (ValueError, TypeError):
                total_stock = None

        if total_stock is None:
            cond_ser = getattr(track_rec, 'condemned_ser', 0) or 0 if track_rec else 0
            cond_pws = getattr(track_rec, 'condemned_pws', 0) or 0 if track_rec else 0

            unit_trans_query = Transactions.query.filter(
                db.func.lower(db.func.trim(Transactions.received_by)).in_(unit_name_lowers),
                Transactions.item_id == item_id
            )
            trans_list = unit_trans_query.all()
            if trans_list:
                orig_dou_ser = sum(t.ser or 0 for t in trans_list)
                orig_dou_pws = sum(t.pws or 0 for t in trans_list)
            elif track_rec:
                orig_dou_ser = (track_rec.available_ser or 0) or (track_rec.ser or 0)
                orig_dou_pws = (track_rec.available_pws or 0) or (track_rec.pws or 0)
                if orig_dou_ser == 0 and orig_dou_pws == 0:
                    orig_dou_ser = (track_rec.held or 0) + cond_ser
                    orig_dou_pws = cond_pws
            else:
                orig_dou_ser = 0
                orig_dou_pws = 0

            total_stock = max(0, (orig_dou_ser + orig_dou_pws) - (cond_ser + cond_pws))

        # Enforce split constraint: SER + PWS = total_stock
        if new_ser is not None and new_pws is None:
            if new_ser > total_stock:
                new_ser = total_stock
            new_pws = max(0, total_stock - new_ser)
        elif new_pws is not None and new_ser is None:
            if new_pws > total_stock:
                new_pws = total_stock
            new_ser = max(0, total_stock - new_pws)
        else:
            # Both provided: if new_ser + new_pws != total_stock, clamp pws = total_stock - new_ser
            if new_ser > total_stock:
                new_ser = total_stock
            new_pws = max(0, total_stock - new_ser)

        if track_rec:
            track_rec.held = total_stock
            track_rec.held_pws = new_pws
            track_rec.pws = new_pws
            track_rec.ser = new_ser
        else:
            track_rec = TrackUnitItems(
                unit_name=unit_name,
                item_id=item_id,
                held=total_stock,
                ser=new_ser,
                pws=new_pws
            )
            track_rec.held_pws = new_pws
            db.session.add(track_rec)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Held condition updated: SER={new_ser}, PWS={new_pws}",
            "item_id": item_id,
            "ser": new_ser,
            "pws": new_pws,
            "total_stock": total_stock
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


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



# THIS BELOW FUNCTIONALITY IS FOR ADDING USERS AND MANAGING DATA BY SUPER_ADMIN (ORD) AND DIVISION_ADMIN
@unit_bp.route("/org")
def manage_org():
    if "user_id" not in session or session.get("role") not in ["super_admin", "division_admin"]:
        return redirect("/")

    user = LoginUser.query.get(session["user_id"])
    if not user:
        return redirect("/")

    orgs = OrgLadder.query.order_by(
        OrgLadder.name
    ).all()

    return render_template(
        "create_user/create_user.html",
        orgs=orgs,
        current_user=user
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

        if not current_user or current_user.role not in ["super_admin", "division_admin"]:
            return jsonify({"success": False, "message": "Only ORD (super_admin) and Division Admin are authorized to create users."}), 403

        data = request.get_json() or {}

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        role = data.get("role", "").strip()
        parent_id = data.get("parent_id")

        # ---------------- DIVISION ADMIN RESTRICTION ----------------
        if current_user.role == "division_admin":
            if role != "unit":
                return jsonify({"success": False, "message": "Division Admin can only create Unit users."}), 403
            # Force parent_id to Division Admin's organization ID
            parent_id = current_user.org_id

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

        # Create Notification entry
        try:
            item_name_str = unit_item.item.item_name if (unit_item and unit_item.item) else f"Item #{unit_item.item_id}"
            notif = Notification(
                title="Equipment Issued to Personnel",
                message=f"Issued {ser_qty} SER / {pws_qty} PWS of '{item_name_str}' to {personnel_desc}.",
                sender_name=session.get("username", unit_name),
                target_user=unit_name,
                target_role="unit",
                item_id=unit_item.item_id
            )
            db.session.add(notif)
        except Exception as ne:
            print("Notification insert notice:", ne)

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


@unit_bp.route('/all_items', methods=['GET'])
def get_all_unit_items():
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

        unit_name_lowers = [name.lower().strip() for name in unit_names if name] if unit_names else [username.lower().strip()]

        # 1. Fetch items registered in catalog with type == 'ecc'
        all_scme_items = ScmeItems.query.filter(
            db.func.lower(ScmeItems.type) == 'ecc'
        ).all()

        def cat_sort_key(item):
            cat = (item.category or "").upper().replace(" ", "").replace("-", "")
            if "CAT1" in cat or ("CATI" in cat and "CATII" not in cat):
                cat_rank = 1
            elif "CAT2" in cat or "CATII" in cat:
                cat_rank = 2
            else:
                cat_rank = 3
            return (cat_rank, (item.item_name or "").lower())

        all_scme_items.sort(key=cat_sort_key)

        # 2. Fetch ItemAuth records for this unit
        item_auth_map = {}
        if unit_name_lowers:
            auth_recs = ItemAuth.query.filter(
                db.func.lower(db.func.trim(ItemAuth.unit_name)).in_(unit_name_lowers)
            ).all()
            for a in auth_recs:
                item_auth_map[a.item_id] = a.auth or 0

        # 3. Fetch TrackUnitItems records for this unit
        track_items_map = {}
        if unit_name_lowers:
            track_recs = TrackUnitItems.query.filter(
                db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_(unit_name_lowers)
            ).all()
            for tr in track_recs:
                iid = tr.item_id
                if iid not in track_items_map:
                    track_items_map[iid] = {
                        "auth": tr.auth or 0,
                        "scale": (tr.scale or "").strip(),
                        "ser": getattr(tr, 'ser', 0) or 0,
                        "pws": getattr(tr, 'pws', 0) or 0,
                        "available_ser": getattr(tr, 'available_ser', 0) or 0,
                        "available_pws": getattr(tr, 'available_pws', 0) or 0,
                        "condemned_ser": getattr(tr, 'condemned_ser', 0) or 0,
                        "condemned_pws": getattr(tr, 'condemned_pws', 0) or 0,
                    }
                else:
                    track_items_map[iid]["ser"] += getattr(tr, 'ser', 0) or 0
                    track_items_map[iid]["pws"] += getattr(tr, 'pws', 0) or 0
                    track_items_map[iid]["available_ser"] += getattr(tr, 'available_ser', 0) or 0
                    track_items_map[iid]["available_pws"] += getattr(tr, 'available_pws', 0) or 0
                    track_items_map[iid]["condemned_ser"] += getattr(tr, 'condemned_ser', 0) or 0
                    track_items_map[iid]["condemned_pws"] += getattr(tr, 'condemned_pws', 0) or 0

        # 4. Fetch TPS Stock (issued to personnel) aggregated for this unit
        tps_stock_map = {}
        if unit_name_lowers:
            tps_recs = db.session.query(
                UnitTpsStock.item_id,
                db.func.sum(UnitTpsStock.tps_ser).label("total_ser"),
                db.func.sum(UnitTpsStock.tps_pws).label("total_pws")
            ).filter(
                db.func.lower(db.func.trim(UnitTpsStock.unit_name)).in_(unit_name_lowers)
            ).group_by(UnitTpsStock.item_id).all()

            for t in tps_recs:
                tps_stock_map[t.item_id] = {
                    "tps_ser": int(t.total_ser or 0),
                    "tps_pws": int(t.total_pws or 0)
                }

        items_list = []
        categories = set()

        for item in all_scme_items:
            iid = item.id
            cat = item.category or "General"
            categories.add(cat)

            # Determine authorization: ItemAuth takes precedence, then TrackUnitItems, else 0
            if iid in item_auth_map:
                authorized = item_auth_map[iid]
            elif iid in track_items_map:
                authorized = track_items_map[iid]["auth"]
            else:
                authorized = 0

            track = track_items_map.get(iid, {
                "auth": 0,
                "scale": "—",
                "ser": 0,
                "pws": 0,
                "available_ser": 0,
                "available_pws": 0,
                "condemned_ser": 0,
                "condemned_pws": 0
            })

            tps = tps_stock_map.get(iid, {"tps_ser": 0, "tps_pws": 0})

            res_ser = track["available_ser"]
            res_pws = track["available_pws"]
            held_ser = track["ser"]
            held_pws = track["pws"]
            tps_ser = tps["tps_ser"]
            tps_pws = tps["tps_pws"]
            cond_ser = track.get("condemned_ser", 0)
            cond_pws = track.get("condemned_pws", 0)

            total_ser = res_ser + held_ser + tps_ser
            total_pws = res_pws + held_pws + tps_pws
            # held = held - (condemned_ser + condemned_pws)
            held = max(0, (total_ser + total_pws) - (cond_ser + cond_pws))

            items_list.append({
                "id": iid,
                "item_name": item.item_name,
                "held": held,
                "authorized": authorized
            })

        return jsonify({
            "success": True,
            "items": items_list,
            "summary": {
                "total_catalog_items": len(all_scme_items),
                "total_held_qty": sum(item["held"] for item in items_list),
                "total_authorized_qty": sum(item["authorized"] for item in items_list)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error fetching all items for unit: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@unit_bp.route('/api/update-tps-stock', methods=['POST'])
def update_tps_stock():
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

        unit_name_lowers = [name.lower().strip() for name in unit_names if name] if unit_names else [username.lower().strip()]
        target_unit_name = username.strip()

        data = request.get_json() or {}
        items_payload = data.get("items") if "items" in data else ([data] if "item_id" in data else [])

        for item_data in items_payload:
            item_id = item_data.get("item_id")
            if not item_id:
                continue
            
            if "tps_ser" in item_data or "tps_pws" in item_data:
                new_tps_ser = max(0, int(item_data.get("tps_ser", 0)))
                new_tps_pws = max(0, int(item_data.get("tps_pws", 0)))

                personnel_tps = db.session.query(
                    db.func.sum(UnitTpsStock.tps_ser).label("p_ser"),
                    db.func.sum(UnitTpsStock.tps_pws).label("p_pws")
                ).filter(
                    db.func.lower(db.func.trim(UnitTpsStock.unit_name)).in_(unit_name_lowers),
                    UnitTpsStock.item_id == item_id,
                    UnitTpsStock.army_number.isnot(None)
                ).first()

                personnel_ser = int(personnel_tps.p_ser or 0) if personnel_tps else 0
                personnel_pws = int(personnel_tps.p_pws or 0) if personnel_tps else 0

                unassigned_ser = max(0, new_tps_ser - personnel_ser)
                unassigned_pws = max(0, new_tps_pws - personnel_pws)

                unassigned_rec = UnitTpsStock.query.filter(
                    db.func.lower(db.func.trim(UnitTpsStock.unit_name)).in_(unit_name_lowers),
                    UnitTpsStock.item_id == item_id,
                    UnitTpsStock.army_number.is_(None)
                ).first()

                if unassigned_rec:
                    unassigned_rec.tps_ser = unassigned_ser
                    unassigned_rec.tps_pws = unassigned_pws
                else:
                    unassigned_rec = UnitTpsStock(
                        unit_name=target_unit_name,
                        item_id=item_id,
                        army_number=None,
                        tps_ser=unassigned_ser,
                        tps_pws=unassigned_pws
                    )
                    db.session.add(unassigned_rec)

            # Update condemnation in TrackUnitItems
            if "condemned_ser" in item_data or "condemned_pws" in item_data:
                c_ser = max(0, int(item_data.get("condemned_ser", 0)))
                c_pws = max(0, int(item_data.get("condemned_pws", 0)))
                now_dt = datetime.now()

                track_rec = TrackUnitItems.query.filter(
                    db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_(unit_name_lowers),
                    TrackUnitItems.item_id == item_id
                ).first()

                if track_rec:
                    track_rec.condemned_ser = c_ser
                    track_rec.condemned_pws = c_pws
                    track_rec.condemnation_date = now_dt
                    track_rec.held = track_rec.calc_held()
                else:
                    track_rec = TrackUnitItems(
                        unit_name=target_unit_name,
                        item_id=item_id,
                        condemned_ser=c_ser,
                        condemned_pws=c_pws,
                        condemnation_date=now_dt
                    )
                    track_rec.held = track_rec.calc_held()
                    db.session.add(track_rec)

        db.session.commit()
        return jsonify({"success": True, "message": "Changes saved successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating TPS stock: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@unit_bp.route('/api/submit-condemnation-request', methods=['POST'])
def submit_condemnation_request():
    """Unit submits condemnation details — auto-applied immediately (no DOU wait required)."""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        user = LoginUser.query.get(session["user_id"])
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        # Resolve unit name
        unit_name = (user.org.name if user.org else None) or user.username or ""
        unit_name = unit_name.strip()

        # Resolve parent DOU name from OrgLadder (optional — fallback to unit name)
        parent_dou_name = ""
        if user.org and user.org.parent_id:
            parent_org = db.session.get(OrgLadder, user.org.parent_id)
            if parent_org and parent_org.name:
                parent_dou_name = parent_org.name.strip()
        if not parent_dou_name:
            parent_dou_name = unit_name  # Fallback: use own unit name

        def _parse_bool(val):
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ['true', '1', 'yes', 'on']

        if request.is_json:
            data = request.get_json() or {}
            raw_items = data.get("items")
            item_id  = data.get("item_id")
            req_ser  = max(0, int(data.get("req_ser", 0) or 0))
            req_pws  = max(0, int(data.get("req_pws", 0) or 0))
            condemnation_no = (data.get("condemnation_no") or "").strip()[:100]
            reason   = (data.get("reason") or "").strip()[:500]
            salvage_rv = _parse_bool(data.get("salvage_rv", False))
            destruction_certificate = _parse_bool(data.get("destruction_certificate", False))
            pdf_file = None
        else:
            raw_items = request.form.get("items")
            item_id  = request.form.get("item_id")
            req_ser  = max(0, int(request.form.get("req_ser", 0) or 0))
            req_pws  = max(0, int(request.form.get("req_pws", 0) or 0))
            condemnation_no = (request.form.get("condemnation_no") or "").strip()[:100]
            reason   = (request.form.get("reason") or "").strip()[:500]
            salvage_rv = _parse_bool(request.form.get("salvage_rv", False))
            destruction_certificate = _parse_bool(request.form.get("destruction_certificate", False))
            pdf_file = request.files.get("pdf")

        # Parse items list (batch or single)
        items_to_process = []
        if raw_items:
            if isinstance(raw_items, str):
                try:
                    items_to_process = json.loads(raw_items)
                except Exception:
                    items_to_process = []
            elif isinstance(raw_items, list):
                items_to_process = raw_items

        if not items_to_process and item_id:
            items_to_process = [{
                "item_id": item_id,
                "req_ser": req_ser,
                "req_pws": req_pws
            }]

        if not items_to_process:
            return jsonify({"success": False, "message": "At least one item must be chosen for condemnation."}), 400

        # Validate that every item has valid ID and at least 1 quantity to condemn
        valid_items = []
        for itm in items_to_process:
            try:
                iid = int(itm.get("item_id") or 0)
            except (ValueError, TypeError):
                continue
            s_qty = max(0, int(itm.get("req_ser", 0) or 0))
            p_qty = max(0, int(itm.get("req_pws", 0) or 0))
            if iid and (s_qty > 0 or p_qty > 0):
                valid_items.append({
                    "item_id": iid,
                    "req_ser": s_qty,
                    "req_pws": p_qty
                })

        if not valid_items:
            return jsonify({"success": False, "message": "Enter at least 1 SER or PWS quantity to condemn."}), 400

        if not condemnation_no:
            return jsonify({"success": False, "message": "Condemnation Number is mandatory."}), 400

        # Each condemnation process requires an uploaded PDF
        upload_folder = current_app.config.get("CONDEMNATION_UPLOAD_FOLDER", r"C:\Condemnation_pdf")
        os.makedirs(upload_folder, exist_ok=True)

        if not pdf_file or not pdf_file.filename or not pdf_file.filename.strip():
            return jsonify({"success": False, "message": "Attaching a PDF document is mandatory for each condemnation process."}), 400

        if not pdf_file.filename.lower().endswith(".pdf"):
            return jsonify({"success": False, "message": "Only PDF files (.pdf) are allowed."}), 400

        pdf_bytes = pdf_file.read()
        if not pdf_bytes:
            return jsonify({"success": False, "message": "The attached PDF file is empty."}), 400

        raw_name = os.path.splitext(pdf_file.filename)[0]
        base_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_name).strip('_') or "condemnation"
        timestamp_str = datetime.now().strftime("%d_%b_%y_%I_%M%p").upper()
        safe_name = f"{base_clean}_{timestamp_str}.pdf"

        counter = 1
        while os.path.exists(os.path.join(upload_folder, safe_name)):
            safe_name = f"{base_clean}_{timestamp_str}_{counter}.pdf"
            counter += 1

        pdf_original_name = pdf_file.filename

        unit_name_lowers = [
            unit_name.lower(),
            unit_name.replace('_', ' ').lower(),
            unit_name.replace(' ', '_').lower()
        ]
        now_dt = datetime.now()

        created_requests = []
        updated_records = []

        for itm in valid_items:
            curr_item_id = itm["item_id"]
            curr_ser = itm["req_ser"]
            curr_pws = itm["req_pws"]

            track_rec = TrackUnitItems.query.filter(
                db.func.lower(db.func.trim(TrackUnitItems.unit_name)).in_(unit_name_lowers),
                TrackUnitItems.item_id == curr_item_id
            ).first()

            if track_rec:
                track_rec.condemned_ser = (track_rec.condemned_ser or 0) + curr_ser
                track_rec.condemned_pws = (track_rec.condemned_pws or 0) + curr_pws
                track_rec.condemnation_date = now_dt
                new_cond_ser = track_rec.condemned_ser
                new_cond_pws = track_rec.condemned_pws
            else:
                track_rec = TrackUnitItems(
                    unit_name=unit_name,
                    item_id=curr_item_id,
                    condemned_ser=curr_ser,
                    condemned_pws=curr_pws,
                    condemnation_date=now_dt
                )
                db.session.add(track_rec)
                new_cond_ser = curr_ser
                new_cond_pws = curr_pws

            dou_trans_query = Transactions.query.filter(
                db.func.lower(db.func.trim(Transactions.received_by)).in_(unit_name_lowers),
                Transactions.item_id == curr_item_id
            )
            if parent_dou_name:
                p_names = [parent_dou_name.lower(), parent_dou_name.replace('_', ' ').lower(), parent_dou_name.replace(' ', '_').lower()]
                dou_trans_query = dou_trans_query.filter(db.func.lower(db.func.trim(Transactions.issued_by)).in_(p_names))

            trans_list = dou_trans_query.all()
            if trans_list:
                orig_dou_ser = sum(t.ser or 0 for t in trans_list)
                orig_dou_pws = sum(t.pws or 0 for t in trans_list)
            else:
                orig_dou_ser = (track_rec.available_ser or 0) or (track_rec.ser or 0)
                orig_dou_pws = (track_rec.available_pws or 0) or (track_rec.pws or 0)
                if orig_dou_ser == 0 and orig_dou_pws == 0 and (track_rec.held or 0) > 0:
                    orig_dou_ser = track_rec.held or 0

            orig_held_total = orig_dou_ser + orig_dou_pws
            total_condemned = new_cond_ser + new_cond_pws
            new_dou_held = max(0, orig_held_total - total_condemned)

            custom_held_pws = getattr(track_rec, 'held_pws', None)
            rem_ser = max(0, orig_dou_ser - new_cond_ser)
            rem_pws = max(0, orig_dou_pws - new_cond_pws)
            if rem_ser + rem_pws > new_dou_held:
                if new_cond_pws > orig_dou_pws:
                    rem_ser = max(0, rem_ser - (new_cond_pws - orig_dou_ser))
                if new_cond_ser > orig_dou_ser:
                    rem_pws = max(0, rem_pws - (new_cond_ser - orig_dou_ser))

            if custom_held_pws is not None and new_dou_held > 0:
                new_dou_pws = max(0, min(new_dou_held, int(custom_held_pws)))
                new_dou_ser = new_dou_held - new_dou_pws
            elif (orig_dou_ser + orig_dou_pws) > 0 and new_dou_held > 0:
                new_dou_ser = rem_ser
                new_dou_pws = max(0, new_dou_held - new_dou_ser)
            elif new_dou_held > 0:
                new_dou_ser = new_dou_held
                new_dou_pws = 0
            else:
                new_dou_ser = 0
                new_dou_pws = 0

            track_rec.held = new_dou_held
            track_rec.held_pws = new_dou_pws
            track_rec.ser = new_dou_ser
            track_rec.pws = new_dou_pws

            new_req = CondemnationRequest(
                unit_name=unit_name,
                parent_dou_name=parent_dou_name,
                item_id=curr_item_id,
                req_ser=curr_ser,
                req_pws=curr_pws,
                condemnation_no=condemnation_no,
                pdf_filename=safe_name,
                pdf_original_name=pdf_original_name,
                reason=reason,
                status='approved',
                requested_by_user_id=user.id,
                salvage_rv=salvage_rv,
                destruction_certificate=destruction_certificate
            )
            new_req.reviewed_by = unit_name
            new_req.reviewed_at = now_dt
            db.session.add(new_req)
            created_requests.append(new_req)

            updated_records.append({
                "item_id": curr_item_id,
                "condemned_ser": new_cond_ser,
                "condemned_pws": new_cond_pws,
                "dou_ser": new_dou_ser,
                "dou_pws": new_dou_pws,
                "dou_held": new_dou_held,
                "total_stock": new_dou_held,
                "orig_held_total": orig_dou_ser + orig_dou_pws
            })

        db.session.commit()

        # Save single PDF for this condemnation batch
        file_path = os.path.join(upload_folder, safe_name)
        try:
            with open(file_path, 'wb') as f:
                f.write(pdf_bytes)
        except Exception as file_err:
            for req in created_requests:
                db.session.delete(req)
            db.session.commit()
            raise file_err

        return jsonify({
            "success": True,
            "message": f"Condemnation recorded and applied successfully for {len(valid_items)} item(s).",
            "count": len(valid_items),
            "updated_items": updated_records,
            "pdf_filename": safe_name,
            "pdf_original_name": pdf_original_name,
            "condemnation_no": condemnation_no
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error submitting condemnation request: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@unit_bp.route('/api/condemnation-request-status', methods=['GET'])
def condemnation_request_status():
    """Returns all condemnation requests for the current unit (for the status tracker)."""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        user = LoginUser.query.get(session["user_id"])
        unit_name = (user.org.name if user.org else None) or user.username or ""
        unit_name = unit_name.strip()
        unit_name_lowers = [
            unit_name.lower(),
            unit_name.replace('_', ' ').lower(),
            unit_name.replace(' ', '_').lower()
        ]

        reqs = CondemnationRequest.query.filter(
            db.func.lower(db.func.trim(CondemnationRequest.unit_name)).in_(unit_name_lowers)
        ).order_by(CondemnationRequest.created_at.desc()).all()

        result = []
        for r in reqs:
            item_name = r.item.item_name if r.item else f"Item #{r.item_id}"
            result.append({
                "id": r.id,
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

        return jsonify({"success": True, "requests": result}), 200

    except Exception as e:
        print(f"Error fetching condemnation status: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

