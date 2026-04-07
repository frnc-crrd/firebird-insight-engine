"""Pagina 2: Cartera y Antiguedad.

Analisis detallado de la composicion de la cartera por rangos de
antiguedad, tabla pivote por cliente y comparativa de cartera
vencida vs vigente con metricas de dias.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.data_loader import cargar_analytics

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
        <h1>Cartera y Antiguedad ({moneda_actual})</h1>
        <p>Distribucion de la cartera por rangos de tiempo y analisis de vencimientos</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================================
# CARGA DE DATOS Y LIMPIEZA
# ======================================================================
try:
    analytics = cargar_analytics()
except Exception as e:
    st.error(f"[ERROR] al cargar datos: {e}")
    st.stop()

# Extraccion dinamica por moneda
antiguedad      = analytics.get(f"antiguedad_cartera_{sufijo}", pd.DataFrame())
por_cliente     = analytics.get(f"antiguedad_por_cliente_{sufijo}", pd.DataFrame())
vencida_vigente = analytics.get(f"cartera_vencida_vs_vigente_{sufijo}", pd.DataFrame())
tendencia_mxn   = analytics.get(f"tendencia_mensual_{sufijo}", pd.DataFrame())

# Limpieza quirurgica: Eliminar filas "TOTAL" para evitar duplicacion de saldos
if not antiguedad.empty and "RANGO_ANTIGUEDAD" in antiguedad.columns:
    antiguedad = antiguedad[antiguedad["RANGO_ANTIGUEDAD"] != "TOTAL"].copy()

if not por_cliente.empty and "NOMBRE_CLIENTE" in por_cliente.columns:
    por_cliente = por_cliente[por_cliente["NOMBRE_CLIENTE"] != "TOTAL"].copy()

if not vencida_vigente.empty and "ESTATUS_VENCIMIENTO" in vencida_vigente.columns:
    vencida_vigente = vencida_vigente[vencida_vigente["ESTATUS_VENCIMIENTO"] != "TOTAL"].copy()

# ======================================================================
# SECCION 1: METRICAS DE ANTIGUEDAD
# ======================================================================
st.subheader("Resumen Global de Antiguedad")

if not antiguedad.empty:
    total_cartera = antiguedad["SALDO_PENDIENTE"].sum()
    n_documentos  = int(antiguedad["NUM_FACTURAS_PENDIENTES"].sum())

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Cartera", f"${total_cartera:,.2f}")
    with m2:
        st.metric("Total Documentos", f"{n_documentos:,}")
    with m3:
        vencida = antiguedad[~antiguedad["RANGO_ANTIGUEDAD"].str.contains("VIGENTE", case=False, na=False)]["SALDO_PENDIENTE"].sum()
        st.metric("Total Vencido", f"${vencida:,.2f}")
    with m4:
        pct_vencido = (vencida / total_cartera * 100) if total_cartera > 0 else 0
        st.metric("% Vencido", f"{pct_vencido:.1f}%")

    st.divider()

# ======================================================================
# SECCION 2: GRAFICAS DE ANTIGUEDAD
# ======================================================================
graf_col1, graf_col2 = st.columns(2)

with graf_col1:
    st.subheader(f"Importe por Rango de Antiguedad ({moneda_actual})")
    if not antiguedad.empty:
        colores = {
            "VIGENTE: MÁS DE 1 DÍA": "#16a34a",
            "VIGENTE: VENCE MAÑANA": "#22c55e",
            "VIGENTE: VENCE HOY":    "#84cc16",
            "VENCIDO: 1-30 DÍAS":    "#3b82f6",
            "VENCIDO: 31-60 DÍAS":   "#f59e0b",
            "VENCIDO: 61-90 DÍAS":   "#ea580c",
            "VENCIDO: 91-120 DÍAS":  "#dc2626",
            "VENCIDO: MÁS DE 120 DÍAS": "#991b1b",
        }
        
        fig = px.bar(
            antiguedad,
            x="RANGO_ANTIGUEDAD",
            y="SALDO_PENDIENTE",
            color="RANGO_ANTIGUEDAD",
            color_discrete_map=colores,
            text="PCT_DEL_TOTAL",
            labels={"SALDO_PENDIENTE": "Importe ($)", "RANGO_ANTIGUEDAD": "Rango"},
        )
        fig.update_traces(
            texttemplate="%{text:.1%}",
            textposition="outside",
            textfont=dict(color="#334155")
        )
        fig.update_layout(
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=40, l=10, r=10),
            xaxis=dict(showgrid=False, title="", tickfont=dict(color="#334155")),
            yaxis=dict(showgrid=True, gridcolor="#e2e8f0", title="Importe ($)", tickfont=dict(color="#334155"), title_font=dict(color="#334155")),
        )
        st.plotly_chart(fig, width="stretch")

with graf_col2:
    st.subheader("Numero de Documentos por Rango")
    if not antiguedad.empty:
        fig2 = px.pie(
            antiguedad,
            names="RANGO_ANTIGUEDAD",
            values="NUM_FACTURAS_PENDIENTES",
            hole=0.4,
            color="RANGO_ANTIGUEDAD",
            color_discrete_map=colores,
        )
        fig2.update_layout(
            margin=dict(t=20, b=40, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="v", x=1.0, y=0.5, font=dict(color="#334155")),
        )
        fig2.update_traces(textinfo="percent+label", textfont_size=11)
        st.plotly_chart(fig2, width="stretch")

st.divider()

# ======================================================================
# SECCION 3: TABLA DE ANTIGUEDAD DETALLADA
# ======================================================================
st.subheader("Detalle por Rango de Antiguedad")

if not antiguedad.empty:
    display_ant = antiguedad.copy()

    for col in ["SALDO_PENDIENTE"]:
        if col in display_ant.columns:
            display_ant[col] = display_ant[col].apply(lambda x: f"${float(x):,.2f}")

    if "PCT_DEL_TOTAL" in display_ant.columns:
        display_ant["PCT_DEL_TOTAL"] = display_ant["PCT_DEL_TOTAL"].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, float) else str(x))

    st.dataframe(
        display_ant,
        width="stretch",
        hide_index=True,
        column_config={
            "RANGO_ANTIGUEDAD":        st.column_config.TextColumn("Rango"),
            "NUM_FACTURAS_PENDIENTES": st.column_config.NumberColumn("Documentos", format="%d"),
            "SALDO_PENDIENTE":         st.column_config.TextColumn("Importe Total"),
            "PCT_DEL_TOTAL":           st.column_config.TextColumn("% del Total"),
        },
    )

st.divider()

# ======================================================================
# SECCION 4: VENCIDA VS VIGENTE
# ======================================================================
st.subheader("Cartera Vencida vs Vigente")

if not vencida_vigente.empty:
    vv_col1, vv_col2 = st.columns([1, 1.5])

    with vv_col1:
        for _, row in vencida_vigente.iterrows():
            estatus = row.get("ESTATUS_VENCIMIENTO", "")
            importe = row.get("SALDO_PENDIENTE", 0)
            pct     = row.get("PCT_DEL_TOTAL", 0)
            ndocs   = row.get("NUM_FACTURAS_PENDIENTES", 0)
            
            if "VENCIDA" in str(estatus).upper():
                css = "alert-critico"
            else:
                css = "alert-ok"

            st.markdown(
                f'<div class="{css}">'
                f'<strong>{estatus}</strong><br>'
                f'Importe: <strong>${importe:,.2f}</strong> ({pct * 100:.1f}%)<br>'
                f'Documentos: {int(ndocs):,}'
                f'</div>',
                unsafe_allow_html=True,
            )

    with vv_col2:
        fig_vv = px.bar(
            vencida_vigente,
            x="ESTATUS_VENCIMIENTO",
            y="SALDO_PENDIENTE",
            color="ESTATUS_VENCIMIENTO",
            color_discrete_map={"FACTURAS VENCIDAS": "#dc2626", "FACTURAS VIGENTES": "#16a34a"},
            text="SALDO_PENDIENTE",
            labels={"SALDO_PENDIENTE": "Importe ($)", "ESTATUS_VENCIMIENTO": ""},
        )
        fig_vv.update_traces(
            texttemplate="$%{text:,.0f}",
            textposition="outside",
            textfont=dict(color="#334155")
        )
        fig_vv.update_layout(
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=40, b=20, l=10, r=10),
            yaxis=dict(showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#334155")),
            xaxis=dict(showgrid=False, tickfont=dict(color="#334155")),
        )
        st.plotly_chart(fig_vv, width="stretch")

st.divider()

# ======================================================================
# SECCION 5: PIVOTE POR CLIENTE
# ======================================================================
st.subheader("Antiguedad Desglosada por Cliente")

if not por_cliente.empty:
    busqueda = st.text_input("Buscar cliente", placeholder="Escribe parte del nombre...")

    df_pivote = por_cliente.copy()
    if busqueda:
        df_pivote = df_pivote[
            df_pivote["NOMBRE_CLIENTE"].str.contains(busqueda, case=False, na=False)
        ]

    st.dataframe(
        df_pivote,
        width="stretch",
        hide_index=True,
    )
    st.caption(f"Mostrando {len(df_pivote):,} de {len(por_cliente):,} clientes")
else:
    st.info("Sin datos de antiguedad por cliente disponibles en esta moneda.")

st.divider()

# ======================================================================
# SECCION 6: TENDENCIA HISTORICA (Cobradas vs Pendientes)
# ======================================================================
st.subheader("Evolucion Historica de Facturacion")

if not tendencia_mxn.empty:
    tend_col1, tend_col2 = st.columns([1.2, 1])

    with tend_col1:
        tendencia_mxn["PERIODO"] = tendencia_mxn["ANIO"].astype(str) + "-" + tendencia_mxn["MES"].astype(str).str.zfill(2)
        fig_bar = px.bar(
            tendencia_mxn,
            x="PERIODO",
            y="NUM_FACTURAS",
            color="ESTADO",
            barmode="stack",
            color_discrete_map={"COBRADAS": "#16a34a", "PENDIENTES": "#f97316"},
            text="NUM_FACTURAS",
            labels={"NUM_FACTURAS": "Cantidad", "PERIODO": "Periodo", "ESTADO": "Estado"}
        )
        fig_bar.update_traces(textposition="inside", textfont_size=11)
        fig_bar.update_layout(
            title=dict(text="Comparacion Mensual: Cobradas vs. Pendientes", font=dict(color="#334155")),
            plot_bgcolor="rgba(0,0,0,0)", 
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(color="#334155")),
            xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(color="#334155")),
            yaxis=dict(showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#334155"), title_font=dict(color="#334155")),
            margin=dict(t=50, b=20, l=10, r=10)
        )
        st.plotly_chart(fig_bar, width="stretch")

    with tend_col2:
        df_heatmap = tendencia_mxn[tendencia_mxn["ESTADO"] == "PENDIENTES"].copy()
        if not df_heatmap.empty:
            matriz = df_heatmap.pivot_table(
                index="ANIO", 
                columns="MES", 
                values="NUM_FACTURAS", 
                aggfunc="sum", 
                fill_value=0
            )
            for m in range(1, 13):
                if m not in matriz.columns:
                    matriz[m] = 0
            matriz = matriz[list(range(1, 13))]
            meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            
            fig_cal = go.Figure(data=go.Heatmap(
                z=matriz.values,
                x=meses_nombres,
                y=matriz.index.astype(str),
                colorscale="Blues",
                text=matriz.values,
                texttemplate="%{text}",
                showscale=True,
                colorbar=dict(title="Facturas<br>Pendientes", tickfont=dict(color="#334155"), title_font=dict(color="#334155"))
            ))
            fig_cal.update_layout(
                title=dict(text="Mapa de Calor: Facturas Pendientes", font=dict(color="#334155")),
                yaxis=dict(autorange="reversed", title="Ano", tickfont=dict(color="#334155"), title_font=dict(color="#334155")),
                xaxis=dict(title="", side="top", tickfont=dict(color="#334155")),
                plot_bgcolor="rgba(0,0,0,0)", 
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=50, b=20, l=10, r=10)
            )
            st.plotly_chart(fig_cal, width="stretch")
        else:
            st.success("No hay facturas pendientes en el historial analizado.")
else:
    st.info("Sin datos de tendencia historica disponibles en esta moneda.")