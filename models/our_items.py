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


class ScmeItems(db.Model):
    __tablename__ = "scme_items"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )
    item_name = db.Column(
        db.String(255),
        nullable=False
    )
    category = db.Column(
        db.String(50),
        nullable=False
    )

    def __init__(self, item_name, category="CAT-II"):
        self.item_name = item_name
        self.category = category


class Units(db.Model):
    __tablename__ = "units"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )
    name = db.Column(
        db.String(255),
        nullable=False
    )

    def __init__(self, name):
        self.name = name


class ScmeIssuedItems(db.Model):
    __tablename__ = "scme_issued_items"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )
    unit_name = db.Column(
        db.String(255),
        nullable=False
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("scme_items.id"),
        nullable=False
    )
    scale = db.Column(
        db.Integer,
        nullable=False
    )
    a_u = db.Column(
        db.Integer,
        nullable=False
    )
    held = db.Column(
        db.Integer,
        nullable=False
    )
    deficiency = db.Column(
        db.Integer,
        nullable=False
    )
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    item = db.relationship("ScmeItems", backref="issued_items")

    def __init__(self, unit_name, item_id, scale, a_u, held, deficiency):
        self.unit_name = unit_name
        self.item_id = item_id
        self.scale = scale
        self.a_u = a_u
        self.held = held
        self.deficiency = deficiency




