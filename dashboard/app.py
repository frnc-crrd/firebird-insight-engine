"""Punto de entrada del dashboard CxC.

Configura la app de Streamlit con navegacion multipagina,
tema corporativo forzado y sidebar con informacion del sistema.

Ejecucion:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ======================================================================
# CONFIGURACION GLOBAL DE LA APP
# ======================================================================
st.set_page_config(
    page_title="Dashboard CxC - Microsip",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Dashboard de Cuentas por Cobrar - Microsip v1.0",
    },
)

# ======================================================================
# ESTILOS GLOBALES - UI/UX CORPORATIVO
# ======================================================================
st.markdown(
    """
    <style>
        /* Header principal */
        .main-header {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
            padding: 1.75rem 2.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .main-header h1 {
            color: #ffffff !important;
            margin: 0;
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -0.025em;
        }
        .main-header p {
            color: #93c5fd !important;
            margin: 0.5rem 0 0 0;
            font-size: 1.05rem;
            font-weight: 400;
        }

        /* Tarjetas de metricas */
        [data-testid="metric-container"] {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease-in-out;
        }
        [data-testid="metric-container"]:hover {
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            transform: translateY(-2px);
            border-color: #cbd5e1 !important;
        }
        [data-testid="metric-container"] label {
            color: #64748b !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            text-transform: uppercase;
        }
        [data-testid="metric-container"] div[data-testid="stMetricValue"] {
            color: #0f172a !important;
            font-weight: 700 !important;
        }

        /* Botones de accion */
        .stButton > button {
            border-radius: 8px;
            border: 1px solid #2563eb !important;
            color: #ffffff !important;
            background-color: #2563eb !important;
            font-weight: 600;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            background-color: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
        }

        /* Alertas personalizadas */
        .alert-critico {
            background-color: #fef2f2 !important;
            border-left: 4px solid #dc2626 !important;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin: 0.75rem 0;
            color: #991b1b !important;
            font-weight: 500;
        }
        .alert-warning {
            background-color: #fffbeb !important;
            border-left: 4px solid #d97706 !important;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin: 0.75rem 0;
            color: #92400e !important;
            font-weight: 500;
        }
        .alert-ok {
            background-color: #f0fdf4 !important;
            border-left: 4px solid #16a34a !important;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin: 0.75rem 0;
            color: #166534 !important;
            font-weight: 500;
        }

        /* Ocultar elementos nativos */
        footer { visibility: hidden; }
        #MainMenu { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ======================================================================
# NAVEGACION MULTIPAGINA
# ======================================================================
pg = st.navigation(
    [
        st.Page("pages/01_resumen.py",   title="Resumen Ejecutivo"),
        st.Page("pages/02_cartera.py",   title="Cartera y Antiguedad"),
        st.Page("pages/03_clientes.py",  title="Analisis por Cliente"),
        st.Page("pages/04_kpis.py",      title="KPIs Estrategicos"),
        st.Page("pages/05_auditoria.py", title="Auditoria"),
    ]
)

# ======================================================================
# SIDEBAR - INFORMACION DEL SISTEMA
# ======================================================================
with st.sidebar:
    st.markdown("### Sistema")
    st.markdown("**Base de datos:** Microsip Firebird")

    st.divider()

    if st.button("Refrescar datos", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache limpiado. Recargando...")
        st.rerun()

    st.divider()
    st.caption("Dashboard CxC v1.0")
    st.caption("Datos con cache de 1 hora")

# ======================================================================
# EJECUTAR PAGINA ACTIVA
# ======================================================================
pg.run()