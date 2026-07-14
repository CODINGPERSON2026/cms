import sys
import os

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    from models.our_items import ScmeItems
    from sqlalchemy import text
    
    with app.app_context():
        # Disabling FK checks to safely empty the table
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.session.execute(text("TRUNCATE TABLE ecc_scme_items;"))
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.session.commit()
        
        # 1. ECC Items
        ecc_cat1 = [
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
        
        ecc_cat2 = [
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
        
        # 2. SCME Items
        scme_cat1 = [
            "Head Cap Woollen / Head Cap Spl",
            "Socks Woollen Two Layer",
            "Bag Water Proof",
            "Drawers Cold Weather",
            "Under Shirt Cold Weather",
            "Sleeping Bag Spl",
            "Mask Face (Balaclava)",
            "Boot Multipurpose",
            "Snow Goggle / Goggle Cortina",
            "Jacket Down",
            "Trouser Down",
            "Mattress (Glacier)",
            "Rucksack",
            "Gloves inner and Gloves outer as a set",
            "Professional Modular Gloves",
            "Jacket Wind Cheater / Over Garment Blouse",
            "Over Garment Trouser",
            "ECWCS",
            "Summer Suit for Super High Altitude Areas"
        ]
        
        scme_cat2 = [
            "Karabiner 'P' Type",
            "Karabiner 'S' Type",
            "Pulleys",
            "Tent HA 10-12 Men",
            "Spare Glasses Goggle",
            "Rope Climbing Glacier",
            "Thermal Insoles",
            "Under Slung Cargo Nets",
            "Knife All Purposes",
            "Rock Piton (Horizontal) / Rock Piton (Vertical)",
            "Fire Star Refill 4 Kg",
            "Fire Star Cooker",
            "Fire Star Refill Tube 150 gm",
            "Oxygen Cylinder",
            "Altimeter",
            "Ladder Crevasse — Size 8-16 (20%), Size 12-24 (40%), Size 16-32 (40%)",
            "Sunreal Blanket",
            "Boot Crampons"
        ]
        
        # Seeding ECC items
        for name in ecc_cat1:
            name = name.replace("‑", "-").strip()
            item = ScmeItems(item_name=name, category="CAT-I", type="ecc")
            db.session.add(item)
            
        for name in ecc_cat2:
            name = name.replace("‑", "-").strip()
            item = ScmeItems(item_name=name, category="CAT-II", type="ecc")
            db.session.add(item)
            
        # Seeding SCME items
        for name in scme_cat1:
            name = name.replace("‑", "-").strip()
            item = ScmeItems(item_name=name, category="CAT-I", type="scme")
            db.session.add(item)
            
        for name in scme_cat2:
            name = name.replace("‑", "-").strip()
            item = ScmeItems(item_name=name, category="CAT-II", type="scme")
            db.session.add(item)
            
        db.session.commit()
        print("Successfully seeded all ECC and SCME items.")
except Exception as e:
    print("Error seeding all items:", e)
