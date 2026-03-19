"""Capa de carga y caché de datos para el dashboard CxC.

Este módulo es el único punto de contacto entre la capa de presentación
(Streamlit) y la lógica de negocio (src/). Centraliza la conexión a
Firebird, la transformación de datos en memoria y aplica caché con TTL
de 1 hora para evitar reconexiones en cada interacción del usuario.

Si en el futuro migras a Dash, solo reemplazas el decorador
``@st.cache_data`` por la estrategia de caché de Dash (Flask-Caching
o variable global con timestamp). El resto del archivo no cambia.

Uso desde cualquier página:
    from dashboard.data_loader import cargar_kpis, cargar_analytics
    kpis = cargar_kpis()
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# Asegurar que la raiz del proyecto este en el path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import (
    ANOMALIAS,
    FIREBIRD_CONFIG,
    KPI_PERIODO_DIAS,
    RANGOS_ANTIGUEDAD,
)
from src.analytics import Analytics
from src.auditor import Auditor
from src.db_connector import FirebirdConnector
from src.data_transformer import DataTransformer
from src.kpis import generar_kpis
from src.reporte_cxc import generar_reporte_cxc


# ======================================================================
# CARGA DE DATOS PRINCIPAL
# ======================================================================

@st.cache_data(ttl=3600)
def cargar_datos_crudos() -> pd.DataFrame:
    """Extrae y transforma los datos desde Firebird en memoria.

    Utiliza el DataTransformer para replicar la logica de negocio
    de cuentas por cobrar sin exponer la logica a nivel de sentencias
    SQL en la base de datos.

    Returns:
        pd.DataFrame: Conjunto de datos transaccional maestro.
    """
    connector = FirebirdConnector(FIREBIRD_CONFIG)
    transformer = DataTransformer(connector)
    return transformer.get_master_cxc_data()


@st.cache_data(ttl=3600)
def cargar_reporte() -> dict[str, pd.DataFrame]:
    """Genera el reporte operativo base.

    Returns:
        dict[str, pd.DataFrame]: Diccionario con las vistas del reporte.
    """
    df = cargar_datos_crudos()
    return generar_reporte_cxc(df)


@st.cache_data(ttl=3600)
def cargar_kpis() -> dict[str, pd.DataFrame]:
    """Calcula los indicadores clave de rendimiento (KPIs).

    Returns:
        dict[str, pd.DataFrame]: Diccionario con los DataFrames de KPIs.
    """
    df = cargar_datos_crudos()
    return generar_kpis(df, KPI_PERIODO_DIAS)


@st.cache_data(ttl=3600)
def cargar_analytics() -> dict[str, pd.DataFrame]:
    """Procesa el analisis avanzado de la cartera.

    Returns:
        dict[str, pd.DataFrame]: Diccionario con las vistas analiticas.
    """
    reporte = cargar_reporte()
    vistas_analytics = {
        "movimientos_abiertos_cxc": reporte.get("movimientos_abiertos_cxc", pd.DataFrame()),
        "movimientos_totales_cxc": reporte.get("movimientos_totales_cxc", pd.DataFrame()),
    }
    engine = Analytics(RANGOS_ANTIGUEDAD)
    return engine.run_analytics(vistas_analytics)


@st.cache_data(ttl=3600)
def cargar_auditoria() -> Any:
    """Ejecuta las reglas de auditoria sobre los datos.

    Returns:
        Any: Objeto AuditResult con los hallazgos y resumen.
    """
    df = cargar_datos_crudos()
    reporte = cargar_reporte()
    reporte_cxc_df = reporte.get("reporte_cxc", pd.DataFrame())
    
    auditor = Auditor(ANOMALIAS)
    return auditor.run_audit(df, df_reporte=reporte_cxc_df)


# ======================================================================
# HELPERS DE FILTRADO
# ======================================================================

def get_clientes(df: pd.DataFrame) -> list[str]:
    """Devuelve lista ordenada de clientes unicos del DataFrame.

    Args:
        df: DataFrame con columna NOMBRE_CLIENTE.

    Returns:
        Lista de nombres de cliente ordenada alfabeticamente.
    """
    if "NOMBRE_CLIENTE" not in df.columns:
        return []
    return sorted(df["NOMBRE_CLIENTE"].dropna().unique().tolist())


def get_vendedores(df: pd.DataFrame) -> list[str]:
    """Devuelve lista ordenada de vendedores unicos del DataFrame.

    Args:
        df: DataFrame con columna VENDEDOR.

    Returns:
        Lista de vendedores ordenada alfabeticamente.
    """
    if "VENDEDOR" not in df.columns:
        return []
    return sorted(df["VENDEDOR"].dropna().unique().tolist())


def filtrar_por_cliente(
    df: pd.DataFrame,
    clientes: list[str],
) -> pd.DataFrame:
    """Filtra el DataFrame por lista de clientes seleccionados.

    Si la lista esta vacia devuelve el DataFrame completo.

    Args:
        df:       DataFrame con columna NOMBRE_CLIENTE.
        clientes: Lista de nombres a incluir.

    Returns:
        pd.DataFrame: DataFrame filtrado.
    """
    if not clientes:
        return df
    return df[df["NOMBRE_CLIENTE"].isin(clientes)].copy()


def filtrar_por_vendedor(
    df: pd.DataFrame,
    vendedores: list[str],
) -> pd.DataFrame:
    """Filtra el DataFrame por lista de vendedores seleccionados.

    Si la lista esta vacia devuelve el DataFrame completo.

    Args:
        df:         DataFrame con columna VENDEDOR.
        vendedores: Lista de nombres a incluir.

    Returns:
        pd.DataFrame: DataFrame filtrado.
    """
    if not vendedores:
        return df
    return df[df["VENDEDOR"].isin(vendedores)].copy()