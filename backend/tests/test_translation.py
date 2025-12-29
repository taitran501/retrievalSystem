"""
Quick test script for Vietnamese translation
"""
import sys

print("Testing Vietnamese translation setup...")

# Test 1: Check Marian availability
try:
    from transformers import MarianMTModel, MarianTokenizer
    print("✅ transformers available")
    
    # Try loading model
    print("Loading Marian vi-en model...")
    model_name = "Helsinki-NLP/opus-mt-vi-en"
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    print("✅ Marian model loaded")
    
    # Test translation
    test_query = "người đàn ông đi bộ"
    inputs = tokenizer(test_query, return_tensors="pt", padding=True, truncation=True, max_length=512)
    outputs = model.generate(**inputs, max_length=512)
    translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"✅ Translation test: '{test_query}' → '{translated}'")
    
except ImportError as e:
    print(f"❌ transformers not available: {e}")
except Exception as e:
    print(f"❌ Marian loading failed: {e}")

# Test 2: Check DRES dictionary
try:
    from dres_dictionary import EXACT_QUERIES, CRITICAL_KEYWORDS
    print(f"✅ DRES dictionary: {len(EXACT_QUERIES)} exact queries, {len(CRITICAL_KEYWORDS)} keywords")
except Exception as e:
    print(f"❌ DRES dictionary failed: {e}")

# Test 3: Check translator
try:
    from translator import get_translator
    translator = get_translator(backend='marian')
    
    test_cases = [
        "người đàn ông đi bộ",  # Should match dictionary
        "person walking",  # English, should pass through
        "con lân đang nhảy trên cọc",  # Complex Vietnamese
    ]
    
    print("\n--- Translation Tests ---")
    for query in test_cases:
        try:
            result = translator.process_query(query)
            print(f"'{query}' → '{result}'")
        except Exception as e:
            print(f"❌ Translation failed for '{query}': {e}")
            import traceback
            traceback.print_exc()
    
except Exception as e:
    print(f"❌ Translator failed: {e}")
    import traceback
    traceback.print_exc()

print("\nTest complete!")
