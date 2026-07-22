from imports import *
from extensions import db
from models import LoginUser
from models.our_items import OurItems, ItemRequestTable, Strength, ScmeItems, EccMonthlyState, ScmeIssuedItems, Units, TrackUnitItems
from models.org_ladder import OrgLadder
from validation import get_parent_admin,has_special_characters
from datetime import datetime, timezone
from sqlalchemy import text

div_bp = Blueprint("div",__name__,url_prefix='/division_admin')


def _ensure_track_unit_items_migrated():
    """Ensure track_unit_items table exists and drop legacy columns from unit_strength MySQL table."""
    try:
        db.create_all()
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

    total_stock_held = 0
    stock_records = []
    if possible_names:
        records = EccMonthlyState.query.filter(
            db.func.lower(EccMonthlyState.bbf_division).in_([n.lower() for n in possible_names])
        ).all()

        if not records and user and user.username:
            prefix = user.username.split('_')[0]
            if prefix and prefix.isdigit():
                records = EccMonthlyState.query.filter(
                    EccMonthlyState.bbf_division.ilike(f"{prefix}%")
                ).all()

        for rec in records:
            item_name = rec.item.item_name if rec.item else f"Item #{rec.item_id}"
            stock_records.append({
                "id": rec.id,
                "item_id": rec.item_id,
                "item_name": item_name,
                "scale": rec.scale or "-",
                "auth_res": rec.auth_res or 0,
                "stock_total": rec.stock_total or 0,
                "stock_ser": rec.stock_ser or 0,
                "stock_pws": rec.stock_pws or 0
            })

        total_stock = sum(r["stock_total"] for r in stock_records)
        total_stock_held = total_stock or 0

    return render_template(
        '/Div_Dashboard/div_dashboard.html',
        username=username,
        units=subordinate_units,
        unit_count=len(subordinate_units),
        catalog_items=catalog_items,
        total_items=len(catalog_items),
        critical_alerts_count=0,
        total_stock_held=total_stock_held,
        stock_records=stock_records
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
            defi = max(0, auth - held_qty)
            breakdown.append({
                "id": rec.id,
                "item_id": rec.item_id,
                "item_name": item_name,
                "authorized": auth,
                "held": held_qty,
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
                "held": track_rec.held or 0
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
                "held": issued_rec.held or 0
            }), 200

        return jsonify({"success": True, "exists": False, "auth": None, "held": 0}), 200

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
        issue_count = data.get("issue_count")
        item_auth = data.get("item_auth")

        if not unit_name or not item_id or issue_count is None:
            return jsonify({"success": False, "message": "Unit name, item ID, and issue count are required."}), 400

        try:
            val_qty = int(issue_count)
            item_id = int(item_id)
            if val_qty <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Issue count must be a positive integer."}), 400

        val_auth = None
        if item_auth is not None and item_auth != "":
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

        # Find EccMonthlyState record
        ecc_record = EccMonthlyState.query.filter(
            EccMonthlyState.item_id == item_id,
            db.func.lower(EccMonthlyState.bbf_division).in_([n.lower() for n in possible_names])
        ).first()

        if not ecc_record and user.username:
            prefix = user.username.split('_')[0]
            if prefix and prefix.isdigit():
                ecc_record = EccMonthlyState.query.filter(
                    EccMonthlyState.item_id == item_id,
                    EccMonthlyState.bbf_division.ilike(f"{prefix}%")
                ).first()

        if not ecc_record or (ecc_record.auth_res or 0) < val_qty:
            curr_res = ecc_record.auth_res if ecc_record else 0
            return jsonify({"success": False, "message": f"Insufficient reserve available. Current reserve: {curr_res}."}), 400

        # Deduct issued quantity from reserve (auth_res) in division EccMonthlyState
        ecc_record.auth_res = (ecc_record.auth_res or 0) - val_qty
        ecc_record.issd_total = (ecc_record.issd_total or 0) + val_qty
        if ecc_record.auth_auth is not None:
            ecc_record.auth_total = (ecc_record.auth_auth or 0) + ecc_record.auth_res

        # Add or update ScmeIssuedItems for the target unit
        issued_rec = ScmeIssuedItems.query.filter_by(unit_name=unit_name, item_id=item_id).first()
        if issued_rec:
            issued_rec.held = (issued_rec.held or 0) + val_qty
            if val_auth is not None:
                issued_rec.unit_authorized = val_auth
            else:
                issued_rec.unit_authorized = max((issued_rec.unit_authorized or 0), issued_rec.held)
            issued_rec.deficiency = max(0, (issued_rec.unit_authorized or 0) - issued_rec.held)
        else:
            initial_auth = val_auth if val_auth is not None else val_qty
            issued_rec = ScmeIssuedItems(
                unit_name=unit_name,
                item_id=item_id,
                a_u="Nos",
                unit_authorized=initial_auth,
                scale="100%",
                held=val_qty,
                deficiency=max(0, initial_auth - val_qty)
            )
            db.session.add(issued_rec)

        # Update item in TrackUnitItems table
        now_dt = datetime.now(timezone.utc) if hasattr(timezone, 'utc') else datetime.utcnow()
        track_rec = TrackUnitItems.query.filter_by(unit_name=unit_name, item_id=item_id).first()
        if track_rec:
            track_rec.held = (track_rec.held or 0) + val_qty
            if val_auth is not None:
                track_rec.auth = val_auth
            else:
                track_rec.auth = max(track_rec.auth or 0, track_rec.held)
            track_rec.issued_at = now_dt
        else:
            initial_auth = val_auth if val_auth is not None else val_qty
            track_rec = TrackUnitItems(
                unit_name=unit_name,
                item_id=item_id,
                auth=initial_auth,
                held=val_qty,
                issued_at=now_dt
            )
            db.session.add(track_rec)

        db.session.commit()

        # Recalculate total stock held across division
        records = EccMonthlyState.query.filter(
            db.func.lower(EccMonthlyState.bbf_division).in_([n.lower() for n in possible_names])
        ).all()
        new_total_stock = sum(r.stock_total or 0 for r in records)

        item_obj = ScmeItems.query.get(item_id)
        item_name = item_obj.item_name if item_obj else f"Item #{item_id}"

        return jsonify({
            "success": True,
            "message": f"Successfully issued {val_qty} unit(s) of '{item_name}' to {unit_name}.",
            "item_id": item_id,
            "new_item_reserve": ecc_record.auth_res,
            "new_item_stock": ecc_record.stock_total,
            "new_total_stock": new_total_stock
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500



