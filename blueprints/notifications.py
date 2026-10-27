from flask import Blueprint, jsonify, request, session
from extensions import db, csrf
from models.notifications import Notification
from models.login_users import LoginUser
from sqlalchemy import func, or_, and_

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")

def get_current_user_info():
    user_id = session.get("user_id")
    if not user_id:
        return None, None, None, set()

    username = (session.get("username") or "").strip()
    role = (session.get("role") or "").strip()
    user_div = (session.get("user_div") or "").strip()

    names = set()
    if username:
        u = username.lower()
        names.add(u)
        names.add(u.replace('_', ' '))
        names.add(u.replace(' ', '_'))
    if user_div:
        d = user_div.lower()
        names.add(d)
        names.add(d.replace('_', ' '))
        names.add(d.replace(' ', '_'))

    user = LoginUser.query.get(user_id)
    if user:
        if user.username:
            u = user.username.strip().lower()
            names.add(u)
            names.add(u.replace('_', ' '))
            names.add(u.replace(' ', '_'))
        if user.org and user.org.name:
            o = user.org.name.strip().lower()
            names.add(o)
            names.add(o.replace('_', ' '))
            names.add(o.replace(' ', '_'))

    return user_id, username, role, names


def build_notification_filter(user_id, username, role, names):
    # Super Admin oversees the entire CMS and receives all operational notifications
    if role == "super_admin":
        return None

    conditions = []
    # 1. Targeted notifications to this user / division / unit
    if names:
        conditions.append(func.lower(Notification.target_user).in_(list(names)))

    # 2. Broadcast notifications to user's role (where target_user is NULL or empty)
    broadcast_condition = and_(
        or_(Notification.target_user.is_(None), func.trim(Notification.target_user) == ""),
        or_(func.lower(Notification.target_role) == role.lower(), Notification.target_role.is_(None), func.trim(Notification.target_role) == "")
    )
    conditions.append(broadcast_condition)

    # 3. For SCME (e.g. 2_FOD), also include notifications they originated
    if role == "scme" and names:
        conditions.append(func.lower(Notification.sender_name).in_(list(names)))

    return or_(*conditions)


@notifications_bp.route("/api/list", methods=["GET"])
def get_notifications():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    user_id, username, role, names = get_current_user_info()
    filter_cond = build_notification_filter(user_id, username, role, names)

    query = Notification.query
    if filter_cond is not None:
        query = query.filter(filter_cond)

    notifications = query.order_by(
        Notification.created_at.desc(),
        Notification.id.desc()
    ).limit(50).all()

    unread_count = sum(1 for n in notifications if not n.is_read)

    import re
    formatted_list = []
    for n in notifications:
        d = n.to_dict()
        if d["title"] == "New ECC Stock Allocated to Division":
            d["title"] = "New ECC Stock Allocated to You"
        if "to your division (" in d["message"]:
            d["message"] = re.sub(r"to your division \([^)]+\)\.?", "to you.", d["message"])
            if d["message"].startswith("SCME issued"):
                sender = d.get("sender_name") or "2_FOD"
                d["message"] = d["message"].replace("SCME issued", f"{sender} issued")
        formatted_list.append(d)

    return jsonify({
        "success": True,
        "notifications": formatted_list,
        "unread_count": unread_count
    }), 200


@notifications_bp.route("/api/unread-count", methods=["GET"])
def get_unread_count():
    if "user_id" not in session:
        return jsonify({"success": False, "unread_count": 0}), 200

    user_id, username, role, names = get_current_user_info()
    filter_cond = build_notification_filter(user_id, username, role, names)

    query = Notification.query.filter(Notification.is_read == False)
    if filter_cond is not None:
        query = query.filter(filter_cond)

    unread_count = query.count()

    return jsonify({
        "success": True,
        "unread_count": unread_count
    }), 200


@notifications_bp.route("/api/mark-read/<int:notif_id>", methods=["POST"])
@csrf.exempt
def mark_notification_read(notif_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    notif = Notification.query.get(notif_id)
    if not notif:
        return jsonify({"success": False, "message": "Notification not found"}), 404

    notif.is_read = True
    db.session.commit()
    return jsonify({"success": True, "message": "Marked as read"}), 200


@notifications_bp.route("/api/mark-all-read", methods=["POST"])
@csrf.exempt
def mark_all_notifications_read():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    user_id, username, role, names = get_current_user_info()
    filter_cond = build_notification_filter(user_id, username, role, names)

    query = Notification.query.filter(Notification.is_read == False)
    if filter_cond is not None:
        query = query.filter(filter_cond)

    unread_notifs = query.all()

    for n in unread_notifs:
        n.is_read = True

    db.session.commit()
    return jsonify({"success": True, "message": "All notifications marked as read"}), 200

