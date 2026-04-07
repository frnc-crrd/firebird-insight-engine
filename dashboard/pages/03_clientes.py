"""Pagina 3: Analisis por Cliente.

Vista detallada de cada cliente: saldo, facturas vivas, historial
de movimientos, categoria de mora y evolucion de la deuda.
Incluye filtros interactivos por cliente y vendedor.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.data_loader import (
    cargar_analytics,
    cargar_kpis,
    cargar_reporte,
    get_clientes,
    get_vendedores,
)

# ======================================================================
# INICIALIZACION DE ESTADO GLOBAL (MONEDA)
# ======================================================================
if "moneda" not in st.session_state:
    st.session_state.moneda = "MXN"

with st.sidebar:
    st.markdown("### Configuracion Global")
    st.radio("Moneda de Analisis", ["MXN", "USD"], horizontal=True, key="moneda")
    st.divider()

moneda_actual = st.session_state.moneda
sufijo = moneda_actual.lower()

# ======================================================================
# HEADER
# ======================================================================
st.markdown(
    f"""
    <div class="main-header">
        <h1>Analisis por Cliente ({moneda_actual})</h1>
        <p>Detalle de saldos, morosidad y facturas pendientes por cliente</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================================
# CARGA DE DATOS
# ======================================================================
try:
    analytics    = cargar_analytics()
    kpis_data    = cargar_kpis()
    reporte_data = cargar_reporte()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# Extraccion dinamica, con fallback al esquema genérico si no existe
resumen_clientes   = analytics.get(f"resumen_por_cliente_{sufijo}", analytics.get("resumen_por_cliente", pd.DataFrame()))
resumen_vendedores = analytics.get(f"resumen_por_vendedor_{sufijo}", analytics.get("resumen_por_vendedor", pd.DataFrame()))
morosidad_cliente  = kpis_data.get(f"kpis_morosidad_cliente_{sufijo}", pd.DataFrame())
limite_credito     = kpis_data.get(f"kpis_limite_credito_{sufijo}", pd.DataFrame())
facturas_vivas     = reporte_data.get("movimientos_abiertos_cxc", pd.DataFrame())

# Limpieza quirurgica: Eliminar filas sumatorias "TOTAL"
if not resumen_clientes.empty and "NOMBRE_CLIENTE" in resumen_clientes.columns:
    resumen_clientes = resumen_clientes[resumen_clientes["NOMBRE_CLIENTE"] != "TOTAL"].copy()
if not morosidad_cliente.empty and "NOMBRE_CLIENTE" in morosidad_cliente.columns:
    morosidad_cliente = morosidad_cliente[morosidad_cliente["NOMBRE_CLIENTE"] != "TOTAL"].copy()
if not resumen_vendedores.empty and "VENDEDOR" in resumen_vendedores.columns:
    resumen_vendedores = resumen_vendedores[resumen_vendedores["VENDEDOR"] != "TOTAL"].copy()
if not limite_credito.empty and "NOMBRE_CLIENTE" in limite_credito.columns:
    limite_credito = limite_credito[limite_credito["NOMBRE_CLIENTE"] != "TOTAL"].copy()

# ======================================================================
# FILTROS EN SIDEBAR
# ======================================================================
with st.sidebar:
    st.markdown("### Filtros")

    clientes_disponibles = get_clientes(resumen_clientes)
    vendedores_disponibles = get_vendedores(resumen_vendedores)

    filtro_vendedor = st.selectbox(
        "Vendedor",
        ["Todos"] + vendedores_disponibles,
        index=0,
    )

    filtro_cliente = st.multiselect(
        "Cliente(s)",
        clientes_disponibles,
        placeholder="Todos los clientes",
    )

    filtro_mora = st.multiselect(
        "Categoria de mora",
        ["Por vencer", "Mora temprana (1-30)", "Mora media (31-60)",
         "Mora alta (61-90)", "Mora critica (>90)"],
        placeholder="Todas",
    )

    st.divider()
    solo_con_saldo = st.checkbox("Solo clientes con saldo > 0", value=True)

# ======================================================================
# APLICAR FILTROS
# ======================================================================
def _aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    resultado = df.copy()

    if filtro_cliente and "NOMBRE_CLIENTE" in resultado.columns:
        resultado = resultado[resultado["NOMBRE_CLIENTE"].isin(filtro_cliente)]

    if filtro_vendedor != "Todos" and "VENDEDOR" in resultado.columns:
        resultado = resultado[resultado["VENDEDOR"] == filtro_vendedor]

    return resultado

morosidad_filtrada = _aplicar_filtros(morosidad_cliente)
facturas_filtradas = _aplicar_filtros(facturas_vivas)

# Saneamiento de MONEDA en la tabla cruda si el selector de moneda está activo
if not facturas_filtradas.empty and "MONEDA" in facturas_filtradas.columns:
    if moneda_actual == "MXN":
        facturas_filtradas = facturas_filtradas[facturas_filtradas["MONEDA"] == "Moneda Nacional"]
    else:
        facturas_filtradas = facturas_filtradas[facturas_filtradas["MONEDA"] != "Moneda Nacional"]

if solo_con_saldo and not morosidad_filtrada.empty and "SALDO_PENDIENTE" in morosidad_filtrada.columns:
    morosidad_filtrada = morosidad_filtrada[morosidad_filtrada["SALDO_PENDIENTE"] > 0]

if filtro_mora and not facturas_filtradas.empty and "CATEGORIA_MORA" in facturas_filtradas.columns:
    facturas_filtradas = facturas_filtradas[facturas_filtradas["CATEGORIA_MORA"].isin(filtro_mora)]

# ======================================================================
# SANITIZACION DE DATOS
# ======================================================================
def _formatear_porcentaje(x: Any) -> str:
    try:
        if pd.isna(x) or str(x).strip() == "":
            return "0.0%"
        val = str(x).replace('%', '').strip()
        return f"{float(val):.1f}%"
    except (ValueError, TypeError):
        return str(x)

def _formatear_moneda_seguro(x: Any) -> str:
    try:
        if pd.isna(x) or str(x).strip() == "":
            return "$0.00"
        val_str = str(x).replace('$', '').replace(',', '').strip()
        return f"${float(val_str):,.2f}"
    except (ValueError, TypeError):
        return str(x)

# ======================================================================
# SECCION 1: RESUMEN EJECUTIVO DE CLIENTES
# ======================================================================
st.subheader("Resumen de Cartera por Cliente")

if not morosidad_filtrada.empty:
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Clientes con saldo", f"{len(morosidad_filtrada):,}")
    with m2:
        saldo_total = morosidad_filtrada["SALDO_PENDIENTE"].sum() if "SALDO_PENDIENTE" in morosidad_filtrada.columns else 0
        st.metric("Saldo total", f"${saldo_total:,.2f}")
    with m3:
        saldo_vencido = morosidad_filtrada["SALDO_VENCIDO"].sum() if "SALDO_VENCIDO" in morosidad_filtrada.columns else 0
        st.metric("Total vencido", f"${saldo_vencido:,.2f}")
    with m4:
        pct = (saldo_vencido / saldo_total * 100) if saldo_total > 0 else 0
        st.metric("% Vencido", f"{pct:.1f}%")

    st.divider()

    display_mor = morosidad_filtrada.copy()
    
    if "DIAS_VENCIDO_MAX" in display_mor.columns:
        display_mor["DIAS_VENCIDO_MAX"] = pd.to_numeric(display_mor["DIAS_VENCIDO_MAX"], errors="coerce").fillna(0).astype(int)
    if "NUM_FACTURAS" in display_mor.columns:
        display_mor["NUM_FACTURAS"] = pd.to_numeric(display_mor["NUM_FACTURAS"], errors="coerce").fillna(0).astype(int)
    if "NUM_VENCIDAS" in display_mor.columns:
        display_mor["NUM_VENCIDAS"] = pd.to_numeric(display_mor["NUM_VENCIDAS"], errors="coerce").fillna(0).astype(int)

    for col in ["SALDO_PENDIENTE", "SALDO_VIGENTE", "SALDO_VENCIDO"]:
        if col in display_mor.columns:
            display_mor[col] = display_mor[col].apply(_formatear_moneda_seguro)
    
    if "PCT_VENCIDO" in display_mor.columns:
        display_mor["PCT_VENCIDO"] = display_mor["PCT_VENCIDO"].apply(_formatear_porcentaje)

    st.dataframe(
        display_mor,
        width="stretch",
        hide_index=True,
        column_config={
            "NOMBRE_CLIENTE":  st.column_config.TextColumn("Cliente"),
            "SALDO_PENDIENTE": st.column_config.TextColumn("Saldo Total"),
            "SALDO_VIGENTE":   st.column_config.TextColumn("Vigente"),
            "SALDO_VENCIDO":   st.column_config.TextColumn("Vencido"),
            "PCT_VENCIDO":     st.column_config.TextColumn("% Vencido"),
            "NUM_FACTURAS":    st.column_config.NumberColumn("Facturas", format="%d"),
            "NUM_VENCIDAS":    st.column_config.NumberColumn("Vencidas", format="%d"),
            "DIAS_VENCIDO_MAX":st.column_config.NumberColumn("Dias Vencido Max", format="%d"),
        },
    )

    st.divider()

# ======================================================================
# SECCION 2: GRAFICA VENCIDO VS VIGENTE POR CLIENTE (Top 15)
# ======================================================================
st.subheader("Top 15 Clientes - Vencido vs Vigente")

if not morosidad_filtrada.empty:
    cols_req = ["NOMBRE_CLIENTE", "SALDO_VIGENTE", "SALDO_VENCIDO"]
    if all(c in morosidad_filtrada.columns for c in cols_req):
        top15 = morosidad_filtrada.nlargest(15, "SALDO_PENDIENTE")[cols_req].copy()
        
        for col in ["SALDO_VIGENTE", "SALDO_VENCIDO"]:
            top15[col] = pd.to_numeric(top15[col], errors='coerce').fillna(0)
            
        top15_melted = top15.melt(
            id_vars="NOMBRE_CLIENTE",
            value_vars=["SALDO_VIGENTE", "SALDO_VENCIDO"],
            var_name="Tipo",
            value_name="Importe",
        )
        top15_melted["Tipo"] = top15_melted["Tipo"].map({
            "SALDO_VIGENTE": "Vigente",
            "SALDO_VENCIDO": "Vencido",
        })

        fig = px.bar(
            top15_melted,
            x="Importe",
            y="NOMBRE_CLIENTE",
            color="Tipo",
            orientation="h",
            color_discrete_map={"Vigente": "#16a34a", "Vencido": "#dc2626"},
            labels={"NOMBRE_CLIENTE": "", "Importe": f"Importe ({moneda_actual})"},
            barmode="stack",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20, l=150, r=20),
            yaxis=dict(autorange="reversed", tickfont=dict(color="#334155")),
            xaxis=dict(showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#334155"), title_font=dict(color="#334155")),
            legend=dict(orientation="h", y=-0.15, x=0.3, font=dict(color="#334155")),
        )
        st.plotly_chart(fig, width="stretch")

    st.divider()

# ======================================================================
# SECCION 3: UTILIZACION DE LIMITE DE CREDITO
# ======================================================================
st.subheader("Utilizacion de Limite de Credito")

if not limite_credito.empty:
    lc_filtrado = _aplicar_filtros(limite_credito)

    alertas_credito = lc_filtrado["ALERTA"].value_counts() if "ALERTA" in lc_filtrado.columns else pd.Series()

    if not alertas_credito.empty:
        cols_alerta = st.columns(len(alertas_credito))
        colores_alerta = {
            "SOBRE_LIMITE": ("alert-critico"),
            "CRITICO":      ("alert-warning"),
            "ALTO":         ("alert-warning"),
            "NORMAL":       ("alert-ok"),
            "SIN_LIMITE":   ("alert-warning"),
        }
        for i, (nivel, cantidad) in enumerate(alertas_credito.items()):
            css = colores_alerta.get(nivel, "alert-ok")
            with cols_alerta[i]:
                st.markdown(
                    f'<div class="{css}"><strong>{nivel}</strong><br>{cantidad} clientes</div>',
                    unsafe_allow_html=True,
                )

    st.write("")

    display_lc = lc_filtrado.copy()
    for col in ["SALDO", "LIMITE_CREDITO", "DISPONIBLE"]:
        if col in display_lc.columns:
            display_lc[col] = display_lc[col].apply(_formatear_moneda_seguro)
            
    if "UTILIZACION_PCT" in display_lc.columns:
        display_lc["UTILIZACION_PCT"] = display_lc["UTILIZACION_PCT"].apply(_formatear_porcentaje)

    st.dataframe(
        display_lc,
        width="stretch",
        hide_index=True,
        column_config={
            "NOMBRE_CLIENTE":  st.column_config.TextColumn("Cliente"),
            "SALDO":           st.column_config.TextColumn("Saldo Actual"),
            "LIMITE_CREDITO":  st.column_config.TextColumn("Limite de Credito"),
            "UTILIZACION_PCT": st.column_config.TextColumn("Utilizacion"),
            "DISPONIBLE":      st.column_config.TextColumn("Disponible"),
            "ALERTA":          st.column_config.TextColumn("Nivel"),
        },
    )
    st.divider()
else:
    st.info("Para ver utilizacion de credito, agregue CLIENTES.LIMITE_CREDITO al query SQL maestro.")
    st.divider()

# ======================================================================
# SECCION 4: FACTURAS VIVAS CON FILTROS
# ======================================================================
st.subheader("Facturas con Saldo Pendiente")

if not facturas_filtradas.empty:
    cargos_vivos = facturas_filtradas[facturas_filtradas["TIPO_IMPTE"] == "C"] if "TIPO_IMPTE" in facturas_filtradas.columns else facturas_filtradas

    st.caption(f"{len(cargos_vivos):,} facturas abiertas - {facturas_filtradas['NOMBRE_CLIENTE'].nunique() if 'NOMBRE_CLIENTE' in facturas_filtradas.columns else 0} clientes")

    cols_mostrar = [
        "NOMBRE_CLIENTE", "FOLIO", "FECHA_EMISION", "FECHA_VENCIMIENTO",
        "CONCEPTO", "IMPORTE", "SALDO_FACTURA", "DELTA_MORA", "CATEGORIA_MORA",
    ]
    cols_disponibles = [c for c in cols_mostrar if c in facturas_filtradas.columns]
    display_fv = facturas_filtradas[cols_disponibles].copy()

    for col in ["IMPORTE", "SALDO_FACTURA"]:
        if col in display_fv.columns:
            display_fv[col] = display_fv[col].apply(_formatear_moneda_seguro)

    st.dataframe(
        display_fv,
        width="stretch",
        hide_index=True,
        column_config={
            "NOMBRE_CLIENTE":    st.column_config.TextColumn("Cliente"),
            "FOLIO":             st.column_config.TextColumn("Folio"),
            "FECHA_EMISION":     st.column_config.DateColumn("Emision", format="DD/MM/YYYY"),
            "FECHA_VENCIMIENTO": st.column_config.DateColumn("Vencimiento", format="DD/MM/YYYY"),
            "CONCEPTO":          st.column_config.TextColumn("Concepto"),
            "IMPORTE":           st.column_config.TextColumn("Importe"),
            "SALDO_FACTURA":     st.column_config.TextColumn("Saldo"),
            "DELTA_MORA":        st.column_config.NumberColumn("Dias Mora", format="%d"),
            "CATEGORIA_MORA":    st.column_config.TextColumn("Categoria"),
        },
    )
else:
    st.info("No hay facturas con saldo pendiente con los filtros actuales.")

# ======================================================================
# SECCION 5: DISTRIBUCION POR VENDEDOR
# ======================================================================
if not resumen_vendedores.empty:
    st.divider()
    st.subheader("Cartera por Vendedor")
    
    vend_df = resumen_vendedores.head(10).copy()
    if "SALDO_PENDIENTE" in vend_df.columns:
        vend_df["SALDO_PENDIENTE"] = pd.to_numeric(vend_df["SALDO_PENDIENTE"], errors='coerce').fillna(0)
    
    fig_vend = px.bar(
        vend_df,
        x="VENDEDOR",
        y="SALDO_PENDIENTE",
        color="SALDO_PENDIENTE",
        color_continuous_scale="Blues",
        text_auto=".2s",
        labels={"VENDEDOR": "Vendedor", "SALDO_PENDIENTE": f"Saldo Pendiente ({moneda_actual})"},
    )
    fig_vend.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=60, l=10, r=10),
        xaxis=dict(showgrid=False, tickfont=dict(color="#334155"), title_font=dict(color="#334155")),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#334155"), title_font=dict(color="#334155")),
    )
    st.plotly_chart(fig_vend, width="stretch")