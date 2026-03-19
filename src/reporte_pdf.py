"""Generador del reporte PDF de analisis de cartera CxC y KPIs.

Produce un PDF ejecutivo con orientacion horizontal (Landscape),
asignando una pagina independiente a cada indicador clave de la cartera.

Arquitectura Visual (Apilamiento Vertical):
    - Agrupación estricta de Monedas: Primero todo MXN, luego todo USD.
    - Encabezado formal con el nombre del analisis y la moneda.
    - Explicación de negocio alineada a estándares financieros.
    - Gráfica renderizada centrada.
    - Tabla truncada dinámicamente para garantizar que encaje en la misma
      página sin generar saltos de línea (Page Breaks indeseados).

Uso:
    from src.reporte_pdf import generar_reporte_pdf
    generar_reporte_pdf(analisis_dict, output_path, timestamp)
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ======================================================================
# CONFIGURACION DE ESTILOS Y COLORES
# ======================================================================

_COLOR_AZUL    = "#4472C4"
_COLOR_VERDE   = "#548235"
_COLOR_AMARILLO= "#FFC000"
_COLOR_ROJO    = "#C00000"
_COLOR_GRIS    = "#A6A6A6"
_COLOR_FONDO   = "#F2F2F2"

_PAGE_WIDTH, _PAGE_HEIGHT = landscape(A4)

_STYLES = getSampleStyleSheet()
_STYLE_TITLE = ParagraphStyle(
    "ReportTitle",
    parent=_STYLES["Heading1"],
    fontSize=18,
    textColor=colors.HexColor(_COLOR_AZUL),
    alignment=TA_CENTER,
    spaceAfter=10,
    fontName="Helvetica-Bold",
)
_STYLE_SUBTITLE = ParagraphStyle(
    "ReportSubtitle",
    parent=_STYLES["Heading2"],
    fontSize=14,
    textColor=colors.HexColor("#333333"),
    alignment=TA_LEFT,
    spaceAfter=10,
    fontName="Helvetica-Bold",
)
_STYLE_BODY = ParagraphStyle(
    "ReportBody",
    parent=_STYLES["Normal"],
    fontSize=10,
    textColor=colors.HexColor("#404040"),
    alignment=TA_JUSTIFY,
    spaceAfter=10,
    leading=14,
    fontName="Helvetica",
)

# ======================================================================
# UTILIDADES DE RENDERIZADO
# ======================================================================

def _truncar_df_para_pdf(df: pd.DataFrame, max_rows: int = 8) -> pd.DataFrame:
    """Trunca el DataFrame para evitar tablas partidas, preservando el TOTAL."""
    if df.empty:
        return df
    
    col_zero = df.columns[0]
    is_total = df[col_zero].astype(str).str.strip().str.upper() == "TOTAL"
    
    df_data = df[~is_total]
    df_total = df[is_total]
    
    if len(df_data) > max_rows:
        return pd.concat([df_data.head(max_rows), df_total], ignore_index=True)
    return df


def _crear_tabla_estilo_financiero(df: pd.DataFrame, col_widths: list[float] | None = None) -> Table:
    """Convierte un DataFrame a una tabla ReportLab con estilo financiero estricto."""
    if df.empty:
        return Paragraph("No hay datos disponibles para este rubro.", _STYLE_BODY)

    data = [df.columns.tolist()]
    
    for _, row in df.iterrows():
        fila_formateada = []
        for col_name, val in zip(df.columns, row):
            col_upper = str(col_name).upper()
            if pd.isna(val):
                fila_formateada.append("")
            elif "PCT" in col_upper or col_upper == "VALOR" and isinstance(val, (float, int)) and val <= 1.0:
                try:
                    fila_formateada.append(f"{float(val) * 100:.2f}%")
                except ValueError:
                    fila_formateada.append(str(val))
            elif "NUM_" in col_upper or "DIAS_" in col_upper:
                try:
                    fila_formateada.append(f"{int(val):,}")
                except ValueError:
                    fila_formateada.append(str(val))
            elif isinstance(val, (float, int)):
                fila_formateada.append(f"${float(val):,.2f}")
            else:
                fila_formateada.append(str(val))
        data.append(fila_formateada)

    tabla = Table(data, colWidths=col_widths, repeatRows=1)
    
    estilo = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_COLOR_AZUL)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
        ("ALIGN", (0, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B4C6E7")),
    ])

    for row_idx, row in enumerate(data):
        if str(row[0]).strip().upper() == "TOTAL":
            estilo.add("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor(_COLOR_GRIS))
            estilo.add("TEXTCOLOR", (0, row_idx), (-1, row_idx), colors.white)
            estilo.add("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold")
            
    for row_idx in range(1, len(data)):
        if str(data[row_idx][0]).strip().upper() != "TOTAL" and row_idx % 2 == 0:
            estilo.add("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor(_COLOR_FONDO))

    tabla.setStyle(estilo)
    return tabla


def _generar_imagen_grafico(fig: plt.Figure, max_w_cm: float = 16.0, max_h_cm: float = 7.0) -> Image:
    """Convierte una figura Matplotlib a Imagen ReportLab respetando bounding boxes verticales."""
    buf = io.BytesPath() if hasattr(io, "BytesPath") else io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    img = Image(buf)
    
    w_factor = (max_w_cm * cm) / img.drawWidth
    h_factor = (max_h_cm * cm) / img.drawHeight
    factor = min(w_factor, h_factor)
    
    img.drawWidth = img.drawWidth * factor
    img.drawHeight = img.drawHeight * factor

    plt.close(fig)
    return img


# ======================================================================
# GENERADORES DE SECCIONES (PAGINAS)
# ======================================================================

def _seccion_kpis_macro(df: pd.DataFrame, moneda: str, story: list[Any]) -> None:
    """Página 1: Resumen de KPIs Estratégicos."""
    if df.empty: return
    
    story.append(Paragraph(f"Dashboard de Cuentas por Cobrar — {moneda}", _STYLE_TITLE))
    story.append(Paragraph("Resumen Estratégico (KPIs)", _STYLE_SUBTITLE))
    
    texto = (
        "Los Indicadores Clave de Desempeño (KPIs) ofrecen una radiografía inmediata de la salud "
        "financiera y la efectividad del ciclo de cobranza. Un DSO elevado compromete el flujo de caja, "
        "mientras que un índice de morosidad en crecimiento demanda acciones de recuperación inmediatas."
    )
    story.append(Paragraph(texto, _STYLE_BODY))
    story.append(_crear_tabla_estilo_financiero(df))
    story.append(PageBreak())


def _seccion_vencido_vs_vigente(df: pd.DataFrame, moneda: str, story: list[Any]) -> None:
    """Página: Gráfico de Dona apilado verticalmente sobre la tabla."""
    if df.empty: return
    
    story.append(Paragraph(f"Cartera Vencida vs Vigente — {moneda}", _STYLE_TITLE))
    
    texto = (
        "Esta vista clasifica el capital pendiente en dos grandes bloques: lo que aún se encuentra "
        "dentro de los términos de pago acordados (Vigente) y lo que representa un incumplimiento de contrato "
        "(Vencido). Permite priorizar la estrategia de contacto con el cliente."
    )
    story.append(Paragraph(texto, _STYLE_BODY))

    df_plot = df[df["ESTATUS_VENCIMIENTO"].str.upper() != "TOTAL"].copy()
    
    if not df_plot.empty and df_plot["SALDO_PENDIENTE"].sum() > 0:
        fig, ax = plt.subplots(figsize=(8, 3.5))
        colores = np.where(df_plot["ESTATUS_VENCIMIENTO"].str.contains("VIGENTE"), _COLOR_VERDE, _COLOR_ROJO)
        
        wedges, texts, autotexts = ax.pie(
            df_plot["SALDO_PENDIENTE"],
            colors=colores,
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.75,
            wedgeprops=dict(width=0.4, edgecolor='w')
        )
        
        plt.setp(autotexts, size=9, weight="bold", color="#333333")
        
        # Externalizamos la leyenda para evitar superposición de textos
        ax.legend(wedges, df_plot["ESTATUS_VENCIMIENTO"], loc="center left", bbox_to_anchor=(1, 0.5))
        ax.set_title("Proporción de Deuda", fontweight="bold", color="#333333")
        
        img = _generar_imagen_grafico(fig, max_w_cm=14.0, max_h_cm=6.5)
        story.append(img)
        story.append(Spacer(1, 0.5 * cm))

    # Restringimos a 8 filas para asegurar el ajuste vertical en la página
    df_mostrar = _truncar_df_para_pdf(df, max_rows=8)
    story.append(_crear_tabla_estilo_financiero(df_mostrar))
    story.append(PageBreak())


def _seccion_antiguedad(df: pd.DataFrame, moneda: str, story: list[Any]) -> None:
    """Página: Gráfico de Barras apilado verticalmente."""
    if df.empty: return

    story.append(Paragraph(f"Antigüedad de Cartera (Aging) — {moneda}", _STYLE_TITLE))
    
    texto = (
        "El análisis de antigüedad segmenta la deuda según sus días de mora. "
        "Facturas en el segmento de 1-30 días requieren gestión preventiva, mientras que los "
        "saldos superiores a 90 días poseen un riesgo crítico de incobrabilidad y exigen escalamiento."
    )
    story.append(Paragraph(texto, _STYLE_BODY))

    df_plot = df[df["RANGO_ANTIGUEDAD"].str.upper() != "TOTAL"].copy()
    
    if not df_plot.empty and df_plot["SALDO_PENDIENTE"].sum() > 0:
        fig, ax = plt.subplots(figsize=(10, 3.5))
        
        colores = []
        for rango in df_plot["RANGO_ANTIGUEDAD"]:
            if "VIGENTE" in str(rango).upper():
                colores.append(_COLOR_VERDE)
            else:
                colores.append(_COLOR_ROJO)
                
        barras = ax.barh(df_plot["RANGO_ANTIGUEDAD"], df_plot["SALDO_PENDIENTE"], color=colores)
        
        ax.xaxis.set_major_formatter(mticker.StrMethodFormatter('${x:,.0f}'))
        ax.invert_yaxis()
        ax.set_title("Distribución del Saldo por Rango", fontweight="bold", color="#333333")
        
        for bar in barras:
            width = bar.get_width()
            if width > 0:
                ax.annotate(
                    f'${width:,.0f}',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(3, 0),
                    textcoords="offset points",
                    ha='left', va='center', fontsize=7
                )
                
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.yticks(fontsize=7)

        img = _generar_imagen_grafico(fig, max_w_cm=16.0, max_h_cm=6.5)
        story.append(img)
        story.append(Spacer(1, 0.5 * cm))

    df_mostrar = _truncar_df_para_pdf(df, max_rows=8)
    story.append(_crear_tabla_estilo_financiero(df_mostrar))
    story.append(PageBreak())


def _seccion_concentracion(df: pd.DataFrame, moneda: str, story: list[Any]) -> None:
    """Página: Pareto apilado verticalmente."""
    if df.empty: return

    story.append(Paragraph(f"Concentración de Cartera (Regla 80/20) — {moneda}", _STYLE_TITLE))
    
    texto = (
        "Identifica la dependencia financiera evaluando qué clientes acumulan la mayor parte de la deuda. "
        "La Clasificación A representa a los deudores críticos que agrupan el 80% del saldo total. "
        "Cualquier impago en este sector compromete severamente la viabilidad operativa de la empresa."
    )
    story.append(Paragraph(texto, _STYLE_BODY))

    df_plot = df[df["NOMBRE_CLIENTE"].str.upper() != "TOTAL"].copy()
    if not df_plot.empty:
        top_n = df_plot.head(10).copy()
        fig, ax1 = plt.subplots(figsize=(10, 3.5))
        
        ax1.bar(
            top_n["NOMBRE_CLIENTE"].str[:12] + "..", 
            top_n["SALDO_PENDIENTE"], 
            color=_COLOR_AZUL, alpha=0.8
        )
        ax1.set_ylabel('Saldo ($)', color=_COLOR_AZUL, fontweight="bold", fontsize=8)
        ax1.tick_params(axis='y', labelcolor=_COLOR_AZUL, labelsize=8)
        ax1.yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.0f}'))
        plt.xticks(rotation=45, ha='right', fontsize=7)

        ax2 = ax1.twinx()
        ax2.plot(
            top_n["NOMBRE_CLIENTE"].str[:12] + "..", 
            top_n["PCT_ACUMULADO"] * 100, 
            color=_COLOR_ROJO, marker='o', linewidth=2
        )
        ax2.set_ylabel('% Acumulado', color=_COLOR_ROJO, fontweight="bold", fontsize=8)
        ax2.tick_params(axis='y', labelcolor=_COLOR_ROJO, labelsize=8)
        ax2.set_ylim(0, 105)
        ax2.axhline(80, color='gray', linestyle='dashed', alpha=0.5)
        
        plt.title("Análisis Pareto (Top 10 Clientes)", fontweight="bold", color="#333333")

        img = _generar_imagen_grafico(fig, max_w_cm=16.0, max_h_cm=6.5)
        story.append(img)
        story.append(Spacer(1, 0.5 * cm))

    df_mostrar = _truncar_df_para_pdf(df, max_rows=8)
    story.append(_crear_tabla_estilo_financiero(df_mostrar))
    story.append(PageBreak())


def _seccion_limite_credito(df: pd.DataFrame, moneda: str, story: list[Any]) -> None:
    """Página: Riesgo por Límites de Crédito Excedidos (Sin gráfica, permite más filas)."""
    if df.empty: return

    story.append(Paragraph(f"Utilización de Límite de Crédito — {moneda}", _STYLE_TITLE))
    
    texto = (
        "Mide la exposición al riesgo comparando la deuda actual contra la línea de crédito autorizada. "
        "Las cuentas marcadas en 'SOBRE_LIMITE' operan fuera de política corporativa. "
        "Se recomienda el bloqueo preventivo de despacho hasta garantizar la regularización del pago."
    )
    story.append(Paragraph(texto, _STYLE_BODY))

    df_mostrar = _truncar_df_para_pdf(df, max_rows=16)
    story.append(_crear_tabla_estilo_financiero(df_mostrar))
    story.append(PageBreak())


def _seccion_anexos_operativos(df: pd.DataFrame, titulo: str, descripcion: str, story: list[Any]) -> None:
    """Páginas: Tablas operativas simples."""
    if df.empty: return

    story.append(Paragraph(titulo, _STYLE_TITLE))
    story.append(Paragraph(descripcion, _STYLE_BODY))
    
    df_mostrar = _truncar_df_para_pdf(df, max_rows=16)
    story.append(_crear_tabla_estilo_financiero(df_mostrar))
    story.append(PageBreak())


# ======================================================================
# ENSAMBLADOR PRINCIPAL
# ======================================================================

def generar_reporte_pdf(analisis: dict[str, pd.DataFrame], output_path: Path, timestamp: str) -> None:
    """Ensambla todas las paginas del PDF agrupando por moneda."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title="Dashboard Estratégico de CxC",
        author="Firebird Insight Engine"
    )
    
    story: list[Any] = []

    # Portada
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph("DASHBOARD ESTRATÉGICO", ParagraphStyle("Title1", parent=_STYLE_TITLE, fontSize=30)))
    story.append(Paragraph("Cuentas por Cobrar (CxC)", ParagraphStyle("Title2", parent=_STYLE_TITLE, fontSize=24, textColor=colors.HexColor("#333333"))))
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph(f"Generado automáticamente: {timestamp}", ParagraphStyle("Date", parent=_STYLE_BODY, alignment=TA_CENTER)))
    story.append(PageBreak())

    # --- BLOQUE MXN ---
    _seccion_kpis_macro(analisis.get("kpis_resumen_mxn", pd.DataFrame()), "MXN", story)
    _seccion_vencido_vs_vigente(analisis.get("cartera_vencida_vs_vigente_mxn", pd.DataFrame()), "MXN", story)
    _seccion_antiguedad(analisis.get("antiguedad_cartera_mxn", pd.DataFrame()), "MXN", story)
    _seccion_concentracion(analisis.get("kpis_concentracion_mxn", pd.DataFrame()), "MXN", story)
    _seccion_limite_credito(analisis.get("kpis_limite_credito_mxn", pd.DataFrame()), "MXN", story)

    _seccion_anexos_operativos(
        analisis.get("resumen_concepto_cxc_mxn", pd.DataFrame()), 
        "Anexo: Movimientos por Concepto Contable (MXN)",
        "Distribución transaccional del capital. Permite auditar el volumen operativo detrás de los montos financieros.",
        story
    )
    _seccion_anexos_operativos(
        analisis.get("resumen_cancelados_cxc_mxn", pd.DataFrame()), 
        "Anexo: Análisis de Documentos Cancelados (MXN)",
        "Las cancelaciones recurrentes pueden ser un síntoma de errores operativos o disputas comerciales. Un volumen alto requiere auditoría inmediata.",
        story
    )
    _seccion_anexos_operativos(
        analisis.get("resumen_ajustes_cxc_mxn", pd.DataFrame()), 
        "Anexo: Registros por Acreditar / Anticipos (MXN)",
        "Pagos o anticipos ingresados al sistema que no han sido conciliados o aplicados a una factura específica, distorsionando el saldo real del cliente.",
        story
    )

    # --- TRANSICIÓN A USD ---
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph("SECCIÓN EN DÓLARES (USD)", ParagraphStyle("TitleUSD", parent=_STYLE_TITLE, fontSize=28, textColor=colors.HexColor(_COLOR_VERDE))))
    story.append(PageBreak())

    # --- BLOQUE USD ---
    _seccion_kpis_macro(analisis.get("kpis_resumen_usd", pd.DataFrame()), "USD", story)
    _seccion_vencido_vs_vigente(analisis.get("cartera_vencida_vs_vigente_usd", pd.DataFrame()), "USD", story)
    _seccion_antiguedad(analisis.get("antiguedad_cartera_usd", pd.DataFrame()), "USD", story)
    _seccion_concentracion(analisis.get("kpis_concentracion_usd", pd.DataFrame()), "USD", story)
    _seccion_limite_credito(analisis.get("kpis_limite_credito_usd", pd.DataFrame()), "USD", story)

    _seccion_anexos_operativos(
        analisis.get("resumen_concepto_cxc_usd", pd.DataFrame()), 
        "Anexo: Movimientos por Concepto Contable (USD)",
        "Distribución transaccional del capital. Permite auditar el volumen operativo detrás de los montos financieros.",
        story
    )
    _seccion_anexos_operativos(
        analisis.get("resumen_cancelados_cxc_usd", pd.DataFrame()), 
        "Anexo: Análisis de Documentos Cancelados (USD)",
        "Las cancelaciones recurrentes pueden ser un síntoma de errores operativos o disputas comerciales. Un volumen alto requiere auditoría inmediata.",
        story
    )
    _seccion_anexos_operativos(
        analisis.get("resumen_ajustes_cxc_usd", pd.DataFrame()), 
        "Anexo: Registros por Acreditar / Anticipos (USD)",
        "Pagos o anticipos ingresados al sistema que no han sido conciliados o aplicados a una factura específica, distorsionando el saldo real del cliente.",
        story
    )

    try:
        doc.build(story)
        logger.info("PDF generado correctamente: %s", output_path.name)
    except Exception as exc:
        logger.error("Error al construir el PDF: %s", exc)
        raise