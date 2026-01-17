import re
from typing import List, Tuple, Optional

# =========================
# Normalización y reglas por usuario
# =========================
def normalize_contains(text: str) -> str:
    t = (text or "").strip().upper()
    t = re.sub(r"\s+", " ", t)
    return t[:120]

def match_user_rules(description: str, rules: List[Tuple[str, str]]) -> Optional[str]:
    """
    rules: lista de (contains, category)
    Si description contiene "contains" => category
    """
    d = (description or "").upper()
    for contains, category in rules:
        if contains and contains in d:
            return category
    return None

# =========================
# Clasificación (MVP)
# =========================
def classify(
    description: str,
    amount: float,
    user_rules: Optional[List[Tuple[str, str]]] = None
):
    """
    Devuelve (category, confidence)
    - Primero aplica reglas del usuario (si existen)
    - Luego fallback a reglas simples globales (MVP)
    """
    # 1) Reglas personalizadas del usuario
    if user_rules:
        hit = match_user_rules(description, user_rules)
        if hit:
            return hit, 1.0

    # 2) Fallback global
    desc = (description or "").upper()

    # Ingresos
    if amount > 0:
        if "NOMINA" in desc or "NÓMINA" in desc or "SUELDO" in desc:
            return "Ingreso", 0.90
        return "Ingreso", 0.70

    # Gastos (amount < 0)
    if any(k in desc for k in ["UBER", "DIDI", "CABIFY"]):
        return "Transporte", 0.85

    if any(k in desc for k in ["OXXO", "7-ELEVEN", "SEVEN", "CIRCLE K", "EXTRA"]):
        return "Conveniencia", 0.75

    if any(k in desc for k in ["NETFLIX", "SPOTIFY", "AMAZON PRIME", "PRIME VIDEO", "APPLE", "GOOGLE"]):
        return "Suscripciones", 0.75

    if any(k in desc for k in ["WALMART", "COSTCO", "SORIANA", "HEB", "SUPER", "SUPERMERCADO"]):
        return "Super", 0.75

    if any(k in desc for k in ["RESTAUR", "STARBUCKS", "CAFÉ", "CAFE", "BAR", "ANTOJ"]):
        return "Restaurantes", 0.70

    if any(k in desc for k in ["TELCEL", "AT&T", "ATT", "IZZI", "TOTALPLAY", "CFE", "GAS", "AGUA"]):
        return "Servicios", 0.70

    if any(k in desc for k in ["RENTA", "HIPOTECA", "MORTGAGE"]):
        return "Renta/Hipoteca", 0.70

    return "Otros", 0.55

