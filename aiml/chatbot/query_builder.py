"""
Query Builder Module for CMS AI Assistant.
Safely translates intent parameters and natural language requests into structured SQLAlchemy queries.
Never executes raw SQL strings.
"""

from typing import Dict, Any, List, Optional
from extensions import db
from models.our_items import (
    ScmeItems, TrackUnitItems, ScmeIssuedItems, FodStock,
    ItemRequestTable, Transactions, Divs, Strength, ItemAuth, ArmyPersonnel, UnitTpsStock, OurItems
)
from models.login_users import LoginUser, User
from models.action_log import ActionLog
from sqlalchemy import func, desc, or_, and_


def query_products_catalog(category_filter: Optional[str] = None, item_filter: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve catalog items filtered by category (CAT-I, CAT-II) or item name."""
    try:
        query = db.session.query(ScmeItems)

        if category_filter:
            query = query.filter(ScmeItems.category.ilike(f"%{category_filter}%"))
        if item_filter:
            query = query.filter(ScmeItems.item_name.ilike(f"%{item_filter}%"))

        items = query.all()
        item_list = [{"id": item.id, "item_name": item.item_name, "category": item.category, "type": item.type} for item in items]

        return {
            "total_count": len(item_list),
            "category": category_filter or "All",
            "items": item_list[:20]
        }
    except Exception as e:
        print(f"Error querying products catalog: {e}")
        return {"total_count": 0, "items": [], "error": str(e)}


def query_product_availability(item_name: str) -> Dict[str, Any]:
    """Retrieve stock availability, SER, PWS, and reserve stock for a specific item/product."""
    try:
        # Search item in ScmeItems catalog
        scme_item = ScmeItems.query.filter(ScmeItems.item_name.ilike(f"%{item_name}%")).first()

        if not scme_item:
            # Fallback check in OurItems table
            our_item = OurItems.query.filter(OurItems.item_name.ilike(f"%{item_name}%")).first()
            if not our_item:
                return {"found": False, "item_name": item_name, "message": f"Item '{item_name}' not found in catalog."}
            item_id = our_item.id
            item_display = our_item.item_name
            cat_display = "N/A"
        else:
            item_id = scme_item.id
            item_display = scme_item.item_name
            cat_display = scme_item.category

        # Aggregate unit stock held, SER, PWS, and available_res
        unit_stock = db.session.query(
            func.sum(TrackUnitItems.held).label("held"),
            func.sum(TrackUnitItems.ser).label("ser"),
            func.sum(TrackUnitItems.pws).label("pws"),
            func.sum(TrackUnitItems.available_res).label("res")
        ).filter(TrackUnitItems.item_id == item_id).first()

        held_qty = int(unit_stock.held or 0) if unit_stock else 0
        ser_qty = int(unit_stock.ser or 0) if unit_stock else 0
        pws_qty = int(unit_stock.pws or 0) if unit_stock else 0
        res_qty = int(unit_stock.res or 0) if unit_stock else 0

        # Aggregate FOD depot stock
        fod_qty = db.session.query(func.sum(FodStock.quantity)).filter(FodStock.item_id == item_id).scalar() or 0

        total_available = held_qty + res_qty + int(fod_qty)

        return {
            "found": True,
            "item_name": item_display,
            "category": cat_display,
            "total_available": total_available,
            "held_in_units": held_qty,
            "ser": ser_qty,
            "pws": pws_qty,
            "reserve_stock": res_qty,
            "fod_depot_stock": int(fod_qty)
        }
    except Exception as e:
        print(f"Error querying product availability: {e}")
        return {"found": False, "item_name": item_name, "error": str(e)}


def query_unit_deficiencies(unit_filter: Optional[str] = None, top_n: int = 10) -> Dict[str, Any]:
    """Retrieve unit deficiencies (Auth - Held) ranked by highest deficiency."""
    try:
        results = []
        track_records = db.session.query(
            TrackUnitItems, ScmeItems
        ).join(
            ScmeItems, TrackUnitItems.item_id == ScmeItems.id
        )

        if unit_filter:
            track_records = track_records.filter(TrackUnitItems.unit_name.ilike(f"%{unit_filter}%"))

        for track, item in track_records.all():
            auth_qty = track.auth or 0
            held_qty = track.held or 0
            deficiency = max(0, auth_qty - held_qty)
            if deficiency > 0:
                results.append({
                    "unit_name": track.unit_name,
                    "item_name": item.item_name,
                    "category": item.category,
                    "auth": auth_qty,
                    "held": held_qty,
                    "deficiency": deficiency
                })

        # Fallback to ScmeIssuedItems if empty
        if not results:
            issued_records = db.session.query(
                ScmeIssuedItems, ScmeItems
            ).join(
                ScmeItems, ScmeIssuedItems.item_id == ScmeItems.id
            ).filter(ScmeIssuedItems.deficiency > 0)

            if unit_filter:
                issued_records = issued_records.filter(ScmeIssuedItems.unit_name.ilike(f"%{unit_filter}%"))

            for issued, item in issued_records.all():
                results.append({
                    "unit_name": issued.unit_name,
                    "item_name": item.item_name,
                    "category": item.category,
                    "auth": issued.unit_authorized or 0,
                    "held": issued.held or 0,
                    "deficiency": issued.deficiency or 0
                })

        results.sort(key=lambda x: x["deficiency"], reverse=True)

        return {
            "total_deficiencies_found": len(results),
            "top_deficiencies": results[:top_n]
        }
    except Exception as e:
        print(f"Error querying unit deficiencies: {e}")
        return {"total_deficiencies_found": 0, "top_deficiencies": [], "error": str(e)}


def query_category_comparison() -> Dict[str, Any]:
    """Compare CAT-I vs CAT-II clothing stock, total catalog items, and issued counts."""
    try:
        cat_stats = {}
        for cat in ["CAT-I", "CAT-II"]:
            item_count = ScmeItems.query.filter(ScmeItems.category == cat).count()

            held_stock = db.session.query(
                func.sum(TrackUnitItems.held)
            ).join(
                ScmeItems, TrackUnitItems.item_id == ScmeItems.id
            ).filter(ScmeItems.category == cat).scalar() or 0

            issued_stock = db.session.query(
                func.sum(Transactions.ser + Transactions.pws)
            ).join(
                ScmeItems, Transactions.item_id == ScmeItems.id
            ).filter(ScmeItems.category == cat).scalar() or 0

            cat_stats[cat] = {
                "catalog_items": item_count,
                "held_stock": int(held_stock),
                "issued_stock": int(issued_stock)
            }

        return {
            "comparison": cat_stats,
            "categories": ["CAT-I", "CAT-II"]
        }
    except Exception as e:
        print(f"Error querying category comparison: {e}")
        return {"comparison": {}, "error": str(e)}


def query_issuance_and_issues(item_filter: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve issued items and transaction statistics."""
    try:
        tx_query = db.session.query(
            Transactions, ScmeItems
        ).join(
            ScmeItems, Transactions.item_id == ScmeItems.id
        )

        if item_filter:
            tx_query = tx_query.filter(ScmeItems.item_name.ilike(f"%{item_filter}%"))

        tx_list = tx_query.all()

        top_issued = db.session.query(
            ScmeItems.item_name,
            func.sum(Transactions.ser + Transactions.pws).label("qty")
        ).join(
            Transactions, Transactions.item_id == ScmeItems.id
        )

        if item_filter:
            top_issued = top_issued.filter(ScmeItems.item_name.ilike(f"%{item_filter}%"))

        top_issued_list = top_issued.group_by(
            ScmeItems.item_name
        ).order_by(desc("qty")).limit(5).all()

        return {
            "total_transactions": len(tx_list),
            "top_issued_items": [{"item_name": item, "issued_qty": int(qty or 0)} for item, qty in top_issued_list]
        }
    except Exception as e:
        print(f"Error querying issuance: {e}")
        return {"total_transactions": 0, "top_issued_items": [], "error": str(e)}


def query_inventory_summary() -> Dict[str, Any]:
    """Calculate aggregate inventory metrics across all units and catalog items."""
    try:
        total_items = ScmeItems.query.count()

        totals = db.session.query(
            func.sum(TrackUnitItems.held).label("held"),
            func.sum(TrackUnitItems.ser).label("ser"),
            func.sum(TrackUnitItems.pws).label("pws"),
            func.sum(TrackUnitItems.available_res).label("res")
        ).first()

        fod_total = db.session.query(func.sum(FodStock.quantity)).scalar() or 0

        return {
            "total_items_catalog": total_items,
            "total_held_stock": int(totals.held or 0) if totals else 0,
            "serviceable_ser": int(totals.ser or 0) if totals else 0,
            "partially_working_pws": int(totals.pws or 0) if totals else 0,
            "reserve_stock": int(totals.res or 0) if totals else 0,
            "fod_depot_stock": int(fod_total)
        }
    except Exception as e:
        print(f"Error querying inventory summary: {e}")
        return {"error": str(e)}


def query_unit_and_dou_info(unit_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve unit & DOU organization hierarchy and posted strength."""
    try:
        query = Divs.query
        if unit_name:
            query = query.filter(Divs.name.ilike(f"%{unit_name}%"))

        divs = query.all()
        unit_list = [{"name": d.name, "auth_strength": d.authorized_strength or 0, "posted_strength": d.posted_strength or 0} for d in divs]

        return {
            "units_count": len(unit_list),
            "units": unit_list[:10]
        }
    except Exception as e:
        print(f"Error querying unit info: {e}")
        return {"units_count": 0, "units": [], "error": str(e)}


def query_users_info() -> Dict[str, Any]:
    """Retrieve user statistics and role distributions from LoginUser and User models."""
    try:
        login_users = LoginUser.query.all()
        roles_count = {}
        users_list = []

        for u in login_users:
            r = u.role or "Unknown"
            roles_count[r] = roles_count.get(r, 0) + 1
            users_list.append({"username": u.username, "role": r})

        # Also check User table if present
        extra_users = User.query.all()
        for u in extra_users:
            r = u.role or "Unknown"
            if not any(x["username"] == u.username for x in users_list):
                roles_count[r] = roles_count.get(r, 0) + 1
                users_list.append({"username": u.username, "role": r})

        return {
            "total_users": len(users_list),
            "roles_breakdown": roles_count,
            "sample_users": users_list[:10]
        }
    except Exception as e:
        print(f"Error querying users info: {e}")
        return {"total_users": 0, "roles_breakdown": {}, "error": str(e)}


def query_authorization_details(unit_filter: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve item authorization limits and scales of issue across units."""
    try:
        query = db.session.query(
            ItemAuth, ScmeItems
        ).join(
            ScmeItems, ItemAuth.item_id == ScmeItems.id
        )

        if unit_filter:
            query = query.filter(ItemAuth.unit_name.ilike(f"%{unit_filter}%"))

        auth_records = query.all()
        results = [
            {
                "unit_name": auth.unit_name,
                "item_name": item.item_name,
                "category": item.category,
                "auth": auth.auth
            }
            for auth, item in auth_records
        ]

        if not results:
            track_records = db.session.query(
                TrackUnitItems, ScmeItems
            ).join(
                ScmeItems, TrackUnitItems.item_id == ScmeItems.id
            )
            if unit_filter:
                track_records = track_records.filter(TrackUnitItems.unit_name.ilike(f"%{unit_filter}%"))
            for track, item in track_records.all():
                if track.auth and track.auth > 0:
                    results.append({
                        "unit_name": track.unit_name,
                        "item_name": item.item_name,
                        "category": item.category,
                        "auth": track.auth,
                        "scale": track.scale
                    })

        return {
            "total_records": len(results),
            "authorizations": results[:10]
        }
    except Exception as e:
        print(f"Error querying authorization details: {e}")
        return {"total_records": 0, "authorizations": [], "error": str(e)}


def query_reserve_stock() -> Dict[str, Any]:
    """Retrieve total reserve stock held in units and FOD depots."""
    try:
        unit_res = db.session.query(func.sum(TrackUnitItems.available_res)).scalar() or 0
        fod_res = db.session.query(func.sum(FodStock.quantity)).filter(FodStock.type == "RES").scalar() or 0
        total_fod = db.session.query(func.sum(FodStock.quantity)).scalar() or 0

        return {
            "reserve_in_units": int(unit_res),
            "reserve_in_fod": int(fod_res),
            "fod_depot_stock": int(total_fod),
            "grand_total_reserve": int(unit_res) + int(fod_res)
        }
    except Exception as e:
        print(f"Error querying reserve stock: {e}")
        return {"error": str(e)}


def query_unit_comparison() -> Dict[str, Any]:
    """Compare stock holdings, posted strength, and deficiencies across units."""
    try:
        divs = Divs.query.all()
        comparison = []

        for d in divs:
            unit_name = d.name
            held = db.session.query(func.sum(TrackUnitItems.held)).filter(TrackUnitItems.unit_name == unit_name).scalar() or 0
            auth = db.session.query(func.sum(TrackUnitItems.auth)).filter(TrackUnitItems.unit_name == unit_name).scalar() or 0
            deficiency = max(0, int(auth) - int(held))

            comparison.append({
                "unit_name": unit_name,
                "posted_strength": d.posted_strength or 0,
                "authorized_strength": d.authorized_strength or 0,
                "held_stock": int(held),
                "auth_stock": int(auth),
                "deficiency": deficiency
            })

        return {
            "units_compared": len(comparison),
            "comparison": comparison[:10]
        }
    except Exception as e:
        print(f"Error querying unit comparison: {e}")
        return {"units_compared": 0, "comparison": [], "error": str(e)}


def query_inventory_report() -> Dict[str, Any]:
    """Compile aggregated inventory report data across all modules."""
    try:
        summary = query_inventory_summary()
        cat_comp = query_category_comparison()
        defs = query_unit_deficiencies(top_n=5)
        res = query_reserve_stock()

        return {
            "catalog_items_count": summary.get("total_items_catalog", 0),
            "total_held_stock": summary.get("total_held_stock", 0),
            "deficiencies_count": defs.get("total_deficiencies_found", 0),
            "top_deficiencies": defs.get("top_deficiencies", []),
            "categories": cat_comp.get("comparison", {}),
            "reserve": res
        }
    except Exception as e:
        print(f"Error compiling inventory report: {e}")
        return {"error": str(e)}
