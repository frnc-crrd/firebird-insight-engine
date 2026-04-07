"""Pagina 4: KPIs Estrategicos.

Vista profunda de los cinco indicadores clave: DSO, CEI, Indice de
Morosidad, analisis Pareto/ABC y utilizacion de limite de credito.
Incluye interpretacion textual de cada KPI y graficas de gauge.
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

from dashboard.data_loader import cargar_kpis
from config.settings import KPI_PERIODO_DIAS

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
        <h1>KPIs Estrategicos de Cobranza ({moneda_actual})</h1>
        <p>Indicadores clave para evaluacion estrategica de la gestion de cuentas por cobrar</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================================
# CARGA DE DATOS Y LIMPIEZA
# ======================================================================
try:
    kpis_data = cargar_kpis()
except Exception as e:
    st.error(f"[ERROR] al cargar datos: {e}")
    st.stop()

# Extraccion dinamica por moneda
kpis_resumen      = kpis_data.get(f"kpis_resumen_{sufijo}", pd.DataFrame())
concentracion     = kpis_data.get(f"kpis_concentracion_{sufijo}", pd.DataFrame())
limite_credito    = kpis_data.get(f"kpis_limite_credito_{sufijo}", pd.DataFrame())
morosidad_cliente = kpis_data.get(f"kpis_morosidad_cliente_{sufijo}", pd.DataFrame())

# Filtrado quirurgico de fila "TOTAL"
if not concentracion.empty and "NOMBRE_CLIENTE" in concentracion.columns:
    concentracion = concentracion[concentracion["NOMBRE_CLIENTE"] != "TOTAL"].copy()
if not morosidad_cliente.empty and "NOMBRE_CLIENTE" in morosidad_cliente.columns:
    morosidad_cliente = morosidad_cliente[morosidad_cliente["NOMBRE_CLIENTE"] != "TOTAL"].copy()

st.caption(f"Periodo de analisis: ultimos {KPI_PERIODO_DIAS} dias")
st.divider()

# ======================================================================
# HELPERS
# ======================================================================
def _get_kpi_row(nombre: str) -> dict:
    if kpis_resumen.empty:
        return {}
    row = kpis_resumen[kpis_resumen["KPI"].str.contains(nombre, case=False, na=False)]
    return row.iloc[0].to_dict() if not row.empty else {}

def _gauge(valor: float, min_val: float, max_val: float, umbral_ok: float,
           umbral_warn: float, titulo: str, unidad: str,
           invertir: bool = False) -> go.Figure:
    if not invertir:
        pasos = [
            {"range": [min_val, umbral_ok],   "color": "#dcfce7"},
            {"range": [umbral_ok, umbral_warn], "color": "#fef9c3"},
            {"range": [umbral_warn, max_val],  "color": "#fee2e2"},
        ]
    else:
        pasos = [
            {"range": [min_val, umbral_warn],  "color": "#fee2e2"},
            {"range": [umbral_warn, umbral_ok], "color": "#fef9c3"},
            {"range": [umbral_ok, max_val],    "color": "#dcfce7"},
        ]

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=valor,
        number={"suffix": f" {unidad}", "font": {"size": 28, "color": "#0f172a"}},
        title={"text": titulo, "font": {"size": 14, "color": "#334155"}},
        gauge={
            "axis": {"range": [min_val, max_val], "tickwidth": 1, "tickcolor": "#94a3b8", "tickfont": {"color": "#334155"}},
            "bar":  {"color": "#2d6a9f", "thickness": 0.3},
            "steps": pasos,
            "threshold": {
                "line": {"color": "#1e3a5f", "width": 3},
                "thickness": 0.75,
                "value": valor,
            },
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(t=40, b=10, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

# ======================================================================
# SECCION 1: DSO
# ======================================================================
st.subheader("DSO - Days Sales Outstanding")

dso_row = _get_kpi_row("DSO")
dso_val = float(dso_row.get("VALOR", 0))

if not kpis_resumen.empty:
    dso_col1, dso_col2 = st.columns([1, 2])

    with dso_col1:
        st.plotly_chart(
            _gauge(dso_val, 0, 120, 45, 70, "DSO", "dias", invertir=False),
            width="stretch",
        )

    with dso_col2:
        st.markdown("#### ¿Que mide el DSO?")
        st.markdown(
            "Los **dias promedio que tarda la empresa en convertir sus ventas a credito en efectivo**. "
            "Un DSO alto indica lentitud en cobranza o clientes con problemas de pago."
        )

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown('<div class="alert-ok">[OK] <strong>&lt; 45 dias</strong><br>Cobranza eficiente</div>', unsafe_allow_html=True)
        with col_b:
            st.markdown('<div class="alert-warning">[WARN] <strong>45-70 dias</strong><br>Requiere atencion</div>', unsafe_allow_html=True)
        with col_c:
            st.markdown('<div class="alert-critico">[CRITICO] <strong>&gt; 70 dias</strong><br>Problema critico</div>', unsafe_allow_html=True)

        if dso_row.get("INTERPRETACION"):
            st.info(f"{dso_row['INTERPRETACION']}")
else:
    st.info("Sin datos suficientes para calcular DSO en esta moneda.")

st.divider()

# ======================================================================
# SECCION 2: CEI
# ======================================================================
st.subheader("CEI - Collection Effectiveness Index")

cei_row = _get_kpi_row("CEI")
cei_val = float(cei_row.get("VALOR", 0))

if not kpis_resumen.empty:
    cei_col1, cei_col2 = st.columns([1, 2])

    with cei_col1:
        st.plotly_chart(
            _gauge(cei_val, 0, 100, 80, 60, "CEI", "%", invertir=True),
            width="stretch",
        )

    with cei_col2:
        st.markdown("#### ¿Que mide el CEI?")
        st.markdown(
            "El **porcentaje del total cobrable que efectivamente se recupero** en el periodo. "
            "Complementa al DSO: el DSO dice *que tan rapido* cobras, el CEI dice *que tan bien* cobras."
        )

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown('<div class="alert-ok">[OK] <strong>≥ 80%</strong><br>Eficiencia aceptable</div>', unsafe_allow_html=True)
        with col_b:
            st.markdown('<div class="alert-warning">[WARN] <strong>60-79%</strong><br>Mejorable</div>', unsafe_allow_html=True)
        with col_c:
            st.markdown('<div class="alert-critico">[CRITICO] <strong>&lt; 60%</strong><br>Problemas serios</div>', unsafe_allow_html=True)

        if cei_row.get("INTERPRETACION"):
            st.info(f"{cei_row['INTERPRETACION']}")
else:
    st.info("Sin datos suficientes para calcular CEI en esta moneda.")

st.divider()

# ======================================================================
# SECCION 3: INDICE DE MOROSIDAD
# ======================================================================
st.subheader("Indice de Morosidad")

mor_row = _get_kpi_row("Morosidad")
mor_val = float(mor_row.get("VALOR", 0))

if not kpis_resumen.empty:
    mor_col1, mor_col2 = st.columns([1, 2])

    with mor_col1:
        st.plotly_chart(
            _gauge(mor_val, 0, 100, 10, 25, "Morosidad", "%", invertir=False),
            width="stretch",
        )

    with mor_col2:
        st.markdown("#### ¿Que mide el Indice de Morosidad?")
        st.markdown(
            "La **proporcion de la cartera cuya fecha de vencimiento ya paso**. "
            "Valores por encima del 25% indican cartera deteriorada que requiere acciones correctivas."
        )

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.markdown('<div class="alert-ok">[OK] <strong>&lt; 10%</strong><br>Sana</div>', unsafe_allow_html=True)
        with col_b:
            st.markdown('<div class="alert-warning">[WARN] <strong>10-25%</strong><br>Atencion</div>', unsafe_allow_html=True)
        with col_c:
            st.markdown('<div class="alert-critico">[CRITICO] <strong>&gt; 25%</strong><br>Deteriorada</div>', unsafe_allow_html=True)
        with col_d:
            st.markdown('<div class="alert-critico">[CRISIS] <strong>&gt; 50%</strong><br>Crisis</div>', unsafe_allow_html=True)

        if mor_row.get("INTERPRETACION"):
            st.info(f"{mor_row['INTERPRETACION']}")
else:
    st.info("Sin datos suficientes para calcular Morosidad en esta moneda.")

st.divider()

# ======================================================================
# SECCION 4: ANALISIS PARETO / ABC
# ======================================================================
st.subheader(f"Concentracion de Cartera - Analisis Pareto 80/20 ({moneda_actual})")

if not concentracion.empty:
    pareto_col1, pareto_col2 = st.columns([1.5, 1])

    with pareto_col1:
        df_pareto = concentracion.copy()
        
        if "SALDO_PENDIENTE" in df_pareto.columns:
            df_pareto["SALDO_PENDIENTE"] = pd.to_numeric(df_pareto["SALDO_PENDIENTE"], errors="coerce").fillna(0)
        if "PCT_ACUMULADO" in df_pareto.columns:
            df_pareto["PCT_ACUMULADO"] = pd.to_numeric(df_pareto["PCT_ACUMULADO"], errors="coerce").fillna(0) * 100

        df_pareto["RANK"] = range(1, len(df_pareto) + 1)
        top20 = df_pareto.head(20)

        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(
            x=top20["NOMBRE_CLIENTE"],
            y=top20["SALDO_PENDIENTE"],
            name="Saldo",
            marker_color="#3b82f6",
            opacity=0.8,
            yaxis="y1",
        ))
        fig_pareto.add_trace(go.Scatter(
            x=top20["NOMBRE_CLIENTE"],
            y=top20["PCT_ACUMULADO"],
            name="% Acumulado",
            line=dict(color="#ef4444", width=2),
            mode="lines+markers",
            yaxis="y2",
        ))
        fig_pareto.add_hline(
            y=80, line_dash="dash", line_color="#16a34a",
            annotation_text="80%", yref="y2", annotation_font_color="#334155"
        )

        fig_pareto.update_layout(
            xaxis=dict(tickangle=-45, showgrid=False, tickfont=dict(color="#334155")),
            yaxis=dict(title=f"Saldo ({moneda_actual})", showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#334155"), title_font=dict(color="#334155")),
            yaxis2=dict(
                title="% Acumulado",
                overlaying="y", side="right",
                range=[0, 110],
                showgrid=False,
                tickfont=dict(color="#334155"),
                title_font=dict(color="#334155")
            ),
            legend=dict(orientation="h", y=1.1, font=dict(color="#334155")),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=40, b=100, l=10, r=60),
            height=380,
        )
        st.plotly_chart(fig_pareto, width="stretch")

    with pareto_col2:
        if "CLASIFICACION" in concentracion.columns:
            if "SALDO_PENDIENTE" in concentracion.columns:
                concentracion["SALDO_PENDIENTE"] = pd.to_numeric(concentracion["SALDO_PENDIENTE"], errors="coerce").fillna(0)

            abc = concentracion.groupby("CLASIFICACION").agg(
                CLIENTES=("NOMBRE_CLIENTE", "count"),
                SALDO_PENDIENTE=("SALDO_PENDIENTE", "sum"),
            ).reset_index()

            total_saldo = concentracion["SALDO_PENDIENTE"].sum()
            total_clientes = len(concentracion)

            for _, row in abc.iterrows():
                clase = row["CLASIFICACION"]
                saldo = row["SALDO_PENDIENTE"]
                clientes = row["CLIENTES"]
                pct_s = saldo / total_saldo * 100 if total_saldo > 0 else 0
                pct_c = clientes / total_clientes * 100 if total_clientes > 0 else 0

                desc = {
                    "A": ("[A]", "Top 80% del saldo - maxima prioridad"),
                    "B": ("[B]", "Siguiente 15% - seguimiento regular"),
                    "C": ("[C]", "Ultimo 5% - gestion estandar"),
                }.get(clase, ("[ND]", ""))

                icono, descripcion = desc
                st.markdown(
                    f"""
                    **{icono} Clase {clase}**
                    - {clientes} clientes ({pct_c:.1f}%)
                    - ${saldo:,.2f} ({pct_s:.1f}% del total)
                    - *{descripcion}*
                    """,
                )
                st.divider()

    with st.expander("Ver tabla completa de concentracion"):
        display_conc = concentracion.copy()
        if "SALDO_PENDIENTE" in display_conc.columns:
            display_conc["SALDO_PENDIENTE"] = pd.to_numeric(display_conc["SALDO_PENDIENTE"], errors="coerce").fillna(0).apply(lambda x: f"${x:,.2f}")
        if "PCT_DEL_TOTAL" in display_conc.columns:
            display_conc["PCT_DEL_TOTAL"] = pd.to_numeric(display_conc["PCT_DEL_TOTAL"], errors="coerce").fillna(0).apply(lambda x: f"{x * 100:.2f}%")
        if "PCT_ACUMULADO" in display_conc.columns:
            display_conc["PCT_ACUMULADO"] = pd.to_numeric(display_conc["PCT_ACUMULADO"], errors="coerce").fillna(0).apply(lambda x: f"{x * 100:.2f}%")

        st.dataframe(display_conc, width="stretch", hide_index=True)

else:
    st.info("Sin datos de concentracion disponibles en esta moneda.")

st.divider()

# ======================================================================
# SECCION 5: MOROSIDAD POR CLIENTE - TOP RIESGOS
# ======================================================================
st.subheader(f"Top 10 Clientes por Saldo Vencido ({moneda_actual})")

if not morosidad_cliente.empty and "SALDO_VENCIDO" in morosidad_cliente.columns:
    morosidad_cliente["SALDO_VENCIDO"] = pd.to_numeric(morosidad_cliente["SALDO_VENCIDO"], errors="coerce").fillna(0)
    top_riesgo = morosidad_cliente[morosidad_cliente["SALDO_VENCIDO"] > 0].nlargest(10, "SALDO_VENCIDO").copy()

    if not top_riesgo.empty:
        if "DIAS_VENCIDO_MAX" in top_riesgo.columns:
            top_riesgo["DIAS_VENCIDO_MAX"] = pd.to_numeric(top_riesgo["DIAS_VENCIDO_MAX"], errors="coerce").fillna(0).astype(int)

        fig_riesgo = px.bar(
            top_riesgo,
            x="SALDO_VENCIDO",
            y="NOMBRE_CLIENTE",
            orientation="h",
            color="DIAS_VENCIDO_MAX",
            color_continuous_scale=["#16a34a", "#f59e0b", "#dc2626"],
            labels={
                "SALDO_VENCIDO": f"Saldo Vencido ({moneda_actual})",
                "NOMBRE_CLIENTE": "",
                "DIAS_VENCIDO_MAX": "Dias vencido",
            },
            text="SALDO_VENCIDO",
        )
        fig_riesgo.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", textfont=dict(color="#334155"))
        fig_riesgo.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed", tickfont=dict(color="#334155")),
            xaxis=dict(showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#334155")),
            margin=dict(t=20, b=20, l=150, r=120),
            coloraxis_colorbar=dict(title="Dias<br>vencido", tickfont=dict(color="#334155"), title_font=dict(color="#334155")),
            height=400,
        )
        st.plotly_chart(fig_riesgo, width="stretch")
    else:
        st.success(f"[OK] No hay clientes con saldo vencido en {moneda_actual}.")
else:
    st.info("Sin datos de morosidad por cliente disponibles en esta moneda.")