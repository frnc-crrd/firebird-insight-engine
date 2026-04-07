"""Pagina 5: Auditoria de Anomalias.

Resultados de las reglas de negocio aplicadas sobre los datos crudos:
importes atipicos, documentos sin cliente o vendedor, cancelados,
vencimientos criticos y reporte de calidad de datos.
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
        <h1>Auditoria de Anomalias</h1>
        <p>Deteccion de inconsistencias y problemas de calidad en los datos de CxC</p>
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
    st.error(f"[ERROR] al cargar auditoria: {e}")
    st.stop()

resumen          = audit.resumen
atipicos         = audit.importes_atipicos
sin_cliente      = audit.sin_tipo_cliente
sin_vendedor     = audit.sin_vendedor
cancelados       = audit.documentos_cancelados
venc_criticos    = audit.moras_atipicas
calidad_datos    = audit.calidad_datos

# Limpieza estandar (aunque atipica en raw data, previene inyecciones sumatorias)
if not atipicos.empty and "NOMBRE_CLIENTE" in atipicos.columns:
    atipicos = atipicos[atipicos["NOMBRE_CLIENTE"] != "TOTAL"].copy()

# ======================================================================
# SECCION 1: RESUMEN EJECUTIVO DE AUDITORIA
# ======================================================================
st.subheader("Resumen de Hallazgos")

total_hallazgos = resumen.get("total_hallazgos", 0)
total_registros = resumen.get("total_registros", 0)

if total_hallazgos == 0:
    st.success(f"[OK] Auditoria limpia - {total_registros:,} registros revisados sin hallazgos criticos.")
else:
    pct_hallazgos = (total_hallazgos / total_registros * 100) if total_registros > 0 else 0
    if pct_hallazgos < 2:
        nivel = "alert-ok"
        icono = "[OK]"
        texto = "Tasa de anomalias baja"
    elif pct_hallazgos < 5:
        nivel = "alert-warning"
        icono = "[WARN]"
        texto = "Anomalias moderadas - revisar"
    else:
        nivel = "alert-critico"
        icono = "[CRITICO]"
        texto = "Alta tasa de anomalias - accion requerida"

    st.markdown(
        f'<div class="{nivel}">{icono} <strong>{texto}</strong> - '
        f'{total_hallazgos:,} hallazgos en {total_registros:,} registros '
        f'({pct_hallazgos:.1f}%)</div>',
        unsafe_allow_html=True,
    )

st.write("")

col1, col2, col3, col4, col5 = st.columns(5)

hallazgos_config = [
    (col1, "importes_atipicos",   "Importes Atipicos",    resumen.get("importes_atipicos", 0)),
    (col2, "sin_tipo_cliente",    "Sin Tipo Cliente",     resumen.get("sin_tipo_cliente", 0)),
    (col3, "sin_vendedor",        "Sin Vendedor",         resumen.get("sin_vendedor", 0)),
    (col4, "cancelados",          "Cancelados",           resumen.get("cancelados", 0)),
    (col5, "moras_atipicas",      "Moras Atipicas",       resumen.get("moras_atipicas", 0)),
]

for col, clave, titulo, cantidad in hallazgos_config:
    with col:
        color = "[X]" if cantidad > 0 else "[OK]"
        st.metric(titulo, f"{color} {cantidad:,}")

st.divider()

# ======================================================================
# SECCION 2: GRAFICA DE DISTRIBUCION DE HALLAZGOS
# ======================================================================
if total_hallazgos > 0:
    st.subheader("Distribucion de Hallazgos por Tipo")

    datos_grafica = pd.DataFrame([
        {"Tipo": "Importes Atipicos", "Cantidad": resumen.get("importes_atipicos", 0)},
        {"Tipo": "Sin Tipo Cliente",  "Cantidad": resumen.get("sin_tipo_cliente", 0)},
        {"Tipo": "Sin Vendedor",      "Cantidad": resumen.get("sin_vendedor", 0)},
        {"Tipo": "Cancelados",        "Cantidad": resumen.get("cancelados", 0)},
        {"Tipo": "Moras Atipicas",    "Cantidad": resumen.get("moras_atipicas", 0)},
    ])
    datos_grafica = datos_grafica[datos_grafica["Cantidad"] > 0]

    if not datos_grafica.empty:
        fig = px.bar(
            datos_grafica,
            x="Tipo",
            y="Cantidad",
            color="Tipo",
            color_discrete_sequence=["#dc2626", "#ea580c", "#d97706", "#94a3b8", "#2563eb"],
            text="Cantidad",
        )
        fig.update_traces(textposition="outside", textfont=dict(color="#334155"))
        fig.update_layout(
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=30, b=20, l=10, r=10),
            xaxis=dict(showgrid=False, tickfont=dict(color="#334155")),
            yaxis=dict(showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#334155")),
        )
        st.plotly_chart(fig, width="stretch")

    st.divider()

# ======================================================================
# SECCION 3: DETALLE POR TIPO DE HALLAZGO
# ======================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Importes Atipicos",
    "Sin Tipo Cliente",
    "Sin Vendedor",
    "Cancelados",
    "Moras Atipicas",
    "Calidad de Datos",
])

# -- TAB 1: IMPORTES ATIPICOS -------------------------------------------
with tab1:
    st.markdown("#### Importes con Z-score elevado (outliers estadisticos)")
    st.markdown(
        "Un **Z-score >= 3** significa que el importe esta a mas de 3 desviaciones estandar "
        "de la media - evento estadisticamente raro (< 0.3% en distribucion normal). "
        "Puede indicar error de captura o una transaccion inusualmente grande."
    )
    if not atipicos.empty:
        cols_mostrar = [c for c in [
            "NOMBRE_CLIENTE", "FOLIO", "CONCEPTO", "FECHA_EMISION",
            "IMPORTE", "ZSCORE_IMPORTE", "MOTIVO",
        ] if c in atipicos.columns]
        display_at = atipicos[cols_mostrar].copy()
        
        if "IMPORTE" in display_at.columns:
            display_at["IMPORTE"] = pd.to_numeric(display_at["IMPORTE"], errors="coerce").fillna(0).apply(lambda x: f"${x:,.2f}")
        if "ZSCORE_IMPORTE" in display_at.columns:
            display_at["ZSCORE_IMPORTE"] = pd.to_numeric(display_at["ZSCORE_IMPORTE"], errors="coerce").fillna(0).apply(lambda x: f"{x:.2f}")

        st.dataframe(display_at, width="stretch", hide_index=True)
        st.caption(f"{len(atipicos):,} importes atipicos detectados")

        if "IMPORTE" in atipicos.columns and len(atipicos) > 1:
            fig_dist = px.box(
                atipicos,
                y=pd.to_numeric(atipicos["IMPORTE"], errors="coerce").fillna(0),
                title="Distribucion de importes atipicos",
                color_discrete_sequence=["#dc2626"],
            )
            fig_dist.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=40, b=20, l=10, r=10), height=250,
                yaxis=dict(gridcolor="#e2e8f0", tickfont=dict(color="#334155")),
                title_font=dict(color="#334155")
            )
            st.plotly_chart(fig_dist, width="stretch")
    else:
        st.success("[OK] No se detectaron importes atipicos.")

# -- TAB 2: SIN TIPO CLIENTE -------------------------------------------------
with tab2:
    st.markdown("#### Documentos asociados a un cliente sin tipo asignado")
    st.markdown("Afecta la clasificacion del analisis. Verifique la captura en Microsip.")
    if not sin_cliente.empty:
        cols_mostrar = [c for c in [
            "FOLIO", "CONCEPTO", "FECHA_EMISION", "IMPORTE",
            "NOMBRE_CLIENTE", "TIPO_CLIENTE", "VENDEDOR", "MOTIVO",
        ] if c in sin_cliente.columns]
        
        display_sc = sin_cliente[cols_mostrar].copy()
        if "IMPORTE" in display_sc.columns:
            display_sc["IMPORTE"] = pd.to_numeric(display_sc["IMPORTE"], errors="coerce").fillna(0).apply(lambda x: f"${x:,.2f}")
            
        st.dataframe(display_sc, width="stretch", hide_index=True)
    else:
        st.success("[OK] Todos los clientes tienen tipo asignado.")
        
# -- TAB 3: SIN VENDEDOR -------------------------------------------------
with tab3:
    st.markdown("#### Documentos asociados a un cliente sin vendedor asignado")
    st.markdown("Afecta los reportes y graficas de la fuerza de ventas. Verifique la captura en Microsip.")
    if not sin_vendedor.empty:
        cols_mostrar = [c for c in [
            "FOLIO", "CONCEPTO", "FECHA_EMISION", "IMPORTE",
            "NOMBRE_CLIENTE", "TIPO_CLIENTE", "VENDEDOR", "MOTIVO",
        ] if c in sin_vendedor.columns]
        
        display_sv = sin_vendedor[cols_mostrar].copy()
        if "IMPORTE" in display_sv.columns:
            display_sv["IMPORTE"] = pd.to_numeric(display_sv["IMPORTE"], errors="coerce").fillna(0).apply(lambda x: f"${x:,.2f}")
            
        st.dataframe(display_sv, width="stretch", hide_index=True)
    else:
        st.success("[OK] Todos los clientes tienen vendedor asignado.")

# -- TAB 4: CANCELADOS --------------------------------------------------
with tab4:
    st.markdown("#### Documentos cancelados en Microsip")
    st.markdown("El pipeline los excluye de los calculos transaccionales.")
    if not cancelados.empty:
        cols_mostrar = [c for c in [
            "NOMBRE_CLIENTE", "FOLIO", "CONCEPTO", "FECHA_EMISION",
            "IMPORTE", "DIAS_HASTA_CANCELACION", "MOTIVO",
        ] if c in cancelados.columns]
        display_can = cancelados[cols_mostrar].copy()
        
        if "IMPORTE" in display_can.columns:
            display_can["IMPORTE"] = pd.to_numeric(display_can["IMPORTE"], errors="coerce").fillna(0).apply(lambda x: f"${x:,.2f}")
        if "DIAS_HASTA_CANCELACION" in display_can.columns:
            display_can["DIAS_HASTA_CANCELACION"] = pd.to_numeric(display_can["DIAS_HASTA_CANCELACION"], errors="coerce").fillna(0).astype(int)
            
        st.dataframe(display_can, width="stretch", hide_index=True)
        st.caption(f"{len(cancelados):,} documentos cancelados")
    else:
        st.success("[OK] No se encontraron documentos cancelados.")

# -- TAB 5: MORAS ATIPICAS ---------------------------------------
with tab5:
    st.markdown("#### Cargos con mora significativamente alta (Z-Score Elevado)")
    st.markdown("Retraso estadisticamente anormal comparado con el resto de la cartera.")
    if not venc_criticos.empty:
        if "NOMBRE_CLIENTE" in venc_criticos.columns and "IMPORTE" in venc_criticos.columns:
            venc_criticos["IMPORTE"] = pd.to_numeric(venc_criticos["IMPORTE"], errors="coerce").fillna(0)
            venc_criticos["DELTA_MORA"] = pd.to_numeric(venc_criticos["DELTA_MORA"], errors="coerce").fillna(0)
            
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
                st.metric("Clientes con mora atipica", f"{resumen_vc['NOMBRE_CLIENTE'].nunique():,}")
            with g_col2:
                st.metric("Monto en mora atipica", f"${venc_criticos['IMPORTE'].sum():,.2f}")

            st.write("")

            display_vc = resumen_vc.copy()
            display_vc["IMPORTE_TOTAL"] = display_vc["IMPORTE_TOTAL"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(
                display_vc,
                width="stretch",
                hide_index=True,
                column_config={
                    "NOMBRE_CLIENTE": st.column_config.TextColumn("Cliente"),
                    "NUM_DOCS":       st.column_config.NumberColumn("Documentos", format="%d"),
                    "IMPORTE_TOTAL":  st.column_config.TextColumn("Importe en Riesgo"),
                    "DIAS_MAX":       st.column_config.NumberColumn("Dias Mora Max", format="%d"),
                },
            )

        with st.expander("Ver todos los documentos individuales"):
            cols_mostrar = [c for c in [
                "NOMBRE_CLIENTE", "FOLIO", "CONCEPTO", "FECHA_VENCIMIENTO",
                "IMPORTE", "DELTA_MORA", "ZSCORE_DELTA_MORA",
            ] if c in venc_criticos.columns]
            st.dataframe(venc_criticos[cols_mostrar], width="stretch", hide_index=True)
    else:
        st.success("[OK] No hay moras atipicas detectadas.")

# -- TAB 6: CALIDAD DE DATOS --------------------------------------------
with tab6:
    st.markdown("#### Reporte de calidad por columna")
    st.markdown("Estado de completitud. Alto porcentaje de nulos puede indicar configuracion incompleta en Microsip.")
    if not calidad_datos.empty:
        display_cd = calidad_datos.copy()
        if "PCT_NULOS" in display_cd.columns:
            display_cd["PCT_NULOS"] = pd.to_numeric(display_cd["PCT_NULOS"], errors="coerce").fillna(0).apply(lambda x: f"{x:.1f}%")

        st.dataframe(
            display_cd,
            width="stretch",
            hide_index=True,
            column_config={
                "COLUMNA":         st.column_config.TextColumn("Columna"),
                "TIPO_DATO":       st.column_config.TextColumn("Tipo"),
                "TOTAL_REGISTROS": st.column_config.NumberColumn("Total", format="%d"),
                "NULOS":           st.column_config.NumberColumn("Nulos", format="%d"),
                "PCT_NULOS":       st.column_config.TextColumn("% Nulos"),
                "VALORES_UNICOS":  st.column_config.NumberColumn("Valores Unicos", format="%d"),
            },
        )

        if "PCT_NULOS_VAL" in calidad_datos.columns:
            criticas = calidad_datos[calidad_datos["NULOS"] / pd.to_numeric(calidad_datos["TOTAL_REGISTROS"], errors='coerce').fillna(1) > 0.5]
            if not criticas.empty:
                st.warning(
                    f"[WARN] {len(criticas)} columna(s) con mas del 50% de valores nulos: "
                    + ", ".join(f"`{c}`" for c in criticas["COLUMNA"].tolist())
                )
    else:
        st.info("Sin datos de calidad disponibles.")