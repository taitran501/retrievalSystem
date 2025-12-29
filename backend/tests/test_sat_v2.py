
import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.translator import get_translator
from utils.dres_dictionary import get_keywords

async def test_translation():
    print("Testing SAT v2 (Longest-Match First)...")
    translator = get_translator()
    
    # Mock direct translation to simulate behavior without loading models
    def mock_translate(text, source='vi', target='en'):
        # Return a simple translation based on query content
        if "xe bus" in text: return "bus"
        if "vovinam" in text: return "martial arts"
        if "múa lân" in text: return "dance"
        return text
        
    translator.translate_with_timeout = mock_translate
    
    test_cases = [
        "xe bus màu xanh lá",
        "võ vovinam trên sân cỏ",
        "múa lân con lân",
        "người cầm cây giáo"
    ]
    
    for query in test_cases:
        translated = translator.translate_smart(query)
        print(f"Query: '{query}'")
        print(f"Result: '{translated}'")
        # Check for overlaps
        if "xanh lá" in query:
            if "green" in translated and "blue" not in translated:
                print("Correct: Green found, Blue avoided")
            elif "blue" in translated:
                print("Failed: Blue found in green query")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_translation())
