
from imports import *
from models import LoginUser
import re

login_bp = Blueprint("login", __name__, url_prefix="/auth")



@login_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        data = request.get_json()

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        # Empty check
        if not username or not password:
            return jsonify({
                "success": False,
                "message": "Username and password are required"
            })

        # Username validation
        if not re.fullmatch(r"[A-Za-z0-9_]+", username):
            return jsonify({
                "success": False,
                "message": "Username can only contain letters, numbers and underscore"
            })

        user = LoginUser.query.filter_by(username=username).first()

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            })

        if user.password != password:
            return jsonify({
                "success": False,
                "message": "Incorrect password"
            })
          # ✅ SESSION STARTS HERE
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role
        return jsonify({
            "success": True,
            "redirect": f"/{user.role}"
        })

    return render_template("Login_Page/login_page.html")




@login_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/auth/login")