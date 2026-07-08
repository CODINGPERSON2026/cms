from extensions import db


class LoginUser(db.Model):
    __tablename__ = "login_users"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )
    

    role = db.Column(
        db.String(50),
        nullable=False
    )
    org_id = db.Column(
    db.Integer,
    db.ForeignKey("org_ladder.id"),
    nullable=False
)

    org = db.relationship(
    "OrgLadder",
    backref="users"
)



class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(50),
        nullable =False
    )