from extensions import db

class ActionLog(db.Model):
    __tablename__ = "action_logs"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )
    user_id = db.Column(
        db.Integer,
        nullable=True
    )
    username = db.Column(
        db.String(255),
        nullable=False
    )
    role = db.Column(
        db.String(50),
        nullable=False
    )
    action_type = db.Column(
        db.String(50),
        nullable=False
    )
    module = db.Column(
        db.String(50),
        nullable=False
    )
    details = db.Column(
        db.Text,
        nullable=False
    )
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    def __init__(self, user_id, username, role, action_type, module, details):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.action_type = action_type
        self.module = module
        self.details = details
