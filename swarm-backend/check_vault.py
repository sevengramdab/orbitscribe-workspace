from core.business_tools.vault import vault
for coll in vault.collections():
    count = vault.count(coll)
    if count > 0:
        print(f"{coll}: {count} items")
        docs = vault.find(coll, limit=2)
        for doc in docs:
            print(f"  - {doc.get('_id', '?')}: {str(doc)[:120]}...")
        print()
