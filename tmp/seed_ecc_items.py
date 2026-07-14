import sys
import os

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    from models.our_items import ScmeItems
    
    with app.app_context():
        # Clear existing items if any to avoid duplicates
        db.session.query(ScmeItems).filter_by(type='ecc').delete()
        
        # ECC Cat-I Items
        cat1_items = [
            "Bag Sleeping MK-IV",
            "Coat ECC",
            "Socks Men's Woollen",
            "Trouser ECC / Trouser BD Serge",
            "Gloves Leather",
            "Cap Balaclava Snow",
            "Goggles GS MK-II",
            "Vest Thermal",
            "Under Pant Woollen",
            "Sun Screen Lotion"
        ]
        
        # ECC Cat-II Items
        cat2_items = [
            "Snow Boot / Boot RI",
            "Rucksack",
            "Gaiters",
            "Carrier Man Pack",
            "Hot Water Bottle Rubber",
            "Camp Mattress Outdoor",
            "Rescue Bag",
            "ISHD",
            "Rod Avalanche & Marker Trail",
            "Winter Overall",
            "Mattress Kapok MK-II Complete",
            "Tank Mule High Altitude",
            "Tent Arctic Small MK-II",
            "Tent Arctic Med MK-II",
            "Tent Arctic Large MK-II",
            "Tent Arctic Med Medical MK-II",
            "Face Mask"
        ]
        
        # Add to session
        for name in cat1_items:
            # Replace non-standard hyphens with standard dashes
            normalized_name = name.replace("‑", "-")
            item = ScmeItems(item_name=normalized_name, category="CAT-I", type="ecc")
            db.session.add(item)
            
        for name in cat2_items:
            # Replace non-standard hyphens with standard dashes
            normalized_name = name.replace("‑", "-")
            item = ScmeItems(item_name=normalized_name, category="CAT-II", type="ecc")
            db.session.add(item)
            
        db.session.commit()
        print("Successfully seeded ECC items into ecc_scme_items.")
except Exception as e:
    print("Error during seeding:", e)
