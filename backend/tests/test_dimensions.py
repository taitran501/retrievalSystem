"""
Check CLIP model embedding dimension vs Milvus collection dimension
"""
import torch
import open_clip
from pymilvus import connections, Collection

# 1. Check CLIP model dimension
print("=" * 60)
print("CHECKING CLIP MODEL DIMENSION")
print("=" * 60)

# Load from config
model_name = "ViT-L-14"
pretrained = "datacomp_xl_s13b_b90k"

print(f"Model: {model_name}")
print(f"Pretrained: {pretrained}")

try:
    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name,
        pretrained=pretrained
    )
    tokenizer = open_clip.get_tokenizer(model_name)
    
    # Encode test text
    text_inputs = tokenizer(["test"])
    with torch.no_grad():
        text_features = model.encode_text(text_inputs)
    
    clip_dim = text_features.shape[1]
    print(f"✓ CLIP embedding dimension: {clip_dim}")
except Exception as e:
    print(f"✗ Error loading CLIP: {e}")
    clip_dim = None

# 2. Check Milvus collection dimension
print("\n" + "=" * 60)
print("CHECKING MILVUS COLLECTION DIMENSION")
print("=" * 60)

try:
    connections.connect(host='localhost', port='19530')
    col = Collection("AIC_2024_TransNetV2_Full")
    
    # Get schema
    schema = col.schema
    print(f"Collection: {col.name}")
    print(f"Total entities: {col.num_entities}")
    
    # Find vector field
    for field in schema.fields:
        if field.dtype == 101:  # DataType.FLOAT_VECTOR
            print(f"✓ Vector field: {field.name}")
            print(f"✓ Vector dimension: {field.params.get('dim', 'N/A')}")
            milvus_dim = field.params.get('dim')
except Exception as e:
    print(f"✗ Error checking Milvus: {e}")
    milvus_dim = None

# 3. Compare
print("\n" + "=" * 60)
print("DIMENSION COMPARISON")
print("=" * 60)

if clip_dim and milvus_dim:
    if clip_dim == milvus_dim:
        print(f"✓ MATCH: CLIP ({clip_dim}) == Milvus ({milvus_dim})")
    else:
        print(f"✗ MISMATCH: CLIP ({clip_dim}) != Milvus ({milvus_dim})")
        print("   This is likely causing 0 results!")
else:
    print("⚠ Could not verify dimensions")
