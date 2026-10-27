from extensions import db
from datetime import datetime, timezone

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    target_user = db.Column(db.String(100), nullable=True)
    target_role = db.Column(db.String(50), nullable=True)
    sender_name = db.Column(db.String(100), nullable=False, default="System")
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    item_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def __init__(self, title, message, sender_name="System", target_user=None, target_role=None, item_id=None, is_read=False, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.message = message
        self.sender_name = sender_name
        self.target_user = target_user
        self.target_role = target_role
        self.item_id = item_id
        self.is_read = is_read
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            "id": self.id,
            "target_user": self.target_user,
            "target_role": self.target_role,
            "sender_name": self.sender_name,
            "title": self.title,
            "message": self.message,
            "item_id": self.item_id,
            "is_read": self.is_read,
            "created_at": self.created_at.strftime('%d %b %Y, %H:%M') if self.created_at else ''
        }
