import sys
import os
import random

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    from models.our_items import ScmeItems, ScmeIssuedItems
    
    with app.app_context():
        # Get SCME items from DB
        scme_items = ScmeItems.query.filter_by(type='scme').all()
        if not scme_items:
            print("No SCME items found in the database. Please seed them first.")
            sys.exit(1)
            
        units = [
            '19_inf_div',
            '28_inf_div',
            'kfsr',
            'vfsr',
            '2_fod',
            '28_mou'
        ]
        
        # We will pick 13 items and insert issued records
        sample_items = random.sample(scme_items, min(len(scme_items), 14))
        
        # Clear existing issued items first
        db.session.query(ScmeIssuedItems).delete()
        db.session.commit()
        
        seeded_count = 0
        for item in sample_items:
            # Let's target a couple of units for this item so we can see deficiency share
            target_units = random.sample(units, random.randint(1, 3))
            
            for unit in target_units:
                auth = random.randint(80, 250)
                held = random.randint(30, auth)
                deficiency = auth - held
                
                scale = random.choice(["1 per indl", "2 per indl", "Nos", "Prs"])
                a_u = random.choice(["Nos", "Prs"])
                
                issued_record = ScmeIssuedItems(
                    unit_name=unit,
                    item_id=item.id,
                    a_u=a_u,
                    unit_authorized=auth,
                    scale=scale,
                    held=held,
                    deficiency=deficiency
                )
                db.session.add(issued_record)
                seeded_count += 1
                
        db.session.commit()
        print(f"Successfully seeded {seeded_count} issued item transactions in scme_issued_items.")
except Exception as e:
    print("Error seeding issued items:", e)
