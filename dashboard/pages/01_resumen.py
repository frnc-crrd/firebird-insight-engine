# dashboard/pages/01_resumen.py
"""Pagina 1: Resumen Ejecutivo.

Vista de alto nivel pensada para direccion: KPIs principales en tarjetas
grandes, semaforo de alertas, grafica de composicion de cartera y
tabla de los 10 clientes con mayor saldo pendiente.
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

from dashboard.data_loader import cargar_analytics, cargar_kpis, cargar_reporte

# ======================================================================
# HEADER
# ======================================================================
st.markdown(
    """
    <div class="main-header">
        <h1>Resumen Ejecutivo - Cuentas por Cobrar</h1>
        <p>Vision global del estado de la cartera y principales indicadores de cobranza</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================================
# CARGA DE DATOS
# ======================================================================
try:
    kpis_data     = cargar_kpis()
    analytics     = cargar_analytics()
    reporte_data  = cargar_reporte()
except Exception as e:
    st.error(f"[ERROR] al cargar datos: {e}")
    st.stop()

kpis_resumen   = kpis_data.get("kpis_resumen", pd.DataFrame())
concentracion  = kpis_data.get("kpis_concentracion", pd.DataFrame())
antiguedad     = analytics.get("antiguedad_cartera", pd.DataFrame())
vencida_vig    = analytics.get("cartera_vencida_vs_vigente", pd.DataFrame())
facturas_vivas = reporte_data.get("facturas_vivas", pd.DataFrame())

# ======================================================================
# SECCION 1: KPIs PRINCIPALES (tarjetas)
# ======================================================================
st.subheader("Indicadores Clave")

def _get_kpi(df: pd.DataFrame, nombre: str) -> tuple[float, str]:
    """Extrae valor y unidad de un KPI del DataFrame resumen."""
    if df.empty:
        return 0.0, ""
    row = df[df["KPI"].str.contains(nombre, case=False, na=False)]
    if row.empty:
        return 0.0, ""
    return float(row.iloc[0]["VALOR"]), str(row.iloc[0]["UNIDAD"])


dso_val,  dso_unit  = _get_kpi(kpis_resumen, "DSO")
cei_val,  cei_unit  = _get_kpi(kpis_resumen, "CEI")
mor_val,  mor_unit  = _get_kpi(kpis_resumen, "Morosidad")

# Saldo total pendiente
saldo_total: float = 0.0
if not concentracion.empty and "SALDO" in concentracion.columns:
    saldo_total = float(concentracion["SALDO"].sum())

col1, col2, col3, col4 = st.columns(4)

with col1:
    delta_dso = "[OK] Bueno" if dso_val < 45 else ("[WARN] Atencion" if dso_val < 70 else "[CRITICO] Critico")
    st.metric(
        label="DSO - Dias Promedio de Cobro",
        value=f"{dso_val:.1f} dias",
        delta=delta_dso,
        delta_color="off",
    )

with col2:
    delta_cei = "[OK] Bueno" if cei_val >= 80 else ("[WARN] Atencion" if cei_val >= 60 else "[CRITICO] Critico")
    st.metric(
        label="CEI - Efectividad de Cobro",
        value=f"{cei_val:.1f}%",
        delta=delta_cei,
        delta_color="off",
    )

with col3:
    delta_mor = "[OK] Sana" if mor_val < 10 else ("[WARN] Atencion" if mor_val < 25 else "[CRITICO] Deteriorada")
    st.metric(
        label="Indice de Morosidad",
        value=f"{mor_val:.1f}%",
        delta=delta_mor,
        delta_color="off",
    )

with col4:
    st.metric(
        label="Saldo Total Pendiente",
        value=f"${saldo_total:,.2f}",
        delta=f"{len(concentracion)} clientes activos" if not concentracion.empty else "",
        delta_color="off",
    )

st.divider()

# ======================================================================
# SECCION 2: SEMAFORO DE ALERTAS
# ======================================================================
st.subheader("Semaforo de Alertas")

alertas_col1, alertas_col2, alertas_col3 = st.columns(3)

with alertas_col1:
    # DSO
    if dso_val < 45:
        st.markdown('<div class="alert-ok">[OK] <strong>DSO en zona segura</strong><br>Cobro promedio dentro de parametros aceptables (&lt;45 dias)</div>', unsafe_allow_html=True)
    elif dso_val < 70:
        st.markdown(f'<div class="alert-warning">[WARN] <strong>DSO elevado: {dso_val:.0f} dias</strong><br>Revisar clientes con mayor antiguedad</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="alert-critico">[CRITICO] <strong>DSO critico: {dso_val:.0f} dias</strong><br>Requiere accion inmediata en cobranza</div>', unsafe_allow_html=True)

with alertas_col2:
    # Morosidad
    if mor_val < 10:
        st.markdown(f'<div class="alert-ok">[OK] <strong>Cartera sana: {mor_val:.1f}% vencida</strong><br>Nivel de morosidad bajo control</div>', unsafe_allow_html=True)
    elif mor_val < 25:
        st.markdown(f'<div class="alert-warning">[WARN] <strong>Morosidad: {mor_val:.1f}%</strong><br>Monitorear clientes vencidos</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="alert-critico">[CRITICO] <strong>Cartera deteriorada: {mor_val:.1f}%</strong><br>Acciones urgentes de cobranza requeridas</div>', unsafe_allow_html=True)

with alertas_col3:
    # Concentracion
    if not concentracion.empty and "CLASIFICACION" in concentracion.columns:
        n_clase_a = int((concentracion["CLASIFICACION"] == "A").sum())
        total_clientes = len(concentracion)
        pct_concentracion = round(n_clase_a / total_clientes * 100, 1) if total_clientes else 0

        if n_clase_a <= 3:
            st.markdown(f'<div class="alert-critico">[CRITICO] <strong>Alta concentracion: {n_clase_a} clientes = 80% del saldo</strong><br>Riesgo alto de liquidez si alguno falla</div>', unsafe_allow_html=True)
        elif pct_concentracion <= 30:
            st.markdown(f'<div class="alert-ok">[OK] <strong>Concentracion saludable</strong><br>{n_clase_a} clientes acumulan el 80% del saldo</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-warning">[WARN] <strong>Concentracion moderada</strong><br>{n_clase_a} de {total_clientes} clientes = 80% del saldo</div>', unsafe_allow_html=True)

st.divider()

# ======================================================================
# SECCION 3: GRAFICAS
# ======================================================================
graf_col1, graf_col2 = st.columns([1.2, 1])

with graf_col1:
    st.subheader("Composicion de Cartera por Antiguedad")
    if not antiguedad.empty and "RANGO_ANTIGUEDAD" in antiguedad.columns:
        fig_ant = px.bar(
            antiguedad,
            x="RANGO_ANTIGUEDAD",
            y="SALDO_PENDIENTE",
            color="RANGO_ANTIGUEDAD",
            color_discrete_sequence=["#22c55e", "#3b82f6", "#f59e0b", "#f97316", "#ef4444", "#7f1d1d"],
            text_auto=".2s",
            labels={"RANGO_ANTIGUEDAD": "Rango", "SALDO_PENDIENTE": "Importe ($)"},
        )
        fig_ant.update_layout(
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(t=20, b=40, l=10, r=10),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        )
        fig_ant.update_traces(textfont_size=11, textposition="outside")
        st.plotly_chart(fig_ant, width="stretch")
    else:
        st.info("Sin datos de antiguedad disponibles.")

with graf_col2:
    st.subheader("Vencida vs Vigente")
    if not vencida_vig.empty and "SALDO_PENDIENTE" in vencida_vig.columns:
        fig_donut = px.pie(
            vencida_vig,
            names="ESTATUS_VENCIMIENTO",
            values="SALDO_PENDIENTE",
            hole=0.55,
            color="ESTATUS_VENCIMIENTO",
            color_discrete_map={"VENCIDO": "#ef4444", "VIGENTE": "#22c55e"},
        )
        fig_donut.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(t=20, b=60, l=10, r=10),
            paper_bgcolor="white",
        )
        fig_donut.update_traces(
            textposition="inside",
            textinfo="percent+label",
            textfont_size=13,
        )
        st.plotly_chart(fig_donut, width="stretch")
    else:
        st.info("Sin datos de vencimiento disponibles.")

st.divider()

# ======================================================================
# SECCION 4: TOP 10 CLIENTES POR SALDO
# ======================================================================
st.subheader("Top 10 Clientes por Saldo Pendiente")

if not concentracion.empty:
    top10 = concentracion.head(10).copy()

    cols_mostrar = ["NOMBRE_CLIENTE", "SALDO", "PCT_DEL_TOTAL", "PCT_ACUMULADO", "CLASIFICACION"]
    cols_disponibles = [c for c in cols_mostrar if c in top10.columns]
    top10_display = top10[cols_disponibles].copy()

    if "SALDO" in top10_display.columns:
        top10_display["SALDO"] = top10_display["SALDO"].apply(lambda x: f"${x:,.2f}")
    if "PCT_DEL_TOTAL" in top10_display.columns:
        top10_display["PCT_DEL_TOTAL"] = top10_display["PCT_DEL_TOTAL"].apply(lambda x: f"{x:.1f}%")
    if "PCT_ACUMULADO" in top10_display.columns:
        top10_display["PCT_ACUMULADO"] = top10_display["PCT_ACUMULADO"].apply(lambda x: f"{x:.1f}%")

    st.dataframe(
        top10_display,
        width="stretch",
        hide_index=True,
        column_config={
            "NOMBRE_CLIENTE":   st.column_config.TextColumn("Cliente"),
            "SALDO":            st.column_config.TextColumn("Saldo Pendiente"),
            "PCT_DEL_TOTAL":    st.column_config.TextColumn("% del Total"),
            "PCT_ACUMULADO":    st.column_config.TextColumn("% Acumulado"),
            "CLASIFICACION":    st.column_config.TextColumn("Clase ABC"),
        },
    )
else:
    st.info("Sin datos de concentracion disponibles.")