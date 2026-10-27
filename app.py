# Flask Application Setup - Trigger Reload
from imports import *
from extensions import csrf
# from blueprints.chatbot import chatbot_bp  # Disabled: no Ollama model required
from blueprints.notifications import notifications_bp

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
            if 'ecc_monthly_state' in inspector.get_table_names():
                db.session.execute(text('DROP TABLE IF EXISTS ecc_monthly_state'))
                db.session.commit()
        except Exception as e:
            print("Auto-drop ecc_monthly_state notice:", e)

        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'track_unit_items' in inspector.get_table_names():
                columns = [c['name'] for c in inspector.get_columns('track_unit_items')]
                new_cols = [
                    ('scale', 'VARCHAR(255) NULL AFTER item_id'),
                    ('add_knd', 'INT DEFAULT 0 NOT NULL'),
                    ('add_tn_model', 'INT DEFAULT 0 NOT NULL'),
                    ('add_n_area_otg', 'INT DEFAULT 0 NOT NULL'),
                    ('add_idt_ict', 'INT DEFAULT 0 NOT NULL'),
                    ('available_res', 'INT DEFAULT 0 NOT NULL'),
                    ('available_ser', 'INT DEFAULT 0 NOT NULL'),
                    ('available_pws', 'INT DEFAULT 0 NOT NULL'),
                    ('condemned_ser', 'INT DEFAULT 0 NOT NULL'),
                    ('condemned_pws', 'INT DEFAULT 0 NOT NULL'),
                    ('condemnation_date', 'DATETIME NULL'),
                    ('held_pws', 'INT NULL DEFAULT NULL')
                ]
                for col, col_type in new_cols:
                    if col not in columns:
                        db.session.execute(text(f'ALTER TABLE track_unit_items ADD COLUMN {col} {col_type}'))
                db.session.commit()
        except Exception as e:
            print("Auto-migration notice:", e)

        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'item_auth' in inspector.get_table_names():
                columns = [c['name'] for c in inspector.get_columns('item_auth')]
                if 'whole_auth' not in columns:
                    db.session.execute(text('ALTER TABLE item_auth ADD COLUMN whole_auth INT NULL'))
                if 'whole_res' not in columns:
                    db.session.execute(text('ALTER TABLE item_auth ADD COLUMN whole_res INT NULL'))
                if 'scale' not in columns:
                    db.session.execute(text('ALTER TABLE item_auth ADD COLUMN scale VARCHAR(255) NULL'))
                try:
                    db.session.execute(text('ALTER TABLE item_auth MODIFY unit_name VARCHAR(255) NULL'))
                    db.session.execute(text('ALTER TABLE item_auth MODIFY auth INT NULL'))
                except Exception:
                    pass
                db.session.commit()
        except Exception as e:
            print("Auto-migration item_auth notice:", e)

        # Auto-create condemnation_requests table (handled by db.create_all above,
        # but guard here in case older DBs need explicit column additions)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'condemnation_requests' in inspector.get_table_names():
                columns = [c['name'] for c in inspector.get_columns('condemnation_requests')]
                new_cols = [
                    ('rejection_reason', 'VARCHAR(500) NULL'),
                    ('reviewed_by',      'VARCHAR(255) NULL'),
                    ('reviewed_at',      'DATETIME NULL'),
                    ('requested_by_user_id', 'INT NULL'),
                    ('condemnation_no',  'VARCHAR(100) NULL'),
                    ('pdf_filename',     'VARCHAR(255) NULL'),
                    ('pdf_original_name','VARCHAR(255) NULL'),
                    ('salvage_rv',       'TINYINT(1) NOT NULL DEFAULT 0'),
                    ('destruction_certificate', 'TINYINT(1) NOT NULL DEFAULT 0'),
                ]
                for col, col_type in new_cols:
                    if col not in columns:
                        db.session.execute(text(
                            f'ALTER TABLE condemnation_requests ADD COLUMN {col} {col_type}'
                        ))
                db.session.commit()
        except Exception as e:
            print("Auto-migration condemnation_requests notice:", e)

        import os
        from flask import send_from_directory, abort
        upload_folder = app.config.get("CONDEMNATION_UPLOAD_FOLDER", r"C:\Condemnation_pdf")
        os.makedirs(upload_folder, exist_ok=True)

    app.register_blueprint(login_bp)
    app.register_blueprint(unit_bp)
    app.register_blueprint(div_bp)
    app.register_blueprint(ord_bp)
    app.register_blueprint(bde_bp)
    app.register_blueprint(mgt_bp)
    app.register_blueprint(scme_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(notifications_bp)
    
    # chatbot blueprint (disabled: no Ollama 3.2 model required)
    # app.register_blueprint(chatbot_bp, url_prefix='/chatbot')

    @app.route('/condemnation/pdf/<path:filename>')
    def serve_condemnation_pdf(filename):
        if "user_id" not in session:
            abort(401)
        import os
        from flask import send_from_directory
        folder = app.config.get("CONDEMNATION_UPLOAD_FOLDER", r"C:\Condemnation_pdf")
        return send_from_directory(folder, filename, mimetype='application/pdf')
    
        

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
    app.run(port=5000,debug = True)
# ECC Monthly Summary: Both Previous Month and Issued During Month now use real transactions table queries



























