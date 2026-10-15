import re

def ai_json_sanitizer(text: str) -> str:
    if not text:
        return "{}"
    
    cleaned = re.sub(r'```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'```', '', cleaned).strip()
    
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        return match.group(0)
        
    return cleaned