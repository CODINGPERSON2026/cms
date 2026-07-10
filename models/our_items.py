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
    __tablename__ = "ecc_scme_items"

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
        db.ForeignKey("ecc_scme_items.id"),
        nullable=False
    )
    a_u = db.Column(                  # CHANGED: Integer -> String ('Nos' / 'Prs')
        db.String(10),
        nullable=False
    )
    unit_authorized = db.Column(      # NEW: max count allowed for the unit
        db.Integer,
        nullable=False
    )
    scale = db.Column(                # CHANGED: Integer -> String ('50%')
        db.String(10),
        nullable=False
    )
    held = db.Column(
        db.Integer,
        nullable=False
    )
    deficiency = db.Column(           # now = unit_authorized - held
        db.Integer,
        nullable=False
    )
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    item = db.relationship("ScmeItems", backref="issued_items")

    def __init__(self,unit_name, item_id, a_u,
                 unit_authorized, scale, held, deficiency):
        
        self.unit_name = unit_name
        self.item_id = item_id
        self.a_u = a_u
        self.unit_authorized = unit_authorized
        self.scale = scale
        self.held = held
        self.deficiency = deficiency




