"""Página 5: Auditoría de Anomalías.

Resultados de las reglas de negocio aplicadas sobre los datos crudos:
importes atípicos, documentos sin cliente o vendedor, cancelados,
vencimientos críticos y reporte de calidad de datos.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.data_loader import cargar_auditoria

# ======================================================================
# HEADER
# ======================================================================
st.markdown(
    """
    <div class="main-header">
        <h1>🔍 Auditoría de Anomalías</h1>
        <p>Detección de inconsistencias y problemas de calidad en los datos de CxC</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================================
# CARGA DE DATOS
# ======================================================================
try:
    audit = cargar_auditoria()
except Exception as e:
    st.error(f"❌ Error al cargar auditoría: {e}")
    st.stop()

# CORRECCIÓN APLICADA: Extracción de variables ajustada a la clase AuditResult actual
resumen          = audit.resumen
atipicos         = audit.importes_atipicos
sin_cliente      = audit.sin_tipo_cliente
sin_vendedor     = audit.sin_vendedor
cancelados       = audit.documentos_cancelados
venc_criticos    = audit.moras_atipicas
calidad_datos    = audit.calidad_datos

# ======================================================================
# SECCIÓN 1: RESUMEN EJECUTIVO DE AUDITORÍA
# ======================================================================
st.subheader("Resumen de Hallazgos")

total_hallazgos = resumen.get("total_hallazgos", 0)
total_registros = resumen.get("total_registros", 0)

if total_hallazgos == 0:
    st.success(f"✅ Auditoría limpia — {total_registros:,} registros revisados sin hallazgos críticos.")
else:
    pct_hallazgos = (total_hallazgos / total_registros * 100) if total_registros > 0 else 0
    if pct_hallazgos < 2:
        nivel = "alert-ok"
        icono = "✅"
        texto = "Tasa de anomalías baja"
    elif pct_hallazgos < 5:
        nivel = "alert-warning"
        icono = "⚠️"
        texto = "Anomalías moderadas — revisar"
    else:
        nivel = "alert-critico"
        icono = "🚨"
        texto = "Alta tasa de anomalías — acción requerida"

    st.markdown(
        f'<div class="{nivel}">{icono} <strong>{texto}</strong> — '
        f'{total_hallazgos:,} hallazgos en {total_registros:,} registros '
        f'({pct_hallazgos:.1f}%)</div>',
        unsafe_allow_html=True,
    )

st.write("")

# Tarjetas por tipo de hallazgo
col1, col2, col3, col4, col5 = st.columns(5)

hallazgos_config = [
    (col1, "importes_atipicos",   "📊 Importes Atípicos",    resumen.get("importes_atipicos", 0)),
    (col2, "sin_tipo_cliente",    "👤 Sin Tipo Cliente",     resumen.get("sin_tipo_cliente", 0)),
    (col3, "sin_vendedor",        "👔 Sin Vendedor",         resumen.get("sin_vendedor", 0)),
    (col4, "cancelados",          "❌ Cancelados",           resumen.get("cancelados", 0)),
    (col5, "moras_atipicas",      "⏰ Moras Atípicas",       resumen.get("moras_atipicas", 0)),
]

for col, clave, titulo, cantidad in hallazgos_config:
    with col:
        color = "🔴" if cantidad > 0 else "🟢"
        st.metric(titulo, f"{color} {cantidad:,}")

st.divider()

# ======================================================================
# SECCIÓN 2: GRÁFICA DE DISTRIBUCIÓN DE HALLAZGOS
# ======================================================================
if total_hallazgos > 0:
    st.subheader("Distribución de Hallazgos por Tipo")

    datos_grafica = pd.DataFrame([
        {"Tipo": "Importes Atípicos", "Cantidad": resumen.get("importes_atipicos", 0)},
        {"Tipo": "Sin Tipo Cliente",  "Cantidad": resumen.get("sin_tipo_cliente", 0)},
        {"Tipo": "Sin Vendedor",      "Cantidad": resumen.get("sin_vendedor", 0)},
        {"Tipo": "Cancelados",        "Cantidad": resumen.get("cancelados", 0)},
        {"Tipo": "Moras Atípicas",    "Cantidad": resumen.get("moras_atipicas", 0)},
    ])
    datos_grafica = datos_grafica[datos_grafica["Cantidad"] > 0]

    if not datos_grafica.empty:
        fig = px.bar(
            datos_grafica,
            x="Tipo",
            y="Cantidad",
            color="Tipo",
            color_discrete_sequence=["#ef4444", "#f97316", "#f59e0b", "#94a3b8", "#3b82f6"],
            text="Cantidad",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(t=30, b=20, l=10, r=10),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

# ======================================================================
# SECCIÓN 3: DETALLE POR TIPO DE HALLAZGO
# ======================================================================

# Tabs para cada tipo de hallazgo (duplicados eliminado)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Importes Atípicos",
    "👤 Sin Tipo Cliente",
    "👔 Sin Vendedor",
    "❌ Cancelados",
    "⏰ Moras Atípicas",
    "🗂️ Calidad de Datos",
])


# ── TAB 1: IMPORTES ATÍPICOS ───────────────────────────────────────────
with tab1:
    st.markdown("#### Importes con Z-score elevado (outliers estadísticos)")
    st.markdown(
        "Un **Z-score ≥ 3** significa que el importe está a más de 3 desviaciones estándar "
        "de la media — evento estadísticamente raro (< 0.3% en distribución normal). "
        "Puede indicar error de captura o una transacción inusualmente grande."
    )
    if not atipicos.empty:
        cols_mostrar = [c for c in [
            "NOMBRE_CLIENTE", "FOLIO", "CONCEPTO", "FECHA_EMISION",
            "IMPORTE", "ZSCORE_IMPORTE", "MOTIVO",
        ] if c in atipicos.columns]
        display_at = atipicos[cols_mostrar].copy()
        if "IMPORTE" in display_at.columns:
            display_at["IMPORTE"] = display_at["IMPORTE"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
        if "ZSCORE_IMPORTE" in display_at.columns:
            display_at["ZSCORE_IMPORTE"] = display_at["ZSCORE_IMPORTE"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")

        st.dataframe(display_at, use_container_width=True, hide_index=True)
        st.caption(f"{len(atipicos):,} importes atípicos detectados")

        # Mini gráfica de distribución
        if "IMPORTE" in atipicos.columns and len(atipicos) > 1:
            fig_dist = px.box(
                atipicos,
                y="IMPORTE",
                title="Distribución de importes atípicos",
                color_discrete_sequence=["#ef4444"],
            )
            fig_dist.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=40, b=20, l=10, r=10), height=250,
            )
            st.plotly_chart(fig_dist, use_container_width=True)
    else:
        st.success("✅ No se detectaron importes atípicos.")

# ── TAB 2: SIN TIPO CLIENTE ─────────────────────────────────────────────────
with tab2:
    st.markdown("#### Documentos asociados a un cliente sin tipo asignado")
    st.markdown(
        "Afecta la clasificación del análisis. Verifique la captura en Microsip."
    )
    if not sin_cliente.empty:
        cols_mostrar = [c for c in [
            "FOLIO", "CONCEPTO", "FECHA_EMISION", "IMPORTE",
            "NOMBRE_CLIENTE", "TIPO_CLIENTE", "VENDEDOR", "MOTIVO",
        ] if c in sin_cliente.columns]
        st.dataframe(
            sin_cliente[cols_mostrar],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("✅ Todos los clientes tienen tipo asignado.")
        
# ── TAB 3: SIN VENDEDOR ─────────────────────────────────────────────────
with tab3:
    st.markdown("#### Documentos asociados a un cliente sin vendedor asignado")
    st.markdown(
        "Afecta los reportes y gráficas de la fuerza de ventas. Verifique la captura en Microsip."
    )
    if not sin_vendedor.empty:
        cols_mostrar = [c for c in [
            "FOLIO", "CONCEPTO", "FECHA_EMISION", "IMPORTE",
            "NOMBRE_CLIENTE", "TIPO_CLIENTE", "VENDEDOR", "MOTIVO",
        ] if c in sin_vendedor.columns]
        st.dataframe(
            sin_vendedor[cols_mostrar],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("✅ Todos los clientes tienen vendedor asignado.")

# ── TAB 4: CANCELADOS ──────────────────────────────────────────────────
with tab4:
    st.markdown("#### Documentos cancelados en Microsip")
    st.markdown(
        "Estos documentos están marcados como cancelados en el sistema. "
        "El pipeline los excluye de los cálculos, pero se listan aquí para referencia."
    )
    if not cancelados.empty:
        cols_mostrar = [c for c in [
            "NOMBRE_CLIENTE", "FOLIO", "CONCEPTO", "FECHA_EMISION",
            "IMPORTE", "DIAS_HASTA_CANCELACION", "MOTIVO",
        ] if c in cancelados.columns]
        display_can = cancelados[cols_mostrar].copy()
        if "IMPORTE" in display_can.columns:
            display_can["IMPORTE"] = display_can["IMPORTE"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
        st.dataframe(display_can, use_container_width=True, hide_index=True)
        st.caption(f"{len(cancelados):,} documentos cancelados")
    else:
        st.success("✅ No se encontraron documentos cancelados.")

# ── TAB 5: MORAS ATÍPICAS ───────────────────────────────────────
with tab5:
    st.markdown("#### Cargos con mora significativamente alta (Z-Score Elevado)")
    st.markdown(
        "Estas facturas no solo están vencidas, sino que su retraso es "
        "estadísticamente anormal comparado con la mora del resto de la cartera."
    )
    if not venc_criticos.empty:
        # Agrupar por cliente para visualización
        if "NOMBRE_CLIENTE" in venc_criticos.columns and "IMPORTE" in venc_criticos.columns:
            resumen_vc = (
                venc_criticos.groupby("NOMBRE_CLIENTE")
                .agg(
                    NUM_DOCS=("IMPORTE", "count"),
                    IMPORTE_TOTAL=("IMPORTE", "sum"),
                    DIAS_MAX=("DELTA_MORA", "max"),
                )
                .reset_index()
                .sort_values("IMPORTE_TOTAL", ascending=False)
            )

            g_col1, g_col2 = st.columns(2)
            with g_col1:
                st.metric("Clientes con mora atípica", f"{resumen_vc['NOMBRE_CLIENTE'].nunique():,}")
            with g_col2:
                st.metric("Monto en mora atípica", f"${venc_criticos['IMPORTE'].sum():,.2f}")

            st.write("")

            display_vc = resumen_vc.copy()
            display_vc["IMPORTE_TOTAL"] = display_vc["IMPORTE_TOTAL"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(
                display_vc,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "NOMBRE_CLIENTE": st.column_config.TextColumn("Cliente"),
                    "NUM_DOCS":       st.column_config.NumberColumn("Documentos", format="%d"),
                    "IMPORTE_TOTAL":  st.column_config.TextColumn("Importe en Riesgo"),
                    "DIAS_MAX":       st.column_config.NumberColumn("Días Mora Máx", format="%d"),
                },
            )

        with st.expander("Ver todos los documentos individuales"):
            cols_mostrar = [c for c in [
                "NOMBRE_CLIENTE", "FOLIO", "CONCEPTO", "FECHA_VENCIMIENTO",
                "IMPORTE", "DELTA_MORA", "ZSCORE_DELTA_MORA",
            ] if c in venc_criticos.columns]
            st.dataframe(venc_criticos[cols_mostrar], use_container_width=True, hide_index=True)
    else:
        st.success("✅ No hay moras atípicas detectadas.")

# ── TAB 6: CALIDAD DE DATOS ────────────────────────────────────────────
with tab6:
    st.markdown("#### Reporte de calidad por columna")
    st.markdown(
        "Estado de completitud de cada columna del dataset. "
        "Columnas con alto porcentaje de nulos pueden indicar configuración "
        "incompleta en Microsip o campos no utilizados."
    )
    if not calidad_datos.empty:
        display_cd = calidad_datos.copy()
        if "PCT_NULOS" in display_cd.columns:
            display_cd["PCT_NULOS"] = display_cd["PCT_NULOS"].apply(lambda x: f"{x:.1f}%")

        st.dataframe(
            display_cd,
            use_container_width=True,
            hide_index=True,
            column_config={
                "COLUMNA":         st.column_config.TextColumn("Columna"),
                "TIPO_DATO":       st.column_config.TextColumn("Tipo"),
                "TOTAL_REGISTROS": st.column_config.NumberColumn("Total", format="%d"),
                "NULOS":           st.column_config.NumberColumn("Nulos", format="%d"),
                "PCT_NULOS":       st.column_config.TextColumn("% Nulos"),
                "VALORES_UNICOS":  st.column_config.NumberColumn("Valores Únicos", format="%d"),
            },
        )

        # Alertar columnas con > 50% nulos
        if "PCT_NULOS" in calidad_datos.columns:
            criticas = calidad_datos[calidad_datos["NULOS"] / calidad_datos["TOTAL_REGISTROS"] > 0.5]
            if not criticas.empty:
                st.warning(
                    f"⚠️ {len(criticas)} columna(s) con más del 50% de valores nulos: "
                    + ", ".join(f"`{c}`" for c in criticas["COLUMNA"].tolist())
                )
    else:
        st.info("Sin datos de calidad disponibles.")