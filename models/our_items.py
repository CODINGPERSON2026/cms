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

    def __init__(self, item_id=None, requested_by=None, admin_id=None, quantity=0, reason="", priority="normal", remarks="", status="pending", **kwargs):
        super().__init__(**kwargs)
        self.item_id = item_id
        self.requested_by = requested_by
        self.admin_id = admin_id
        self.quantity = quantity
        self.reason = reason
        self.priority = priority
        self.remarks = remarks
        self.status = status


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


class Divs(db.Model):
    __tablename__ = "divs"

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

# Backward compatibility alias for existing imports
Units = Divs

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
    scale = db.Column(db.String(255), nullable=True)         # Scale of issue (e.g., '1 per indl')
    auth = db.Column(db.Integer, default=0, nullable=False)   # MAX limit of this item for unit
    held = db.Column(db.Integer, default=0, nullable=False)   # Quantity currently held
    ser = db.Column(db.Integer, default=0, nullable=False)    # Serviceable quantity held
    pws = db.Column(db.Integer, default=0, nullable=False)    # Partially working quantity held
    add_knd = db.Column(db.Integer, default=0, nullable=False)
    add_tn_model = db.Column(db.Integer, default=0, nullable=False)
    add_n_area_otg = db.Column(db.Integer, default=0, nullable=False)
    add_idt_ict = db.Column(db.Integer, default=0, nullable=False)
    available_res = db.Column(db.Integer, default=0, nullable=False)
    available_ser = db.Column(db.Integer, default=0, nullable=False)
    available_pws = db.Column(db.Integer, default=0, nullable=False)
    condemned_ser = db.Column(db.Integer, default=0, nullable=False)
    condemned_pws = db.Column(db.Integer, default=0, nullable=False)
    condemnation_date = db.Column(db.DateTime, nullable=True)
    held_pws = db.Column(db.Integer, nullable=True, default=None)
    issued_at = db.Column(db.DateTime, nullable=True, server_default=db.func.now())

    item = db.relationship("ScmeItems", backref="track_unit_records")

    def __init__(self, unit_name, item_id, scale=None, auth=0, held=0, ser=0, pws=0, issued_at=None,
                 add_knd=0, add_tn_model=0, add_n_area_otg=0, add_idt_ict=0,
                 available_res=0, available_ser=0, available_pws=0,
                 condemned_ser=0, condemned_pws=0, condemnation_date=None):
        self.unit_name = unit_name
        self.item_id = item_id
        self.scale = scale
        self.auth = auth
        self.held = held
        self.ser = ser
        self.pws = pws
        self.issued_at = issued_at
        self.add_knd = add_knd
        self.add_tn_model = add_tn_model
        self.add_n_area_otg = add_n_area_otg
        self.add_idt_ict = add_idt_ict
        self.available_res = available_res
        self.available_ser = available_ser
        self.available_pws = available_pws
        self.condemned_ser = condemned_ser
        self.condemned_pws = condemned_pws
        self.condemnation_date = condemnation_date

    def calc_held(self):
        components_sum = (self.ser or 0) + (self.pws or 0) + (self.available_ser or 0) + (self.available_pws or 0)
        cond = (self.condemned_ser or 0) + (self.condemned_pws or 0)
        if components_sum > 0:
            return max(0, components_sum - cond)
        return max(0, max(self.held or 0, self.available_res or 0) - cond)



class ItemAuth(db.Model):
    __tablename__ = "item_auth"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    unit_name = db.Column(db.String(255), nullable=True, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("ecc_scme_items.id"), nullable=False)
    auth = db.Column(db.Integer, default=0, nullable=True)
    whole_auth = db.Column(db.Integer, nullable=True)
    whole_res = db.Column(db.Integer, nullable=True)
    scale = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=True, server_default=db.func.now())

    item = db.relationship("ScmeItems", backref="item_auth_records")

    def __init__(self, unit_name=None, item_id=None, auth=None, whole_auth=None, whole_res=None, scale=None):
        self.unit_name = unit_name
        self.item_id = item_id
        self.auth = auth
        self.whole_auth = whole_auth
        self.whole_res = whole_res
        self.scale = scale

class Transactions(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    issued_by = db.Column(db.String(255), nullable=False)
    received_by = db.Column(db.String(255), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("ecc_scme_items.id"), nullable=False)
    ser = db.Column(db.Integer, default=0, nullable=False)
    pws = db.Column(db.Integer, default=0, nullable=False)
    scale = db.Column(db.String(255), nullable=True)
    type = db.Column(db.String(50), nullable=True)
    remarks = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=True, server_default=db.func.now())

    item = db.relationship("ScmeItems", backref="transaction_records")

    def __init__(self, issued_by, received_by, item_id, ser=0, pws=0, scale=None, type=None, remarks=None, timestamp=None):
        self.issued_by = issued_by
        self.received_by = received_by
        self.item_id = item_id
        self.ser = ser
        self.pws = pws
        self.scale = scale
        self.type = type
        self.remarks = remarks
        if timestamp:
            self.timestamp = timestamp

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





class FodStock(db.Model):
    __tablename__ = "fod_stock_table"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    voucher_no = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("ecc_scme_items.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    source = db.Column(db.String(20), nullable=False)   # Depo / LP
    pws = db.Column(db.Integer, nullable=False, default=0)
    ser = db.Column(db.Integer, nullable=False, default=0)
    type = db.Column(db.String(20), nullable=False)     # RES / IHQ / CMD
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    item = db.relationship("ScmeItems", backref="fod_stocks")

    def __init__(self, voucher_no, category, item_id, quantity, source, pws, ser, type):
        self.voucher_no = voucher_no
        self.category = category
        self.item_id = item_id
        self.quantity = quantity
        self.source = source
        self.pws = pws
        self.ser = ser
        self.type = type


class ArmyPersonnel(db.Model):
    __tablename__ = "army_personnel"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    army_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    rank = db.Column(db.String(50), nullable=False)
    company = db.Column(db.String(100), nullable=True)
    unit_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __init__(self, army_number, name, rank, company=None, unit_name=None):
        self.army_number = army_number
        self.name = name
        self.rank = rank
        self.company = company
        self.unit_name = unit_name


class UnitTpsStock(db.Model):
    __tablename__ = "unit_tps_stock"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    unit_name = db.Column(db.String(100), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("ecc_scme_items.id"), nullable=False)
    army_number = db.Column(db.String(50), db.ForeignKey("army_personnel.army_number"), nullable=True)
    tps_ser = db.Column(db.Integer, nullable=False, default=0)
    tps_pws = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    item = db.relationship("ScmeItems", backref="tps_stocks")
    personnel = db.relationship("ArmyPersonnel", backref="tps_stocks", foreign_keys=[army_number])

    def __init__(self, unit_name, item_id, army_number=None, tps_ser=0, tps_pws=0):
        self.unit_name = unit_name
        self.item_id = item_id
        self.army_number = army_number
        self.tps_ser = tps_ser
        self.tps_pws = tps_pws


class CondemnationRequest(db.Model):
    """
    Tracks per-item condemnation requests raised by a unit.
    The unit specifies an absolute quantity (ser + pws) to condemn.
    On DOU approval the amounts are ACCUMULATED into TrackUnitItems.condemned_ser/pws.
    Status lifecycle: 'pending' → 'approved' | 'rejected'
    """
    __tablename__ = "condemnation_requests"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Requesting unit
    unit_name = db.Column(db.String(255), nullable=False, index=True)

    # Parent DOU name (resolved at request time from OrgLadder)
    parent_dou_name = db.Column(db.String(255), nullable=False, index=True)

    # Item being condemned
    item_id = db.Column(db.Integer, db.ForeignKey("ecc_scme_items.id"), nullable=False)

    # Condemnation Number & Attached PDF
    condemnation_no = db.Column(db.String(100), nullable=True)
    pdf_filename = db.Column(db.String(255), nullable=True)
    pdf_original_name = db.Column(db.String(255), nullable=True)

    # Quantities requested (absolute — what the unit wants to condemn in this request)
    req_ser = db.Column(db.Integer, nullable=False, default=0)
    req_pws = db.Column(db.Integer, nullable=False, default=0)

    # Reason / remarks provided by unit
    reason = db.Column(db.String(500), nullable=True)

    # Disposal / Certificate tracking
    salvage_rv = db.Column(db.Boolean, default=False, nullable=False)
    destruction_certificate = db.Column(db.Boolean, default=False, nullable=False)

    # Status: 'pending' | 'approved' | 'rejected'
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)

    # DOU reviewer info
    reviewed_by = db.Column(db.String(255), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.String(500), nullable=True)

    # Audit timestamps
    requested_by_user_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    item = db.relationship("ScmeItems", backref="condemnation_requests")

    def __init__(self, unit_name, parent_dou_name, item_id,
                 req_ser=0, req_pws=0, condemnation_no=None,
                 pdf_filename=None, pdf_original_name=None,
                 reason=None, status='pending', requested_by_user_id=None,
                 salvage_rv=False, destruction_certificate=False):
        self.unit_name = unit_name
        self.parent_dou_name = parent_dou_name
        self.item_id = item_id
        self.req_ser = req_ser
        self.req_pws = req_pws
        self.condemnation_no = condemnation_no
        self.pdf_filename = pdf_filename
        self.pdf_original_name = pdf_original_name
        self.reason = reason
        self.status = status
        self.requested_by_user_id = requested_by_user_id
        self.salvage_rv = salvage_rv
        self.destruction_certificate = destruction_certificate
