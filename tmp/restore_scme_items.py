import sys
import os
import re

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    from models.our_items import ScmeItems
    
    # 1. Parse original items from UPDATED SQL.sql line 92
    sql_path = "UPDATED SQL.sql"
    insert_line = ""
    with open(sql_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "INSERT INTO `ecc_scme_items` VALUES" in line:
                insert_line = line
                break
                
    if insert_line:
        # Find all values like (id, 'item_name', 'category')
        # E.g. (1,'Gaiters','CAT-II'),(2,'Poncho Glacier','CAT-II')
        pattern = r"\(\d+,'[^']+','[^']+'\)"
        matches = re.findall(pattern, insert_line)
        
        with app.app_context():
            print(f"Found {len(matches)} original items in SQL dump. Seeding them with type='scme'.")
            for m in matches:
                # parse out name and category
                # format is (id, 'name', 'category')
                parts = m.strip("()").split(",")
                item_name = parts[1].strip("'")
                category = parts[2].strip("'")
                
                # Check if it already exists as an ECC item.
                # If so, keep it. But we should add it as type='scme' to keep standard SCME function.
                # Since SCME items and ECC items can have the same name but different type.
                item = ScmeItems(item_name=item_name, category=category, type="scme")
                db.session.add(item)
                
            db.session.commit()
            print("Successfully restored original items as type='scme'.")
    else:
        print("Could not find insert line in SQL dump.")
except Exception as e:
    print("Error:", e)
