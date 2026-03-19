"""Configuracion del proyecto de auditoria CxC para Microsip.

Define rutas de archivos, parametros de analisis (rangos de antiguedad,
umbrales de anomalias), ventana de KPIs, nombres de archivos Excel de
salida y contrasenas de hojas protegidas.

Las credenciales de conexion a la base de datos Firebird se gestionan
mediante variables de entorno por motivos de seguridad, evitando su
exposicion en el codigo fuente.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ============================================================================
# RUTAS DEL PROYECTO
# ============================================================================

BASE_DIR: Path = Path(__file__).resolve().parent.parent
OUTPUT_DIR: Path = BASE_DIR / "output"

# Cargar variables de entorno desde el archivo .env si existe en el entorno local
load_dotenv(BASE_DIR / ".env")

# ============================================================================
# CONEXION A FIREBIRD (Microsip - Produccion)
# ============================================================================

# Lectura segura de variables de entorno. Se definen valores por defecto
# unicamente para variables no criticas.
_db_host = os.getenv("FIREBIRD_HOST", os.getenv("FIREBIRD_IP"))
_db_port = os.getenv("FIREBIRD_PORT")
_db_database = os.getenv("FIREBIRD_DATABASE")
_db_user = os.getenv("FIREBIRD_USER")
_db_password = os.getenv("FIREBIRD_PASSWORD")
_db_charset = os.getenv("FIREBIRD_CHARSET")

# Principio Fail-Fast: Validacion estricta de variables criticas
if not _db_database or not _db_password:
    raise ValueError(
        "Faltan variables de entorno criticas. Asegurese de definir "
        "FIREBIRD_DATABASE y FIREBIRD_PASSWORD en su archivo .env o en "
        "el entorno del sistema."
    )

FIREBIRD_CONFIG: dict[str, str | int] = {
    "host": _db_host,
    "port": _db_port,
    "database": _db_database,
    "user": _db_user,
    "password": _db_password,
    "charset": _db_charset,
}

# ============================================================================
# RANGOS DE ANTIGUEDAD Y RECAUDO
# ============================================================================

RANGOS_ANTIGUEDAD: list[tuple[int | None, int | None, str]] = [
    (None, -2, "VIGENTE: MÁS DE 1 DÍA"),
    (-1,   -1, "VIGENTE: VENCE MAÑANA"),
    (0,    0,  "VIGENTE: VENCE HOY"),
    (1,    30, "VENCIDO: 1-30 DÍAS"),
    (31,   60, "VENCIDO: 31-60 DÍAS"),
    (61,   90, "VENCIDO: 61-90 DÍAS"),
    (91,   120,"VENCIDO: 91-120 DÍAS"),
    (121, None,"VENCIDO: MÁS DE 120 DÍAS"),
]

RANGOS_RECAUDO: list[tuple[int | None, int | None, str]] = [
    (None, -1, "PAGO ANTICIPADO"),
    (0,    0,  "PAGO PUNTUAL"),
    (1,    15, "RETRASO LEVE (1-15)"),
    (16,   30, "RETRASO MODERADO (16-30)"),
    (31,   60, "RETRASO ALTO (31-60)"),
    (61, None, "RETRASO CRITICO (>60)"),
]

ANOMALIAS: dict[str, int | float] = {
    "importe_zscore_umbral":       3.0,
    "delta_recaudo_zscore_umbral": 3.0,
    "delta_mora_zscore_umbral":    3.0,
    "dias_vencimiento_critico":    90,
}

# ============================================================================
# KPIS ESTRATEGICOS
# ============================================================================

KPI_PERIODO_DIAS: int = 90

# ============================================================================
# ARCHIVOS DE SALIDA
# ============================================================================

OUTPUT_FORMATS: list[str] = ["xlsx"]

EXCEL_ENGINE: str = "openpyxl"

EXCEL_NOMBRES: dict[str, str] = {
    "auditoria": "00_auditoria_cxc",
    "cxc":       "01_reporte_cxc",
    "analisis":  "02_analisis_cxc",
    "pdf":       "03_dashboard_cxc",
}

SHEET_PASSWORDS: dict[str, str] = {
    "registros_totales_cxc": os.getenv("EXCEL_SHEET_PASSWORD"),
}