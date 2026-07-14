import sys
import os

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from extensions import db
from models.our_items import ScmeItems, EccMonthlyState
import random

with app.app_context():
    # 1. Fetch all ecc items
    ecc_items = ScmeItems.query.filter(ScmeItems.type == 'ecc').all()
    print(f"Found {len(ecc_items)} ECC items in catalog.")
    if not ecc_items:
        print("No ECC items found. Inserting some first!")
        # Let's insert some if none exist
        ecc_item_names = [
            ("Bag Sleeping MK-IV", "CAT-I"),
            ("Coat ECC", "CAT-I"),
            ("Socks Men's Woollen", "CAT-I"),
            ("Trouser ECC", "CAT-I"),
            ("Gloves Leather", "CAT-I"),
            ("Rucksack", "CAT-II"),
            ("Gaiters", "CAT-II"),
            ("Camp Mattress", "CAT-II"),
            ("Rescue Bag", "CAT-II")
        ]
        for name, cat in ecc_item_names:
            it = ScmeItems(item_name=name, category=cat, type='ecc')
            db.session.add(it)
        db.session.commit()
        ecc_items = ScmeItems.query.filter(ScmeItems.type == 'ecc').all()
        print(f"Created {len(ecc_items)} ECC items in catalog.")
    
    # Seed 14 rows into EccMonthlyState
    divisions = ["3 Inf Div", "8 Mtn Div", "2 FOD", "14 Corps", "FC (L)"]
    
    # We will insert 14 rows to have a solid dataset
    for i in range(14):
        item = random.choice(ecc_items)
        div = random.choice(divisions)
        scale = f"Scale {random.randint(1, 10)}"
        auth_auth = random.randint(100, 500)
        auth_res = random.randint(10, 50)
        auth_total = auth_auth + auth_res
        
        bbf_ser = random.randint(80, 400)
        bbf_pws = random.randint(5, 40)
        bbf_total = bbf_ser + bbf_pws
        bbf_comd = random.randint(0, 10)
        bbf_ihq = random.randint(0, 10)
        
        recd_ser = random.randint(5, 50)
        recd_pws = random.randint(1, 10)
        recd_total = recd_ser + recd_pws
        
        issd_ser = random.randint(10, 60)
        issd_pws = random.randint(2, 20)
        issd_total = issd_ser + issd_pws
        
        # calculate stock (make sure it's non-negative)
        stock_ser = max(0, bbf_ser + recd_ser - issd_ser)
        stock_pws = max(0, bbf_pws + recd_pws - issd_pws)
        stock_total = stock_ser + stock_pws
        
        stock_comd = random.randint(0, 5)
        stock_ihq = random.randint(0, 5)
        
        add_knd = random.randint(0, 20)
        add_tn_model = random.randint(0, 20)
        add_n_area_otg = random.randint(0, 20)
        add_idt_ict = random.randint(0, 20)
        add_remarks_ro_bal = random.randint(0, 20)
        
        tps = random.randint(50, 200)
        deficiency = max(0, auth_total - stock_total)
        
        state = EccMonthlyState(
            item_id=item.id,
            scale=scale,
            auth_auth=auth_auth,
            auth_res=auth_res,
            auth_total=auth_total,
            bbf_division=div,
            bbf_ser=bbf_ser,
            bbf_pws=bbf_pws,
            bbf_total=bbf_total,
            bbf_comd=bbf_comd,
            bbf_ihq=bbf_ihq,
            recd_ser=recd_ser,
            recd_pws=recd_pws,
            recd_total=recd_total,
            issd_ser=issd_ser,
            issd_pws=issd_pws,
            issd_total=issd_total,
            stock_ser=stock_ser,
            stock_pws=stock_pws,
            stock_total=stock_total,
            stock_comd=stock_comd,
            stock_ihq=stock_ihq,
            add_knd=add_knd,
            add_tn_model=add_tn_model,
            add_n_area_otg=add_n_area_otg,
            add_idt_ict=add_idt_ict,
            add_remarks_ro_bal=add_remarks_ro_bal,
            tps=tps,
            deficiency=deficiency
        )
        db.session.add(state)
    
    db.session.commit()
    print("Successfully seeded 14 rows into ecc_monthly_state!")
