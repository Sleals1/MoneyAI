import os
import sys
import pandas as pd
import requests

# =========================
# Config
# =========================
FILE_PATH = r"actividad (3).xlsx"
API_URL = "http://127.0.0.1:8000/records"
CHUNK_SIZE = 200

# Palabras clave para detectar encabezados
DATE_KEYS = ["fecha"]
DESC_KEYS = ["descripción", "descripcion"]
AMT_KEYS  = ["importe", "monto", "amount"]

def norm(s: str) -> str:
    return str(s).strip().lower()

def detect_header_row(df_raw: pd.DataFrame, max_rows: int = 60):
    """
    df_raw viene sin header (header=None). Busca la fila donde aparezcan
    columnas tipo Fecha / Descripción / Importe/Monto.
    """
    n = min(max_rows, len(df_raw))
    for i in range(n):
        row = [norm(x) for x in df_raw.iloc[i].tolist()]
        has_date = any(any(k in cell for k in DATE_KEYS) for cell in row)
        has_desc = any(any(k in cell for k in DESC_KEYS) for cell in row)
        has_amt  = any(any(k in cell for k in AMT_KEYS) for cell in row)
        if has_date and has_desc and has_amt:
            return i
    return None

def find_col(df: pd.DataFrame, keys):
    cols = [norm(c) for c in df.columns]
    for k in keys:
        for idx, c in enumerate(cols):
            if k in c:
                return df.columns[idx]
    return None

def parse_amount_series(s: pd.Series) -> pd.Series:
    """
    Convierte "$1,234.56" / "1,234.56" / numérico a float
    """
    x = s.astype(str).str.replace(",", "", regex=False)
    x = x.str.replace("$", "", regex=False).str.strip()
    return pd.to_numeric(x, errors="coerce")

def require_token() -> str:
    """
    Toma el token de la variable de entorno TOKEN.
    En PowerShell:
      $env:TOKEN="..."
    """
    token = os.getenv("TOKEN", "").strip()
    if not token:
        print("ERROR: Falta TOKEN.")
        print("En PowerShell corre:  $env:TOKEN=\"TU_TOKEN\"")
        sys.exit(1)
    return token

def post_batch(batch, headers):
    resp = requests.post(API_URL, json=batch, headers=headers, timeout=60)
    if resp.status_code == 401:
        print("ERROR 401 Unauthorized: Token inválido o faltante.")
        print("Asegúrate de setear $env:TOKEN con el token correcto.")
        raise SystemExit(1)
    if resp.status_code >= 400:
        print(f"ERROR {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    return resp.json()

def main():
    token = require_token()
    headers = {"Authorization": f"Bearer {token}"}

    if not os.path.exists(FILE_PATH):
        print(f"ERROR: No existe el archivo: {FILE_PATH}")
        sys.exit(1)

    # 1) Lee sin header para detectar la fila correcta
    df_raw = pd.read_excel(FILE_PATH, sheet_name=0, header=None)
    hdr = detect_header_row(df_raw)

    if hdr is None:
        print("No pude detectar la fila de encabezados (Fecha/Descripción/Importe).")
        print("Tip: dime qué fila ves en Excel donde empieza la tabla.")
        sys.exit(1)

    # 2) Vuelve a leer usando esa fila como header
    df = pd.read_excel(FILE_PATH, sheet_name=0, header=hdr)

    col_date = find_col(df, DATE_KEYS)
    col_desc = find_col(df, DESC_KEYS)
    col_amt  = find_col(df, AMT_KEYS)

    if not (col_date and col_desc and col_amt):
        print("Detecté header row:", hdr)
        print("No encontré columnas necesarias. Detecté:")
        print("Fecha:", col_date, "Descripción:", col_desc, "Importe/Monto:", col_amt)
        print("Columnas disponibles:", list(df.columns))
        sys.exit(1)

    # 3) Limpieza base
    df = df.dropna(subset=[col_date, col_desc, col_amt]).copy()
    df[col_desc] = df[col_desc].astype(str).str.strip()

    # 4) Fecha robusta
    dates = pd.to_datetime(df[col_date], errors="coerce")
    df = df.loc[dates.notna()].copy()
    df["__date__"] = dates.dt.date.astype(str)

    # 5) Monto robusto
    df["__amt__"] = parse_amount_series(df[col_amt])
    df = df.loc[df["__amt__"].notna()].copy()

    # 6) Construye items para API
    items = []
    for _, r in df.iterrows():
        importe = float(r["__amt__"])

        # Convención:
        # - gasto = negativo
        # - ingreso = positivo
        #
        # Regla AMEX típica:
        # - cargos vienen como positivos -> gasto
        # - abonos / devoluciones vienen como negativos -> ingreso
        #
        amount = -importe if importe >= 0 else abs(importe)

        items.append({
            "date": r["__date__"],
            "description": str(r[col_desc]),
            "amount": round(amount, 2),
            "source": "import",
        })

    print(f"Header detectado en fila: {hdr}")
    print(f"Transacciones a subir: {len(items)}")

    # 7) Subir en lotes
    uploaded = 0
    for i in range(0, len(items), CHUNK_SIZE):
        batch = items[i:i + CHUNK_SIZE]
        out = post_batch(batch, headers)
        uploaded += len(batch)
        print(f"Uploaded {uploaded}/{len(items)} - server: {out}")

    print("DONE ✅")

if __name__ == "__main__":
    main()
