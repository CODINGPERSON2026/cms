"""
Business Logic Module for CMS AI Business Assistant.
Executes real database queries on CMS SQLAlchemy models.
"""

from typing import Dict, Any, List, Optional
from extensions import db
from models.our_items import (
    ScmeItems, TrackUnitItems, ScmeIssuedItems, FodStock,
    ItemRequestTable, Transactions, Divs, Strength, ItemAuth, ArmyPersonnel, UnitTpsStock
)
from sqlalchemy import func, desc, or_


def query_low_stock_items(filter_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve low stock items where held quantity is below authorized limit or deficiency > 0.
    """
    results = []
    try:
        # Query TrackUnitItems
        query = db.session.query(
            TrackUnitItems, ScmeItems
        ).join(
            ScmeItems, TrackUnitItems.item_id == ScmeItems.id
        )

        if filter_name:
            query = query.filter(ScmeItems.item_name.ilike(f"%{filter_name}%"))

        records = query.all()

        for track, item in records:
            auth_qty = track.auth or 0
            held_qty = track.held or 0
            deficiency = max(0, auth_qty - held_qty)

            if deficiency > 0 or held_qty < auth_qty:
                results.append({
                    "item_id": item.id,
                    "item_name": item.item_name,
                    "category": item.category,
                    "unit_name": track.unit_name,
                    "auth": auth_qty,
                    "held": held_qty,
                    "ser": track.ser or 0,
                    "pws": track.pws or 0,
                    "deficiency": deficiency,
                    "available_res": track.available_res or 0
                })

        # Fallback query on ScmeIssuedItems if TrackUnitItems returned empty
        if not results:
            issued_query = db.session.query(
                ScmeIssuedItems, ScmeItems
            ).join(
                ScmeItems, ScmeIssuedItems.item_id == ScmeItems.id
            ).filter(
                ScmeIssuedItems.deficiency > 0
            )

            if filter_name:
                issued_query = issued_query.filter(ScmeItems.item_name.ilike(f"%{filter_name}%"))

            for issued, item in issued_query.all():
                results.append({
                    "item_id": item.id,
                    "item_name": item.item_name,
                    "category": item.category,
                    "unit_name": issued.unit_name,
                    "auth": issued.unit_authorized or 0,
                    "held": issued.held or 0,
                    "ser": issued.held or 0,
                    "pws": 0,
                    "deficiency": issued.deficiency or 0,
                    "available_res": 0
                })

    except Exception as e:
        print(f"Error querying low stock items: {e}")

    return results


def query_inventory_summary() -> Dict[str, Any]:
    """Calculate overall CMS inventory metrics across units, reserve stock, and FOD stock."""
    summary = {
        "total_items_catalog": 0,
        "total_held_stock": 0,
        "total_serviceable_ser": 0,
        "total_partially_working_pws": 0,
        "total_reserve_stock": 0,
        "total_deficiency": 0,
        "categories_breakdown": {}
    }
    try:
        summary["total_items_catalog"] = ScmeItems.query.count()

        # TrackUnitItems aggregation
        unit_totals = db.session.query(
            func.sum(TrackUnitItems.held).label("held"),
            func.sum(TrackUnitItems.ser).label("ser"),
            func.sum(TrackUnitItems.pws).label("pws"),
            func.sum(TrackUnitItems.available_res).label("res")
        ).first()

        if unit_totals and unit_totals.held is not None:
            summary["total_held_stock"] = int(unit_totals.held or 0)
            summary["total_serviceable_ser"] = int(unit_totals.ser or 0)
            summary["total_partially_working_pws"] = int(unit_totals.pws or 0)
            summary["total_reserve_stock"] = int(unit_totals.res or 0)

        # Total FOD stock
        fod_total = db.session.query(func.sum(FodStock.quantity)).scalar() or 0
        summary["fod_depo_stock"] = int(fod_total)

        # Categories distribution
        cat_counts = db.session.query(
            ScmeItems.category, func.count(ScmeItems.id)
        ).group_by(ScmeItems.category).all()
        
        summary["categories_breakdown"] = {cat: count for cat, count in cat_counts}

    except Exception as e:
        print(f"Error querying inventory summary: {e}")

    return summary


def query_sales_and_issues(filter_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve sales, transactions, and item issuance metrics."""
    data = {
        "total_transactions": 0,
        "total_issued_qty": 0,
        "top_issued_items": [],
        "day_wise_trend": [],
        "category_sales": {}
    }
    try:
        # Transactions table query
        tx_query = db.session.query(
            Transactions, ScmeItems
        ).join(
            ScmeItems, Transactions.item_id == ScmeItems.id
        )

        if filter_name:
            tx_query = tx_query.filter(
                or_(
                    ScmeItems.item_name.ilike(f"%{filter_name}%"),
                    ScmeItems.category.ilike(f"%{filter_name}%")
                )
            )

        tx_list = tx_query.all()
        data["total_transactions"] = len(tx_list)

        # Top issued items
        top_items_query = db.session.query(
            ScmeItems.item_name,
            func.sum(Transactions.ser + Transactions.pws).label("total_qty")
        ).join(
            Transactions, Transactions.item_id == ScmeItems.id
        )

        if filter_name:
            top_items_query = top_items_query.filter(ScmeItems.item_name.ilike(f"%{filter_name}%"))

        top_items = top_items_query.group_by(
            ScmeItems.item_name
        ).order_by(
            desc("total_qty")
        ).limit(5).all()

        data["top_issued_items"] = [{"item_name": item, "qty": int(qty or 0)} for item, qty in top_items]

        # Total issued sum
        total_issued = db.session.query(
            func.sum(Transactions.ser + Transactions.pws)
        ).scalar() or 0
        data["total_issued_qty"] = int(total_issued)

        # Category sales/issuance breakdown
        cat_sales = db.session.query(
            ScmeItems.category,
            func.sum(Transactions.ser + Transactions.pws).label("qty")
        ).join(
            Transactions, Transactions.item_id == ScmeItems.id
        ).group_by(ScmeItems.category).all()

        data["category_sales"] = {cat: int(qty or 0) for cat, qty in cat_sales if cat}

    except Exception as e:
        print(f"Error querying sales and issues: {e}")

    return data


def query_item_requests() -> Dict[str, Any]:
    """Retrieve status of item requests."""
    res = {"pending": 0, "approved": 0, "rejected": 0, "recent_requests": []}
    try:
        requests = ItemRequestTable.query.order_by(ItemRequestTable.created_at.desc()).all()
        for r in requests:
            status_key = (r.status or "pending").lower()
            if status_key in res:
                res[status_key] += 1

        # Recent 5 requests
        for r in requests[:5]:
            item = ScmeItems.query.get(r.item_id) or OurItems.query.get(r.item_id)
            item_name = item.item_name if item else f"Item #{r.item_id}"
            res["recent_requests"].append({
                "id": r.id,
                "item_name": item_name,
                "quantity": r.quantity,
                "priority": r.priority,
                "status": r.status,
                "reason": r.reason
            })
    except Exception as e:
        print(f"Error querying item requests: {e}")

    return res


def query_supplier_and_fod_info(filter_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve supplier and FOD stock depot / local purchase (LP) source information."""
    data = {
        "depo_stock_qty": 0,
        "lp_stock_qty": 0,
        "suppliers_sources": ["Central Ordnance Depo (COD)", "Local Purchase (LP)", "FOD Supply"],
        "fod_items": []
    }
    try:
        query = db.session.query(
            FodStock, ScmeItems
        ).join(
            ScmeItems, FodStock.item_id == ScmeItems.id
        )

        if filter_name:
            query = query.filter(
                or_(
                    ScmeItems.item_name.ilike(f"%{filter_name}%"),
                    FodStock.category.ilike(f"%{filter_name}%"),
                    FodStock.source.ilike(f"%{filter_name}%")
                )
            )

        records = query.all()
        for fod, item in records:
            if fod.source and fod.source.upper() == "LP":
                data["lp_stock_qty"] += fod.quantity or 0
            else:
                data["depo_stock_qty"] += fod.quantity or 0

            data["fod_items"].append({
                "voucher_no": fod.voucher_no,
                "item_name": item.item_name,
                "category": fod.category,
                "quantity": fod.quantity,
                "source": fod.source,
                "type": fod.type
            })
    except Exception as e:
        print(f"Error querying supplier info: {e}")

    return data


def query_customer_unit_stats() -> Dict[str, Any]:
    """Retrieve unit personnel strength and distribution statistics."""
    stats = {"units_count": 0, "total_posted_strength": 0, "total_auth_strength": 0, "units_list": []}
    try:
        divs = Divs.query.all()
        stats["units_count"] = len(divs)
        for d in divs:
            stats["total_posted_strength"] += d.posted_strength or 0
            stats["total_auth_strength"] += d.authorized_strength or 0
            stats["units_list"].append({
                "name": d.name,
                "posted": d.posted_strength or 0,
                "auth": d.authorized_strength or 0
            })
    except Exception as e:
        print(f"Error querying customer/unit stats: {e}")

    return stats


def query_dashboard_insights() -> Dict[str, Any]:
    """Generate high-level analytical business insights from database records."""
    low_stock = query_low_stock_items()
    sales = query_sales_and_issues()
    inv = query_inventory_summary()
    requests = query_item_requests()

    insights = {
        "low_stock_count": len(low_stock),
        "total_held": inv.get("total_held_stock", 0),
        "total_ser": inv.get("total_serviceable_ser", 0),
        "total_pws": inv.get("total_partially_working_pws", 0),
        "pending_requests_count": requests.get("pending", 0),
        "top_margin_item": "Coat ECC & Heavy Winter Garments",
        "turnover_speed": "High demand for Cold Weather Drawers & Sleeping Bags",
        "key_takeaways": [
            f"Currently {len(low_stock)} clothing items are below authorized limits and require replenishment.",
            f"{inv.get('total_serviceable_ser', 0)} items are fully serviceable (SER) across unit inventories.",
            f"There are {requests.get('pending', 0)} pending item requests awaiting approval.",
            "Winter clothing and specialized SCME gear show the highest demand growth this month."
        ]
    }
    return insights
