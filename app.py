from imports import *
from extensions import csrf
from blueprints.chatbot import chatbot_bp

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)
    migrate = Migrate(app, db)
    with app.app_context():
        db.create_all()
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'track_unit_items' in inspector.get_table_names():
                columns = [c['name'] for c in inspector.get_columns('track_unit_items')]
                new_cols = [
                    ('add_knd', 'INT DEFAULT 0 NOT NULL'),
                    ('add_tn_model', 'INT DEFAULT 0 NOT NULL'),
                    ('add_n_area_otg', 'INT DEFAULT 0 NOT NULL'),
                    ('add_idt_ict', 'INT DEFAULT 0 NOT NULL')
                ]
                for col, col_type in new_cols:
                    if col not in columns:
                        db.session.execute(text(f'ALTER TABLE track_unit_items ADD COLUMN {col} {col_type}'))
                db.session.commit()
        except Exception as e:
            print("Auto-migration notice:", e)

    app.register_blueprint(login_bp)
    app.register_blueprint(unit_bp)
    app.register_blueprint(div_bp)
    app.register_blueprint(ord_bp)
    app.register_blueprint(bde_bp)
    app.register_blueprint(mgt_bp)
    app.register_blueprint(scme_bp)
    app.register_blueprint(logs_bp)
    
    # chatbot blueprint
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')
    
        

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
