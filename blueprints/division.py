from imports import *
from extensions import db
from models import LoginUser
from models.our_items import OurItems, ItemRequestTable, Strength, ScmeItems, ScmeIssuedItems, Units, TrackUnitItems, Transactions, UnitTpsStock
from models.org_ladder import OrgLadder
from validation import get_parent_admin,has_special_characters
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

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

    total_stock_held = 0
    stock_records = []
    if possible_names:
        records = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_([n.lower() for n in possible_names])
        ).all()

        for rec in records:
            item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
            avail_res_val = getattr(rec, 'available_res', 0) or 0
            avail_ser_val = getattr(rec, 'available_ser', 0) or 0
            avail_pws_val = getattr(rec, 'available_pws', 0) or 0
            if avail_ser_val == 0 and avail_pws_val == 0 and avail_res_val > 0:
                avail_ser_val = avail_res_val

            r_info = recd_year_map.get(rec.item_id, {"ser": avail_ser_val, "pws": avail_pws_val})
            i_info = issd_year_map.get(rec.item_id, {"ser": getattr(rec, 'ser', 0) or 0, "pws": getattr(rec, 'pws', 0) or 0})
            t_info = tps_stock_map.get(rec.item_id, {"tps_ser": 0, "tps_pws": 0})

            stock_records.append({
                "id": rec.id,
                "item_id": rec.item_id,
                "item_name": item_name,
                "scale": getattr(rec, 'scale', None) or "N/A",
                "auth": getattr(rec, 'auth', 0) or 0,
                "auth_res": getattr(rec, 'auth_res', 0) or 0,
                "auth_total": getattr(rec, 'auth', 0) or 0,
                "available_res": avail_res_val,
                "available_ser": avail_ser_val,
                "available_pws": avail_pws_val,
                "recd_year_ser": r_info["ser"],
                "recd_year_pws": r_info["pws"],
                "issd_year_ser": i_info["ser"],
                "issd_year_pws": i_info["pws"],
                "tps_ser": t_info["tps_ser"],
                "tps_pws": t_info["tps_pws"],
                "stock_total": rec.calc_held(),
                "stock_ser": getattr(rec, 'ser', 0) or 0,
                "stock_pws": getattr(rec, 'pws', 0) or 0
            })

        total_stock_held = sum(r["stock_total"] for r in stock_records) or 0

    # Build equipment map for subordinate units to populate graphs
    unit_equipment_map = {}
    if subordinate_units:
        all_unit_names = [u["name"] for u in subordinate_units if "name" in u]
        if all_unit_names:
            all_track_records = TrackUnitItems.query.filter(
                TrackUnitItems.unit_name.in_(all_unit_names)
            ).all()

            for rec in all_track_records:
                u_name = rec.unit_name
                if u_name not in unit_equipment_map:
                    unit_equipment_map[u_name] = []

                item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
                auth = rec.auth or 0
                held_qty = rec.calc_held()
                ser_qty = getattr(rec, 'ser', 0) or 0
                pws_qty = getattr(rec, 'pws', 0) or 0
                defi = max(0, auth - held_qty)

                unit_equipment_map[u_name].append({
                    "id": rec.id,
                    "item_id": rec.item_id,
                    "item_name": item_name,
                    "authorized": auth,
                    "held": held_qty,
                    "ser": ser_qty,
                    "pws": pws_qty,
                    "deficiency": defi
                })

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

    return render_template(
        '/Div_Dashboard/div_dashboard.html',
        username=username,
        units=subordinate_units,
        unit_count=len(subordinate_units),
        catalog_items=catalog_items,
        total_items=len(catalog_items),
        critical_alerts_count=0,
        total_stock_held=total_stock_held,
        stock_records=stock_records,
        unit_equipment_map=unit_equipment_map,
        issued_unit_items=issued_unit_items,
        daily_trend_labels=daily_trend_labels,
        daily_recd_data=daily_recd_data,
        daily_issd_data=daily_issd_data,
        trans_ser_pws_data=trans_ser_pws_data,
        tps_chart_data=tps_chart_data
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

        # Query track_unit_items table for item breakdown
        track_records = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_(list(possible_names))
        ).all()

        breakdown = []
        for rec in track_records:
            item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
            auth = rec.auth or 0
            held_qty = rec.held or 0
            ser_qty = getattr(rec, 'ser', 0) or 0
            pws_qty = getattr(rec, 'pws', 0) or 0
            defi = max(0, auth - held_qty)
            breakdown.append({
                "id": rec.id,
                "item_id": rec.item_id,
                "item_name": item_name,
                "authorized": auth,
                "held": held_qty,
                "ser": ser_qty,
                "pws": pws_qty,
                "deficiency": defi,
                "issued_at": rec.issued_at.strftime('%d %b %Y') if rec.issued_at else None
            })

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

        track_rec = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_(list(possible_names)),
            TrackUnitItems.item_id == item_id
        ).first()

        if track_rec:
            return jsonify({
                "success": True,
                "exists": True,
                "auth": track_rec.auth or 0,
                "held": track_rec.held or 0,
                "ser": getattr(track_rec, 'ser', 0) or 0,
                "pws": getattr(track_rec, 'pws', 0) or 0
            }), 200

        issued_rec = ScmeIssuedItems.query.filter(
            db.func.lower(ScmeIssuedItems.unit_name).in_(list(possible_names)),
            ScmeIssuedItems.item_id == item_id
        ).first()

        if issued_rec:
            return jsonify({
                "success": True,
                "exists": True,
                "auth": issued_rec.unit_authorized or 0,
                "held": issued_rec.held or 0,
                "ser": 0,
                "pws": 0
            }), 200

        return jsonify({"success": True, "exists": False, "auth": None, "held": 0, "ser": 0, "pws": 0}), 200

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

        # Add or update ScmeIssuedItems for the target unit (update auth, leave held untouched for later issue by subordinate unit)
        issued_rec = ScmeIssuedItems.query.filter(
            db.func.lower(ScmeIssuedItems.unit_name).in_(target_names),
            ScmeIssuedItems.item_id == item_id
        ).first()

        if issued_rec:
            if val_auth is not None:
                issued_rec.unit_authorized = val_auth
            issued_rec.deficiency = max(0, (issued_rec.unit_authorized or 0) - (issued_rec.held or 0))
        else:
            initial_auth = val_auth if val_auth is not None else 0
            issued_rec = ScmeIssuedItems(
                unit_name=unit_name,
                item_id=item_id,
                a_u="Nos",
                unit_authorized=initial_auth,
                scale="100%",
                held=0,
                deficiency=initial_auth
            )
            db.session.add(issued_rec)

        # Update item in TrackUnitItems table for the target unit (update available reserve and auth, leave ser/pws/held untouched)
        now_dt = datetime.now(timezone.utc) if hasattr(timezone, 'utc') else datetime.utcnow()
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

            if val_auth is not None:
                track_rec.auth = val_auth
            track_rec.issued_at = now_dt
        else:
            initial_auth = val_auth if val_auth is not None else 0
            track_rec = TrackUnitItems(
                unit_name=unit_name,
                item_id=item_id,
                auth=initial_auth,
                held=(val_ser + val_pws),
                ser=0,
                pws=0,
                available_ser=val_ser,
                available_pws=val_pws,
                available_res=val_qty,
                issued_at=now_dt
            )
            track_rec.held = track_rec.calc_held()
            db.session.add(track_rec)

        # Update the DOU (issuing division) stock record as well
        dou_rec = TrackUnitItems.query.filter(
            db.func.lower(TrackUnitItems.unit_name).in_([n.lower() for n in possible_names]),
            TrackUnitItems.item_id == item_id
        ).first()

        if dou_rec and (not track_rec or dou_rec.id != track_rec.id):
            # 1. Deduct issued counts from DOU's available reserve columns
            dou_rec.available_ser = max(0, (dou_rec.available_ser or 0) - val_ser)
            dou_rec.available_pws = max(0, (dou_rec.available_pws or 0) - val_pws)
            dou_rec.available_res = max(0, (dou_rec.available_res or 0) - val_qty)

            # 2. Accumulate issued counts into DOU's stock held columns
            dou_rec.ser = (dou_rec.ser or 0) + val_ser
            dou_rec.pws = (dou_rec.pws or 0) + val_pws
            dou_rec.held = (dou_rec.held or 0) + val_qty

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

        res_ser_now = getattr(dou_rec, 'available_ser', 0) if dou_rec else 0
        res_pws_now = getattr(dou_rec, 'available_pws', 0) if dou_rec else 0
        held_ser_now = getattr(dou_rec, 'ser', 0) if dou_rec else 0
        held_pws_now = getattr(dou_rec, 'pws', 0) if dou_rec else 0

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



