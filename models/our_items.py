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
    type = db.Column(
        db.String(50),
        nullable=True
    )

    def __init__(self, item_name, category="CAT-II", type=None):
        self.item_name = item_name
        self.category = category
        self.type = type


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
    authorized_strength = db.Column(
        db.Integer,
        nullable=True,
        default=0
    )
    posted_strength = db.Column(
        db.Integer,
        nullable=True,
        default=0
    )

    def __init__(self, name, authorized_strength=0, posted_strength=0):
        self.name = name
        self.authorized_strength = authorized_strength
        self.posted_strength = posted_strength

class Strength(db.Model):
    __tablename__ = "unit_strength"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    unit_name = db.Column(db.String(255), nullable=False)
    posted_strength = db.Column(db.Integer, default=0, nullable=True)
    authorized_strength = db.Column(db.Integer, default=0, nullable=True)

    def __init__(self, unit_name, posted_strength=0, authorized_strength=0):
        self.unit_name = unit_name
        self.posted_strength = posted_strength
        self.authorized_strength = authorized_strength

class TrackUnitItems(db.Model):
    __tablename__ = "track_unit_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    unit_name = db.Column(db.String(255), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("ecc_scme_items.id"), nullable=False)
    auth = db.Column(db.Integer, default=0, nullable=False)   # MAX limit of this item for unit
    held = db.Column(db.Integer, default=0, nullable=False)   # Quantity currently held
    ser = db.Column(db.Integer, default=0, nullable=False)    # Serviceable quantity held
    pws = db.Column(db.Integer, default=0, nullable=False)    # Partially working quantity held
    issued_at = db.Column(db.DateTime, nullable=True, server_default=db.func.now())

    item = db.relationship("ScmeItems", backref="track_unit_records")

    def __init__(self, unit_name, item_id, auth=0, held=0, ser=0, pws=0, issued_at=None):
        self.unit_name = unit_name
        self.item_id = item_id
        self.auth = auth
        self.held = held
        self.ser = ser
        self.pws = pws
        self.issued_at = issued_at

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


class EccMonthlyState(db.Model):
    __tablename__ = "ecc_monthly_state"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_id = db.Column(db.Integer, db.ForeignKey("ecc_scme_items.id"), nullable=False)
    scale = db.Column(db.String(100), nullable=True)
    
    auth_auth = db.Column(db.Integer, default=0)
    auth_res = db.Column(db.Integer, default=0)
    auth_total = db.Column(db.Integer, default=0)
    unit_auth = db.Column(db.Integer, default=0)
    
    bbf_division = db.Column(db.String(255), nullable=False)
    bbf_ser = db.Column(db.Integer, default=0)
    bbf_pws = db.Column(db.Integer, default=0)
    bbf_total = db.Column(db.Integer, default=0)
    bbf_comd = db.Column(db.Integer, nullable=True)
    bbf_ihq = db.Column(db.Integer, nullable=True)
    
    recd_ser = db.Column(db.Integer, default=0)
    recd_pws = db.Column(db.Integer, default=0)
    recd_total = db.Column(db.Integer, default=0)
    
    issd_ser = db.Column(db.Integer, default=0)
    issd_pws = db.Column(db.Integer, default=0)
    issd_total = db.Column(db.Integer, default=0)
    
    stock_ser = db.Column(db.Integer, default=0)
    stock_pws = db.Column(db.Integer, default=0)
    stock_total = db.Column(db.Integer, default=0)
    stock_comd = db.Column(db.Integer, nullable=True)
    stock_ihq = db.Column(db.Integer, nullable=True)
    
    add_knd = db.Column(db.Integer, default=0)
    add_tn_model = db.Column(db.Integer, default=0)
    add_n_area_otg = db.Column(db.Integer, default=0)
    add_idt_ict = db.Column(db.Integer, default=0)
    add_remarks_ro_bal = db.Column(db.Integer, default=0)
    
    tps = db.Column(db.Integer, default=0)
    deficiency = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    item = db.relationship("ScmeItems", backref="ecc_monthly_states")

    def __init__(self, item_id, scale, auth_auth, auth_res, auth_total,
                 bbf_division, bbf_ser, bbf_pws, bbf_total, bbf_comd, bbf_ihq,
                 recd_ser, recd_pws, recd_total,
                 issd_ser, issd_pws, issd_total,
                 stock_ser, stock_pws, stock_total, stock_comd, stock_ihq,
                 add_knd, add_tn_model, add_n_area_otg, add_idt_ict, add_remarks_ro_bal,
                 tps, deficiency=0, unit_auth=0):
        self.item_id = item_id
        self.scale = scale
        self.auth_auth = auth_auth
        self.auth_res = auth_res
        self.auth_total = auth_total
        self.bbf_division = bbf_division
        self.bbf_ser = bbf_ser
        self.bbf_pws = bbf_pws
        self.bbf_total = bbf_total
        self.bbf_comd = bbf_comd
        self.bbf_ihq = bbf_ihq
        self.recd_ser = recd_ser
        self.recd_pws = recd_pws
        self.recd_total = recd_total
        self.issd_ser = issd_ser
        self.issd_pws = issd_pws
        self.issd_total = issd_total
        self.stock_ser = stock_ser
        self.stock_pws = stock_pws
        self.stock_total = stock_total
        self.stock_comd = stock_comd
        self.stock_ihq = stock_ihq
        self.add_knd = add_knd
        self.add_tn_model = add_tn_model
        self.add_n_area_otg = add_n_area_otg
        self.add_idt_ict = add_idt_ict
        self.add_remarks_ro_bal = add_remarks_ro_bal
        self.tps = tps
        self.deficiency = deficiency
        self.unit_auth = unit_auth






