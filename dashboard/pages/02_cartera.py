# dashboard/pages/02_cartera.py
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
# HEADER
# ======================================================================
st.markdown(
    """
    <div class="main-header">
        <h1>Cartera y Antiguedad</h1>
        <p>Distribucion de la cartera por rangos de tiempo y analisis de vencimientos</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================================
# CARGA DE DATOS
# ======================================================================
try:
    analytics = cargar_analytics()
except Exception as e:
    st.error(f"[ERROR] al cargar datos: {e}")
    st.stop()

antiguedad      = analytics.get("antiguedad_cartera", pd.DataFrame())
por_cliente     = analytics.get("antiguedad_por_cliente", pd.DataFrame())
vencida_vigente = analytics.get("cartera_vencida_vs_vigente", pd.DataFrame())
resumen_cliente = analytics.get("resumen_por_cliente", pd.DataFrame())
tendencia_mxn   = analytics.get("tendencia_mensual", pd.DataFrame())

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
        # Cartera vencida = todo excepto "Vigente"
        vencida = antiguedad[antiguedad["RANGO_ANTIGUEDAD"] != "Vigente"]["SALDO_PENDIENTE"].sum()
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
    st.subheader("Importe por Rango de Antiguedad")
    if not antiguedad.empty:
        colores = {
            "Vigente":          "#22c55e",
            "0-30 dias":        "#3b82f6",
            "31-60 dias":       "#f59e0b",
            "61-90 dias":       "#f97316",
            "91-120 dias":      "#ef4444",
            "Mas de 120 dias":  "#7f1d1d",
            "Sin fecha":        "#94a3b8",
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
            texttemplate="%{text:.1f}%",
            textposition="outside",
        )
        fig.update_layout(
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(t=20, b=40, l=10, r=10),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Importe ($)"),
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
            paper_bgcolor="white",
            legend=dict(orientation="v", x=1.0, y=0.5),
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
        display_ant["PCT_DEL_TOTAL"] = display_ant["PCT_DEL_TOTAL"].apply(lambda x: f"{x:.2f}%")

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
            dias_p  = row.get("DIAS_VENCIDO_PROMEDIO", 0)

            if estatus == "VENCIDO":
                css = "alert-critico"
                icono = "[CRITICO]"
            else:
                css = "alert-ok"
                icono = "[OK]"

            st.markdown(
                f'<div class="{css}">'
                f'{icono} <strong>{estatus}</strong><br>'
                f'Importe: <strong>${importe:,.2f}</strong> ({pct:.1f}%)<br>'
                f'Documentos: {int(ndocs):,} | '
                f'Dias vencido prom.: {dias_p:.0f}'
                f'</div>',
                unsafe_allow_html=True,
            )

    with vv_col2:
        fig_vv = px.bar(
            vencida_vigente,
            x="ESTATUS_VENCIMIENTO",
            y="SALDO_PENDIENTE",
            color="ESTATUS_VENCIMIENTO",
            color_discrete_map={"VENCIDO": "#ef4444", "VIGENTE": "#22c55e"},
            text="SALDO_PENDIENTE",
            labels={"SALDO_PENDIENTE": "Importe ($)", "ESTATUS_VENCIMIENTO": ""},
        )
        fig_vv.update_traces(
            texttemplate="$%{text:,.0f}",
            textposition="outside",
        )
        fig_vv.update_layout(
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(t=40, b=20, l=10, r=10),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig_vv, width="stretch")

st.divider()

# ======================================================================
# SECCION 5: PIVOTE POR CLIENTE
# ======================================================================
st.subheader("Antiguedad Desglosada por Cliente")

if not por_cliente.empty:
    # Filtro de busqueda
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
    st.info("Sin datos de antiguedad por cliente disponibles.")

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
            color_discrete_map={"COBRADAS": "#22c55e", "PENDIENTES": "#f97316"},
            text="NUM_FACTURAS",
            labels={"NUM_FACTURAS": "Cantidad", "PERIODO": "Periodo (Ano-Mes)", "ESTADO": "Estado"}
        )
        fig_bar.update_traces(textposition="inside", textfont_size=11)
        fig_bar.update_layout(
            title="Comparacion Mensual: Cobradas vs. Pendientes",
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
            xaxis=dict(showgrid=False, tickangle=-45),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
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
                colorbar=dict(title="Facturas<br>Pendientes")
            ))
            fig_cal.update_layout(
                title="Mapa de Calor: Facturas Pendientes",
                yaxis=dict(autorange="reversed", title="Ano"),
                xaxis=dict(title="", side="top"),
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=50, b=20, l=10, r=10)
            )
            st.plotly_chart(fig_cal, width="stretch")
        else:
            st.success("No hay facturas pendientes en el historial analizado.")
else:
    st.info("Sin datos de tendencia historica disponibles.")