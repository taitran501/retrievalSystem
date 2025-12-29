from pymilvus import connections, utility, Collection
import os

connections.connect(host="localhost", port=19530)

print("=" * 60)
print("MILVUS COLLECTION AUDIT")
print("=" * 60)

collections = utility.list_collections()
for name in collections:
    c = Collection(name)
    print(f"Collection: {name}")
    print(f"  - Count: {c.num_entities:,}")
    print(f"  - Load Status: {utility.load_state(name)}")

print("\n" + "=" * 60)
print("PROPOSED ACTIONS:")
print("1. Delete redundant folder: data/embeddings (768-dim)")
print("2. Drop old collection: AIC_2024_TransNetV2_Full")
print("=" * 60)
