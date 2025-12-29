"""
DRES Query Dictionary for Vietnamese-English Translation
Pre-built mappings for common DRES competition queries
"""

# Complete query phrases (exact match - highest priority)
EXACT_QUERIES = {
    # === VIETNAM NEWS SPECIFIC ===
    
    # Government & Politics
    "chủ tịch nước phát biểu": "president speaks",
    "thủ tướng tham dự": "prime minister attends",
    "bộ trưởng họp báo": "minister holds press conference",
    "chủ tịch quốc hội": "national assembly chairman",
    "chủ tịch ubnd": "people's committee chairman",
    
    # Events & Ceremonies  
    "lễ khánh thành": "inauguration ceremony",
    "họp báo": "press conference",
    "hội nghị": "conference",
    "lễ ký kết": "signing ceremony",
    "buổi làm việc": "working session",
    "cuộc họp": "meeting",
    
    # Locations
    "tại tp.hcm": "in ho chi minh city",
    "tại hà nội": "in hanoi",
    "tại đà nẵng": "in da nang",
    "thành phố hồ chí minh": "ho chi minh city",
    
    # Government Actions
    "tuyên bố": "announce",
    "công bố": "announce",
    "ban hành": "issue",
    "thông qua": "approve",
    
    # === GENERAL DRES ===
    
    # People with actions
    "người đàn ông đi bộ": "man walking",
    "người phụ nữ chạy": "woman running",
    "trẻ em chơi": "children playing",
    "người già ngồi": "elderly person sitting",
    
    # People with clothing
    "người mặc áo đỏ": "person wearing red shirt",
    "người đàn ông mặc áo xanh": "man wearing blue shirt",
    "người phụ nữ mặc váy": "woman wearing dress",
    
    # Vehicles
    "xe hơi màu trắng": "white car",
    "xe máy màu đen": "black motorcycle",
    "xe buýt": "bus",
    "xe đạp": "bicycle",
    
    # Locations
    "trong nhà": "indoors",
    "ngoài trời": "outdoors",
    "trên đường": "on the street",
    "trong công viên": "in the park",
    
    # Actions with objects
    "người cầm điện thoại": "person holding phone",
    "người đọc sách": "person reading book",
    "người uống nước": "person drinking water",
}

# Critical keywords that MUST be preserved (used for phrase replacement)
CRITICAL_KEYWORDS = {
    # === VIETNAM NEWS DOMAIN ===
    
    # Government Titles
    "chủ tịch nước": "president",
    "thủ tướng": "prime minister",
    "thủ tướng chính phủ": "prime minister",
    "bộ trưởng": "minister",
    "phó thủ tướng": "deputy prime minister",
    "chủ tịch quốc hội": "national assembly chairman",
    "chủ tịch ubnd": "people's committee chairman",
    "ủy viên": "member",
    "đại biểu": "delegate",
    
    # Organizations
    "quốc hội": "national assembly",
    "chính phủ": "government",
    "ủy ban nhân dân": "people's committee",
    "ubnd": "people's committee",
    "hội đồng nhân dân": "people's council",
    "hđnd": "people's council",
    "bộ": "ministry",
    
    # Vietnamese Locations - Cities
    "tp.hcm": "ho chi minh city",
    "tp. hcm": "ho chi minh city",
    "thành phố hồ chí minh": "ho chi minh city",
    "hồ chí minh": "ho chi minh city",
    "sài gòn": "ho chi minh city",
    "hà nội": "hanoi",
    "đà nẵng": "da nang",
    "cần thơ": "can tho",
    "hải phòng": "hai phong",
    
    # Vietnamese Locations - General
    "việt nam": "vietnam",
    "thủ đô": "capital",
    "tỉnh": "province",
    "huyện": "district",
    "xã": "commune",
    "phường": "ward",
    
    # News Events
    "họp báo": "press conference",
    "hội nghị": "conference",
    "hội thảo": "seminar",
    "lễ khánh thành": "inauguration ceremony",
    "lễ ký kết": "signing ceremony",
    "lễ phát động": "launching ceremony",
    "buổi làm việc": "working session",
    "cuộc họp": "meeting",
    
    # News Actions - Speaking
    "phát biểu": "speak",
    "tuyên bố": "announce",
    "công bố": "announce",
    "tuyên dương": "commend",
    "khen thưởng": "reward",
    "kêu gọi": "call for",
    "đề ra": "propose",
    
    # News Actions - Government
    "ban hành": "issue",
    "thông qua": "approve",
    "ký kết": "sign",
    "khánh thành": "inaugurate",
    "thăm": "visit",
    "kiểm tra": "inspect",
    "chỉ đạo": "direct",
    
    # === GENERAL DRES ===
    
    # People - Gender/Age (MT handles these well, no need for tags)
    "trẻ em": "child",
    "em bé": "baby",
    "người già": "elderly person",
    "thanh niên": "young person",
    
    # Common DRES specific terms (High Signal Visual Anchors)
    "đầu trọc": "bald head",
    "áo sọc": "striped shirt",
    "kẻ sọc": "striped",
    "gây tai nạn": "caused the accident",
    "va chạm": "collision",
    "cháy": "fire",
    "khói": "smoke",
    "đám đông": "crowd",
    "nam": "male",
    "nữ": "female",
    "võ vovinam": "vovinam martial arts",
    "vovinam": "vovinam martial arts",
    "múa lân": "lion dance",
    "con lân": "lion dance",
    "cây giáo": "spear",
    "ngọn giáo": "spear",
    
    # Actions - Movement (Only specific ones)
    "nhảy": "jumping",
    "bơi": "swimming",
    "đứng": "standing",
    "ngồi": "sitting",
    "nằm": "lying",
    
    # Actions - Activities
    "đọc": "reading",
    "viết": "writing",
    "nghe": "listening",
    
    # Objects - Vehicles
    "xe máy": "motorcycle",
    "xe đạp": "bicycle",
    "xe buýt": "bus",
    "xe buýt màu xanh lá": "green bus",
    "xe buýt màu vàng": "yellow bus",
    "máy bay": "airplane",
    "tàu hỏa": "train",
    
    # Objects - Electronics
    "laptop": "laptop",
    "tivi": "television",
    
    # Objects - Common items
    "chai": "bottle",
    "ly": "cup",
    
    # Clothing (Specific items)
    "váy": "dress",
    "đầm": "dress",
    "giày": "shoes",
    "mũ": "hat",
    "kính": "glasses",
    
    # Colors (Often important for anchors)
    "màu đỏ": "red",
    "màu xanh lá": "green",
    "màu xanh dương": "blue",
    "màu xanh nước biển": "blue",
    "màu xanh": "blue",
    "màu vàng": "yellow",
    "màu trắng": "white",
    "màu đen": "black",
    
    # Numbers
    "hai": "two",
    "ba": "three",
    "nhiều": "many",
    
    # Attributes
    "lớn": "large",
    "nhỏ": "small",
    "cao": "tall",
    "thấp": "short",
    "dài": "long",
    "ngắn": "short",
}

# Common DRES query patterns (for future expansion)
QUERY_PATTERNS = [
    # Pattern: [person] [action]
    "{person} {action}",
    
    # Pattern: [person] wearing [clothing] [color]
    "{person} mặc {clothing} màu {color}",
    "{person} wearing {color} {clothing}",
    
    # Pattern: [vehicle] [color]
    "{vehicle} màu {color}",
    "{color} {vehicle}",
    
    # Pattern: [person] [action] [object]
    "{person} {action} {object}",
    
    # Pattern: [number] [person] [action]
    "{number} {person} {action}",
]


def get_exact_query(query: str) -> str:
    """
    Get exact translation if available
    
    Args:
        query: Vietnamese query string
        
    Returns:
        English translation if found, otherwise None
    """
    # Normalize query
    query_normalized = query.lower().strip()
    
    return EXACT_QUERIES.get(query_normalized)


def get_keywords():
    """Get all critical keywords for preservation"""
    return CRITICAL_KEYWORDS.copy()
