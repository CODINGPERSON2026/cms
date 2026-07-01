from imports import *
from extensions import csrf


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)
    migrate = Migrate(app, db)
    with app.app_context():
        db.create_all()

    app.register_blueprint(login_bp)
    app.register_blueprint(unit_bp)
    app.register_blueprint(div_bp)
    app.register_blueprint(ord_bp)
    app.register_blueprint(bde_bp)
    app.register_blueprint(mgt_bp)

    
        

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        print(str(e))
        return jsonify({"success": False, "message": e.description}), 400

    @app.route("/")
    def homepage():
        if "user_id" not in session:
            return render_template('/Login_page/login_page.html')
        route = session['role']
        return redirect(f'/{route}')
    
    @app.route("/incoming-requests")
    def incoming_requests():
        return render_template("/incoming_requests/incoming_requests.html")
    
    @app.context_processor
    def inject_user_data():
        return {
            "current_role": session.get("role"),
            "current_user_id": session.get("user_id"),
            "current_username": session.get("username")
        }
    
    
    
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(port=9090, debug=True)
