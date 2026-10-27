import re
from extensions import db
from models import LoginUser
from models.our_items import OurItems
from models.our_items import ItemRequestTable
from models.org_ladder import OrgLadder

def has_special_characters(value):
    if value is None:
        return False
    return bool(re.search(r'[^a-zA-Z0-9\s_-]', str(value)))



def get_admin_from_org_ladder(org_id):
    current_org = OrgLadder.query.get(org_id)
    print(current_org.name,"this is current login org")

    while current_org:
        admin = LoginUser.query.filter(
            LoginUser.org_id == current_org.id,
            LoginUser.role.in_(["brigade_admin", "division_admin"])
        ).first()

        if admin:
            print('got the')
            return admin.id

        current_org = OrgLadder.query.get(current_org.parent_id)

    return None


def get_parent_admin(org_id):
    current_org = OrgLadder.query.get(org_id)

    # Move to parent first
    if current_org:
        current_org = OrgLadder.query.get(current_org.parent_id)

    while current_org:
        admin = LoginUser.query.filter(
            LoginUser.org_id == current_org.id,
            LoginUser.role.in_(["brigade_admin", "division_admin",'super_admin'])
        ).first()

        if admin:
            return admin.id

        current_org = OrgLadder.query.get(current_org.parent_id)

    return None