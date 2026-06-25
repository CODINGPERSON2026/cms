from extensions import db


class OrgLadder(db.Model):
    __tablename__ = "org_ladder"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    type = db.Column(
        db.String(20),
        nullable=False
    )

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("org_ladder.id"),
        nullable=True
    )

    parent = db.relationship(
        "OrgLadder",
        remote_side=[id],
        backref="children"
    )