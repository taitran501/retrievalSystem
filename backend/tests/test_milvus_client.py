"""
Test MilvusClient API to replicate backend behavior
"""
import torch
import torch.nn.functional as F
import open_clip
from pymilvus import MilvusClient
import json

print("=" * 60)
print("TEST: Replicate Backend Query with MilvusClient")
print("=" * 60)

# 1. Initialize CLIP (same as backend)
print("\n1. Loading CLIP model...")
model_name = "ViT-L-14"
pretrained = "datacomp_xl_s13b_b90k"

model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
tokenizer = open_clip.get_tokenizer(model_name)

# 2. Encode query
query_text = "person"
print(f"2. Encoding query: '{query_text}'")
text_inputs = tokenizer([query_text])
with torch.no_grad():
    text_features = model.encode_text(text_inputs)
    text_features = F.normalize(text_features, p=2, dim=-1)

query_vector = text_features.tolist()[0]
print(f"   Vector shape: {text_features.shape}")
print(f"   First 5 dims: {query_vector[:5]}")

# 3. Connect to Milvus with MilvusClient (like backend)
print("\n3. Connecting to Milvus with MilvusClient...")
milvus_client = MilvusClient(
    uri="http://localhost:19530",
    db="default"
)

# 4. Load collection (like backend)
collection_name = "AIC_2024_TransNetV2_Full"
print(f"4. Loading collection: {collection_name}")

try:
    milvus_client.load_collection(
        collection_name=collection_name,
        replica_number=1
    )
    
    load_state = milvus_client.get_load_state(collection_name=collection_name)
    print(f"   Load state: {load_state}")
except Exception as e:
    print(f"   Warning: {e}")

# 5. Run search (exactly like backend)
print("\n5. Running search...")
try:
    results = milvus_client.search(
        collection_name=collection_name,
        anns_field="vector",
        data=[query_vector],
        limit=10,
        output_fields=["path", "frame_id", "video"],
        search_params={
            "metric_type": "COSINE",
            "params": {"nprobe": 64}
        }
    )
    
    print(f"   Results type: {type(results)}")
    print(f"   Results length: {len(results)}")
    
    if results and len(results) > 0:
        print(f"   First batch length: {len(results[0])}")
        if len(results[0]) > 0:
            print(f"   ✓ Found {len(results[0])} results!")
            # Print first result
            first_hit = results[0][0]
            print(f"\n   First result:")
            print(f"     Distance: {first_hit.get('distance', first_hit.get('score', 'N/A'))}")
            entity = first_hit.get('entity', first_hit)
            print(f"     Video: {entity.get('video', 'N/A')}")
            print(f"     Path: {entity.get('path', 'N/A')}")
            print(f"     Frame ID: {entity.get('frame_id', 'N/A')}")
        else:
            print(f"   ✗ First batch is empty!")
    else:
        print(f"   ✗ Results is empty!")
        
except Exception as e:
    print(f"   ✗ Error during search: {e}")
    import traceback
    traceback.print_exc()
