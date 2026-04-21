import pandas as pd

# -----------------------------
# CONFIGURACIÓN DEL LEAD
# -----------------------------
LEAD = {
    "empresa": "Lead Ejemplo SL",
    "municipio": "Valencia",
    "provincia": "Valencia",
    "empleados": 5
}

# -----------------------------
# FUNCIÓN DE SCORE
# -----------------------------
def calcular_score(comp, lead):
    score = 0

    # Proximidad
    if comp["D_municipio"] == lead["municipio"]:
        score += 40
    elif comp["tipo"] == "Provincial":
        score += 25
    else:
        score += 10

    # Tamaño relativo
    ratio = comp["E_empleados"] / lead["empleados"]
    if 3 <= ratio <= 20:
        score += 30
    else:
        score += max(0, 30 - abs(ratio - 10))

    # Visibilidad Google
    score_google = min(comp["T_score_google"], 20)
    score += score_google

    # Licitaciones (placeholder)
    score += min(comp.get("licitaciones_24m", 0), 10)

    return round(score, 2)

# -----------------------------
# DATOS MOCK (MVP)
# -----------------------------
competidores = [
    {
        "empresa": "Competidor Local SL",
        "tipo": "Local",
        "motivo": "Mismo CNAE y muy conocido en la ciudad",
        "C_email": "info@local.com",
        "C_telefono": "960000001",
        "C_web": "https://local.com",
        "D_direccion": "Calle Mayor 1",
        "D_municipio": "Valencia",
        "D_distancia_km": 2,
        "E_CNAE": "4662",
        "E_empleados": 25,
        "T_facturacion": 3200000,
        "T_score_google": 18,
        "T_ranking": 3,
        "T_crecimiento": 18,
        "T_decrecimiento": 0,
        "T_tendencia": "Crece",
        "licitaciones_24m": 8
    },
    {
        "empresa": "Competidor Provincial SA",
        "tipo": "Provincial",
        "motivo": "Más grande y activo en licitaciones",
        "C_email": "contacto@provincial.com",
        "C_telefono": "960000002",
        "C_web": "https://provincial.com",
        "D_direccion": "Polígono Norte",
        "D_municipio": "Gandía",
        "D_distancia_km": 65,
        "E_CNAE": "4662",
        "E_empleados": 80,
        "T_facturacion": 9000000,
        "T_score_google": 12,
        "T_ranking": 7,
        "T_crecimiento": 5,
        "T_decrecimiento": 0,
        "T_tendencia": "Estable",
        "licitaciones_24m": 10
    }
]

# -----------------------------
# CALCULAR SCORE
# -----------------------------
for c in competidores:
    c["T_score"] = calcular_score(c, LEAD)

# -----------------------------
# EXPORTAR A EXCEL
# -----------------------------
df = pd.DataFrame(competidores)

notas = pd.DataFrame({
    "Cómo se calcula el Score": [
        "Score = Proximidad (0–40) + Tamaño relativo (0–30) + "
        "Visibilidad Google (0–20) + Licitaciones (0–10).\n"
        "El competidor seleccionado es el de mayor score dentro "
        "del radio geográfico más cercano posible."
    ]
})

with pd.ExcelWriter("competidores_MVP.xlsx", engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Competidores", index=False)
    notas.to_excel(writer, sheet_name="Notas_Score", index=False)

print("✅ Excel generado: competidores_MVP.xlsx")
