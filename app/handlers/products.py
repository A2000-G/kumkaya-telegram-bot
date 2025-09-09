from typing import Optional

def search_product(text: str) -> Optional[str]:
    """
    Placeholder: Burada Google Sheets araması yapılacak.
    Şimdilik demo bir yanıt döndürüyoruz.
    """
    q = (text or "").strip().lower()
    if not q:
        return None
    # Demo eşleşme
    if "lider" in q:
        return "LIDER60: 60'lık döner fırın. Demo açıklama. Video: https://youtu.be/dQw4w9WgXcQ"
    return None
