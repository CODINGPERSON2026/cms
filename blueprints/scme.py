from imports import *
from extensions import db
from models import LoginUser
from models.our_items import OurItems, ItemRequestTable, ScmeItems, Units, ScmeIssuedItems
from models.org_ladder import OrgLadder
from validation import has_special_characters

scme_bp = Blueprint("scme", __name__, url_prefix='/scme')


@scme_bp.route('/')
def scme_home():
    if "user_id" not in session or session.get("role") != "scme":
        return redirect("/auth/login")
        
    from sqlalchemy import func
    
    # 1. Total Catalog Items
    total_items = ScmeItems.query.count()
    
    # 2. Active Units Tracked
    active_units = db.session.query(ScmeIssuedItems.unit_name).distinct().count()
    
    # 3. Global Deficiency (Deafy)
    global_deficiency = db.session.query(func.sum(ScmeIssuedItems.deficiency)).scalar() or 0
    
    # 4. Fulfillment Rate calculation
    total_au = db.session.query(func.sum(ScmeIssuedItems.a_u)).scalar() or 0
    total_held = db.session.query(func.sum(ScmeIssuedItems.held)).scalar() or 0
    fulfillment_rate = round((total_held / total_au * 100), 1) if total_au > 0 else 0
    
    # 5. Critical Alerts Count (held < 50% of a_u)
    critical_alerts = ScmeIssuedItems.query.filter(ScmeIssuedItems.held < (ScmeIssuedItems.a_u / 2)).count()
    
    # Chart 1: Deficiency by Unit (Scale, A/U, Held by unit)
    unit_stats = db.session.query(
        ScmeIssuedItems.unit_name,
        func.sum(ScmeIssuedItems.scale).label('scale'),
        func.sum(ScmeIssuedItems.a_u).label('a_u'),
        func.sum(ScmeIssuedItems.held).label('held')
    ).group_by(ScmeIssuedItems.unit_name).all()
    
    unit_chart_data = [
        {
            "unit_name": row[0],
            "scale": int(row[1] or 0),
            "a_u": int(row[2] or 0),
            "held": int(row[3] or 0)
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
    
    issued_items = ScmeIssuedItems.query.order_by(ScmeIssuedItems.created_at.desc()).all()
    
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
        issued_items=issued_items
    )


@scme_bp.route('/enter-items')
def enter_items():
    if "user_id" not in session or session.get("role") != "scme":
        return redirect("/auth/login")
    
    # Get distinct categories from scme_items
    categories = [r[0] for r in db.session.query(ScmeItems.category).distinct().all()]
    
    # Get all units
    units = Units.query.order_by(Units.name).all()
    
    # Get all items to filter in frontend JS
    items = ScmeItems.query.order_by(ScmeItems.item_name).all()
    
    # Get already issued items history
    issued_items = ScmeIssuedItems.query.order_by(ScmeIssuedItems.created_at.desc()).all()
    
    return render_template(
        '/scme_dashboard/enter_scme_items.html',
        categories=categories,
        units=units,
        items=items,
        issued_items=issued_items
    )


@scme_bp.route('/api/add-item', methods=['POST'])
def api_add_item():
    if "user_id" not in session or session.get("role") != "scme":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    try:
        data = request.get_json()
        item_name = data.get("item_name", "").strip()
        category = data.get("category", "").strip()
        
        if not item_name:
            return jsonify({"success": False, "message": "Item name is required"}), 400
            
        if not category:
            category = "CAT-II"
            
        if has_special_characters(item_name):
            return jsonify({"success": False, "message": "Item name contains invalid special characters."}), 400
            
        if has_special_characters(category):
            return jsonify({"success": False, "message": "Category contains invalid special characters."}), 400
            
        # Check if item already exists
        existing = ScmeItems.query.filter(ScmeItems.item_name == item_name).first()
        if existing:
            return jsonify({"success": False, "message": "An item with this name already exists."}), 400
            
        new_item = ScmeItems(item_name=item_name, category=category)
        db.session.add(new_item)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Item added successfully.",
            "item": {
                "id": new_item.id, 
                "item_name": new_item.item_name,
                "category": new_item.category
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
        unit_name = data.get("unit_name", "").strip()
        item_id = data.get("item_id")
        scale = data.get("scale")
        a_u = data.get("a_u")
        held = data.get("held")
        
        if not unit_name or not item_id:
            return jsonify({"success": False, "message": "Unit Name and Item are required."}), 400
            
        try:
            scale_val = int(scale)
            a_u_val = int(a_u)
            held_val = int(held)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Scale, A/U and Held must be numbers."}), 400
            
        if scale_val < 0 or a_u_val < 0 or held_val < 0:
            return jsonify({"success": False, "message": "Values cannot be negative."}), 400
            
        deficiency_val = a_u_val - held_val
        
        # Verify Unit and Item exist
        unit_exists = Units.query.filter_by(name=unit_name).first()
        item_exists = ScmeItems.query.get(item_id)
        
        if not unit_exists:
            return jsonify({"success": False, "message": "Selected Unit does not exist."}), 400
        if not item_exists:
            return jsonify({"success": False, "message": "Selected Item does not exist."}), 400
            
        new_issued = ScmeIssuedItems(
            unit_name=unit_name,
            item_id=item_id,
            scale=scale_val,
            a_u=a_u_val,
            held=held_val,
            deficiency=deficiency_val
        )
        db.session.add(new_issued)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "SCME issued item recorded successfully.",
            "issued_item": {
                "id": new_issued.id,
                "unit_name": new_issued.unit_name,
                "item_name": item_exists.item_name,
                "category": item_exists.category,
                "scale": new_issued.scale,
                "a_u": new_issued.a_u,
                "held": new_issued.held,
                "deficiency": new_issued.deficiency,
                "created_at": new_issued.created_at.strftime('%d %b %Y, %H:%M') if new_issued.created_at else ""
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


