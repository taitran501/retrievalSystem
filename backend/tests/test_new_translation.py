from translator import get_translator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_translations():
    translator = get_translator(backend='google')  # Or 'marian' depending on what's installed
    
    test_queries = [
        "người gây tai nạn đầu trọc mặc áo sọc",
        "một người đàn ông đầu trọc mặc áo thun kẻ sọc",
        "phụ nữ mặc váy đỏ cầm điện thoại",
        "xe hơi màu trắng đi trên đường thành phố",
        "nhiều người tụ tập ở công viên"
    ]
    
    with open("translation_output.txt", "w", encoding="utf-8") as f:
        f.write("=== Translation Test Results ===\n\n")
        for q in test_queries:
            translated = translator.process_query(q)
            f.write(f"Original: {q}\n")
            f.write(f"Translated: {translated}\n")
            f.write("-" * 30 + "\n")
    print("Results written to translation_output.txt")

if __name__ == "__main__":
    test_translations()
