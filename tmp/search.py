target = "ecc_scme_items"
path = "UPDATED SQL.sql"
try:
    with open(path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f, 1):
            if target in line:
                print(f"Line {idx}: {line[:120].strip()}")
except Exception as e:
    print(e)
