from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    category: str
    confidence: float

def build_summary(txs: List[Transaction], month: str) -> Dict:
    """
    Resumen mensual simple (Fase 1):
    - ingresos, gastos, neto
    - top categorías de gasto
    """
    month_txs = [t for t in txs if t.date.startswith(month)]

    income = sum(t.amount for t in month_txs if t.amount > 0)
    expense = sum(-t.amount for t in month_txs if t.amount < 0)  # positivo
    net = income - expense

    # gasto por categoría
    by_cat = {}
    for t in month_txs:
        if t.amount < 0:
            by_cat[t.category] = by_cat.get(t.category, 0) + (-t.amount)

    top_spend = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)[:5]

    # status simple
    if income <= 0 and expense > 0:
        status = "red"
    else:
        if net < 0:
            status = "red"
        elif net < max(1.0, income * 0.05):
            status = "yellow"
        else:
            status = "green"

    return {
        "month": month,
        "income": round(income, 2),
        "expense": round(expense, 2),
        "net": round(net, 2),
        "status": status,
        "top_spend": [{"category": c, "amount": round(a, 2)} for c, a in top_spend],
        "count_records": len(month_txs),
    }

def explain(summary: Dict) -> str:
    income = summary["income"]
    expense = summary["expense"]
    net = summary["net"]
    status = summary["status"]

    if income <= 0 and expense > 0:
        return "Solo detecté gastos este mes. Agrega ingresos (manual o recurrentes) para evaluar tu flujo."

    if status == "red":
        return f"Mes en rojo. Te faltaron {abs(net):,.2f} para cubrir tus gastos."
    if status == "yellow":
        return f"Mes justo. Cerraste con {net:,.2f}. Si bajas un poco el gasto fijo, mejoras margen."
    return f"Buen mes. Cerraste con {net:,.2f} neto. Mantén el control y evita picos de gasto."
