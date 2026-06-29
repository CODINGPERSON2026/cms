from extensions import db
from datetime import datetime

class OurItems(db.Model):
    __tablename__ = "our_items"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )
    item_name = db.Column(
        db.String(255),
        nullable=False
    )


class ItemRequestTable(db.Model):
    __tablename__ = "item_request_table"

    id = db.Column(db.Integer, primary_key=True)

    item_id = db.Column(
        db.Integer,
        db.ForeignKey("our_items.id"),
        nullable=False
    )

    requested_by = db.Column(
        db.Integer,
        nullable=False
    )

    admin_id = db.Column(
        db.Integer,
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    

    reason = db.Column(
        db.String(100)
    )

    priority = db.Column(
        db.String(20),
        default="normal"
    )

    remarks = db.Column(
        db.String(255)
    )

    status = db.Column(
        db.String(20),
        default="pending"
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

