from imports import *
from models import LoginUser
import re

mgt_bp = Blueprint("mgt", __name__, url_prefix="/mgt")


@mgt_bp.route('/')
def management_page():
        return render_template('/management/management.html')


@mgt_bp.route("/tree")
def tree_page():
     return render_template("tree.html")




@mgt_bp.route("/api/tree", methods=["GET"])
def get_tree():

        try:

            if "user_id" not in session:
                return jsonify({
                    "success": False,
                    "message": "Unauthorized"
                }), 401

            current_user = LoginUser.query.get(session["user_id"])

            if not current_user:
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404

            current_org = current_user.org

            if not current_org:
                return jsonify({
                    "success": False,
                    "message": "Organisation not found"
                }), 404

            # Find top-most organisation
            root_org = current_org

            while root_org.parent:
                root_org = root_org.parent

            # Recursive tree builder
            def build_tree(org):

                return {
                    "id": org.id,
                    "name": org.name,
                    "type": org.type,
                    "is_current": org.id == current_org.id,
                    "children": [
                        build_tree(child)
                        for child in org.children
                    ]
                }

            tree = build_tree(root_org)

            return jsonify(tree), 200

        except Exception as e:

            db.session.rollback()

            print(e)

            return jsonify({
                "success": False,
                "message": str(e)
            }), 500