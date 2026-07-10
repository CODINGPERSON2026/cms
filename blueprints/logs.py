from imports import *
from models import ActionLog

logs_bp = Blueprint("logs", __name__, url_prefix="/logs")

@logs_bp.route("/", methods=["GET"])
def view_logs():
    if "user_id" not in session:
        return redirect("/auth/login")
    
    # Retrieve all logs, ordered by created_at desc
    logs = ActionLog.query.order_by(ActionLog.created_at.desc()).all()
    
    return render_template("/logs/logs.html", logs=logs)
