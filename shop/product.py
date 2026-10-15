from dataclasses import dataclass
from typing import Optional

@dataclass
class Product:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    price: float = 0.0
    category: str = ""
    is_active: bool = True
    created_at: Optional[str] = None
    delivery_instruction: Optional[str] = None