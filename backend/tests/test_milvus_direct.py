
from pymilvus import connections, Collection
import time
import numpy as np

print("Connecting to Milvus...")
connections.connect(host='localhost', port='19530')

print("Loading collection...")
col = Collection("AIC_2024_TransNetV2_Full")
col.load()
print(f"Entities: {col.num_entities}")

print("Running search...")
# Random vector
vector = np.random.rand(1, 768).astype(np.float32)

start = time.time()
res = col.search(
    data=vector, 
    anns_field="vector", 
    param={"metric_type": "COSINE", "params": {"nprobe": 16}}, 
    limit=10, 
    output_fields=["path", "video", "frame_id"]
)
end = time.time()

print(f"Search time: {end - start:.4f}s")
print(f"Results: {len(res[0])}")
print("First result:", res[0][0].entity.to_dict())
