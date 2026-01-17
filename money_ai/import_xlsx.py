import json
import pandas as pd
import requests

FILE_PATH = r"actividad (3).xlsx"  # pon aquí la ruta si no está en la misma carpeta
SHEET = "Detalles de la operación"
API_URL = "http://127.0.0.1:8000/transactions"

def parse_date(s):
    # Ej: "02 Jan 2026" -> "2026-01-02"
    return pd.to_datetime(s, format="%d %b %Y").date().isoformat()

def main():
    # La tabla real empieza en la fila donde están los headers (en tu archivo es header=6)
    df = pd.read_excel(FILE_PATH, sheet_name=SHEET, header=6)

    # Limpieza mínima
    df = df.dropna(subset=["Fecha", "Descripción", "Importe"])
    df["Descripción"] = df["Descripción"].astype(str).str.strip()

    items = []
    for _, r in df.iterrows():
        importe = float(r["Importe"])

        # AMEX: Importe positivo = gasto -> lo pasamos a negativo.
        # Importe negativo = abono/devolución -> lo pasamos a positivo.
        if importe >= 0:
            amount = -importe
        else:
            amount = abs(importe)

        items.append({
            "date": parse_date(r["Fecha"]),
            "description": r["Descripción"],
            "amount": round(amount, 2)
        })

    # Sube en lotes para evitar requests enormes
    chunk = 200
    for i in range(0, len(items), chunk):
        batch = items[i:i+chunk]
        resp = requests.post(API_URL, json=batch, timeout=30)
        resp.raise_for_status()
        print(f"Uploaded {i+len(batch)}/{len(items)}")

    print("DONE")

if __name__ == "__main__":
    main()
