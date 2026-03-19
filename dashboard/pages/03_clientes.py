"""Página 3: Análisis por Cliente.

Vista detallada de cada cliente: saldo, facturas vivas, historial
de movimientos, categoría de mora y evolución de la deuda.
Incluye filtros interactivos por cliente y vendedor.
"""

from __future__ import annotations

import sys
from pathlib import Path

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
# HEADER
# ======================================================================
st.markdown(
    """
    <div class="main-header">
        <h1>👥 Análisis por Cliente</h1>
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
    st.error(f"❌ Error al cargar datos: {e}")
    st.stop()

resumen_clientes   = analytics.get("resumen_por_cliente", pd.DataFrame())
resumen_vendedores = analytics.get("resumen_por_vendedor", pd.DataFrame())
morosidad_cliente  = kpis_data.get("kpis_morosidad_cliente", pd.DataFrame())
limite_credito     = kpis_data.get("kpis_limite_credito", pd.DataFrame())
facturas_vivas     = reporte_data.get("movimientos_abiertos_cxc", pd.DataFrame())
reporte_cxc        = reporte_data.get("reporte_cxc", pd.DataFrame())

# ======================================================================
# FILTROS EN SIDEBAR
# ======================================================================
with st.sidebar:
    st.markdown("### 🔎 Filtros")

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
        "Categoría de mora",
        ["Por vencer", "Mora temprana (1-30)", "Mora media (31-60)",
         "Mora alta (61-90)", "Mora crítica (>90)"],
        placeholder="Todas",
    )

    st.divider()
    solo_con_saldo = st.checkbox("Solo clientes con saldo > 0", value=True)


# ======================================================================
# APLICAR FILTROS
# ======================================================================
def _aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica los filtros del sidebar a cualquier DataFrame con NOMBRE_CLIENTE."""
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
reporte_filtrado   = _aplicar_filtros(reporte_cxc)

if solo_con_saldo and not morosidad_filtrada.empty and "SALDO_TOTAL" in morosidad_filtrada.columns:
    morosidad_filtrada = morosidad_filtrada[morosidad_filtrada["SALDO_TOTAL"] > 0]

if filtro_mora and not facturas_filtradas.empty and "CATEGORIA_MORA" in facturas_filtradas.columns:
    facturas_filtradas = facturas_filtradas[facturas_filtradas["CATEGORIA_MORA"].isin(filtro_mora)]

# ======================================================================
# SECCIÓN 1: RESUMEN EJECUTIVO DE CLIENTES
# ======================================================================
st.subheader("Resumen de Cartera por Cliente")

if not morosidad_filtrada.empty:
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Clientes con saldo", f"{len(morosidad_filtrada):,}")
    with m2:
        saldo_total = morosidad_filtrada["SALDO_TOTAL"].sum() if "SALDO_TOTAL" in morosidad_filtrada.columns else 0
        st.metric("Saldo total", f"${saldo_total:,.2f}")
    with m3:
        saldo_vencido = morosidad_filtrada["SALDO_VENCIDO"].sum() if "SALDO_VENCIDO" in morosidad_filtrada.columns else 0
        st.metric("Total vencido", f"${saldo_vencido:,.2f}")
    with m4:
        pct = (saldo_vencido / saldo_total * 100) if saldo_total > 0 else 0
        st.metric("% Vencido", f"{pct:.1f}%")

    st.divider()

    # Tabla principal de morosidad por cliente
    display_mor = morosidad_filtrada.copy()
    for col in ["SALDO_TOTAL", "SALDO_VIGENTE", "SALDO_VENCIDO"]:
        if col in display_mor.columns:
            display_mor[col] = display_mor[col].apply(lambda x: f"${x:,.2f}")
    if "PCT_VENCIDO" in display_mor.columns:
        display_mor["PCT_VENCIDO"] = display_mor["PCT_VENCIDO"].apply(lambda x: f"{x:.1f}%")

    st.dataframe(
        display_mor,
        use_container_width=True,
        hide_index=True,
        column_config={
            "NOMBRE_CLIENTE":  st.column_config.TextColumn("Cliente"),
            "SALDO_TOTAL":     st.column_config.TextColumn("Saldo Total"),
            "SALDO_VIGENTE":   st.column_config.TextColumn("Vigente"),
            "SALDO_VENCIDO":   st.column_config.TextColumn("Vencido"),
            "PCT_VENCIDO":     st.column_config.TextColumn("% Vencido"),
            "NUM_FACTURAS":    st.column_config.NumberColumn("Facturas", format="%d"),
            "NUM_VENCIDAS":    st.column_config.NumberColumn("Vencidas", format="%d"),
            "DIAS_VENCIDO_MAX":st.column_config.NumberColumn("Días Vencido Máx", format="%d"),
        },
    )

    st.divider()

# ======================================================================
# SECCIÓN 2: GRÁFICA VENCIDO VS VIGENTE POR CLIENTE (Top 15)
# ======================================================================
st.subheader("Top 15 Clientes — Vencido vs Vigente")

if not morosidad_filtrada.empty:
    cols_req = ["NOMBRE_CLIENTE", "SALDO_VIGENTE", "SALDO_VENCIDO"]
    if all(c in morosidad_filtrada.columns for c in cols_req):
        top15 = morosidad_filtrada.nlargest(15, "SALDO_TOTAL")[cols_req].copy()
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
            color_discrete_map={"Vigente": "#22c55e", "Vencido": "#ef4444"},
            labels={"NOMBRE_CLIENTE": "", "Importe": "Importe ($)"},
            barmode="stack",
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(t=20, b=20, l=150, r=20),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            legend=dict(orientation="h", y=-0.15, x=0.3),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

# ======================================================================
# SECCIÓN 3: UTILIZACIÓN DE LÍMITE DE CRÉDITO
# ======================================================================
st.subheader("Utilización de Límite de Crédito")

if not limite_credito.empty:
    lc_filtrado = _aplicar_filtros(limite_credito)

    # Semáforo de alertas por nivel
    alertas_credito = lc_filtrado["ALERTA"].value_counts() if "ALERTA" in lc_filtrado.columns else pd.Series()

    if not alertas_credito.empty:
        cols_alerta = st.columns(len(alertas_credito))
        colores_alerta = {
            "SOBRE_LIMITE": ("🚨", "alert-critico"),
            "CRITICO":      ("⚠️", "alert-warning"),
            "ALTO":         ("📊", "alert-warning"),
            "NORMAL":       ("✅", "alert-ok"),
            "SIN_LIMITE":   ("ℹ️", "alert-warning"),
        }
        for i, (nivel, cantidad) in enumerate(alertas_credito.items()):
            icono, css = colores_alerta.get(nivel, ("•", "alert-ok"))
            with cols_alerta[i]:
                st.markdown(
                    f'<div class="{css}">{icono} <strong>{nivel}</strong><br>{cantidad} clientes</div>',
                    unsafe_allow_html=True,
                )

    st.write("")

    # Tabla de utilización
    display_lc = lc_filtrado.copy()
    for col in ["SALDO", "LIMITE_CREDITO", "DISPONIBLE"]:
        if col in display_lc.columns:
            display_lc[col] = display_lc[col].apply(lambda x: f"${x:,.2f}")
    if "UTILIZACION_PCT" in display_lc.columns:
        display_lc["UTILIZACION_PCT"] = display_lc["UTILIZACION_PCT"].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A"
        )

    st.dataframe(
        display_lc,
        use_container_width=True,
        hide_index=True,
        column_config={
            "NOMBRE_CLIENTE":  st.column_config.TextColumn("Cliente"),
            "SALDO":           st.column_config.TextColumn("Saldo Actual"),
            "LIMITE_CREDITO":  st.column_config.TextColumn("Límite de Crédito"),
            "UTILIZACION_PCT": st.column_config.TextColumn("Utilización"),
            "DISPONIBLE":      st.column_config.TextColumn("Disponible"),
            "ALERTA":          st.column_config.TextColumn("Nivel"),
        },
    )
    st.divider()

else:
    st.info("💡 Para ver utilización de crédito, agrega `CLIENTES.LIMITE_CREDITO` al query SQL maestro.")
    st.divider()

# ======================================================================
# SECCIÓN 4: FACTURAS VIVAS CON FILTROS
# ======================================================================
st.subheader("Facturas con Saldo Pendiente")

if not facturas_filtradas.empty:
    # Solo mostrar cargos (no sus abonos parciales) para el conteo
    cargos_vivos = facturas_filtradas[facturas_filtradas["TIPO_IMPTE"] == "C"] if "TIPO_IMPTE" in facturas_filtradas.columns else facturas_filtradas

    st.caption(f"{len(cargos_vivos):,} facturas abiertas — {facturas_filtradas['NOMBRE_CLIENTE'].nunique() if 'NOMBRE_CLIENTE' in facturas_filtradas.columns else 0} clientes")

    cols_mostrar = [
        "NOMBRE_CLIENTE", "FOLIO", "FECHA_EMISION", "FECHA_VENCIMIENTO",
        "CONCEPTO", "IMPORTE", "SALDO_FACTURA", "DELTA_MORA", "CATEGORIA_MORA",
    ]
    cols_disponibles = [c for c in cols_mostrar if c in facturas_filtradas.columns]
    display_fv = facturas_filtradas[cols_disponibles].copy()

    for col in ["IMPORTE", "SALDO_FACTURA"]:
        if col in display_fv.columns:
            display_fv[col] = display_fv[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")

    st.dataframe(
        display_fv,
        use_container_width=True,
        hide_index=True,
        column_config={
            "NOMBRE_CLIENTE":    st.column_config.TextColumn("Cliente"),
            "FOLIO":             st.column_config.TextColumn("Folio"),
            "FECHA_EMISION":     st.column_config.DateColumn("Emisión", format="DD/MM/YYYY"),
            "FECHA_VENCIMIENTO": st.column_config.DateColumn("Vencimiento", format="DD/MM/YYYY"),
            "CONCEPTO":          st.column_config.TextColumn("Concepto"),
            "IMPORTE":           st.column_config.TextColumn("Importe"),
            "SALDO_FACTURA":     st.column_config.TextColumn("Saldo"),
            "DELTA_MORA":        st.column_config.NumberColumn("Días Mora", format="%d"),
            "CATEGORIA_MORA":    st.column_config.TextColumn("Categoría"),
        },
    )
else:
    st.success("✅ No hay facturas con saldo pendiente con los filtros actuales.")

# ======================================================================
# SECCIÓN 5: DISTRIBUCIÓN POR VENDEDOR
# ======================================================================
if not resumen_vendedores.empty:
    st.divider()
    st.subheader("Cartera por Vendedor")
    
    # CORRECCIÓN APLICADA: Uso de SALDO_PENDIENTE en lugar de IMPORTE_TOTAL
    fig_vend = px.bar(
        resumen_vendedores.head(10),
        x="VENDEDOR",
        y="SALDO_PENDIENTE",
        color="SALDO_PENDIENTE",
        color_continuous_scale="Blues",
        text_auto=".2s",
        labels={"VENDEDOR": "Vendedor", "SALDO_PENDIENTE": "Saldo Pendiente ($)"},
    )
    fig_vend.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=20, b=60, l=10, r=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
    )
    st.plotly_chart(fig_vend, use_container_width=True)