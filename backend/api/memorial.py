"""
Gerador de Memorial de Cálculo em PDF e DOCX.

O memorial documenta:
1. Dados de entrada (geometria, cargas, materiais, restrições).
2. Combinações de cargas aplicadas (NBR 6120/8681).
3. Tabela de esforços nas barras (axial, momentos, utilização).
4. Verificações NBR 8800 (ELU, ELS, flambagem) — com referência às equações.
5. Verificações NBR 6120 (cargas de manutenção, assimetrias).
6. Verificações NBR 6123 (vento, pressões).
7. Resultado final (peso, custo, perfis escolhidos).

Geração via ReportLab (PDF) e python-docx (DOCX).
"""
from __future__ import annotations

import base64
import io
import logging
from datetime import datetime
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from api.schemas import RespostaOtimizacao, RequisicaoOtimizacao

_logger = logging.getLogger(__name__)


def _formatar_numero(valor: float, casas: int = 2) -> str:
    """Formata número com separador brasileiro."""
    try:
        s = f"{valor:.{casas}f}"
        return s.replace(".", ",")
    except Exception:
        return str(valor)


def gerar_memorial_pdf(
    requisicao: RequisicaoOtimizacao,
    resposta: RespostaOtimizacao,
) -> bytes:
    """Gera o memorial de cálculo em formato PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Memorial de Cálculo — TRUSS-OPT 3D",
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "Titulo", parent=estilos["Title"],
        fontSize=16, textColor=colors.HexColor("#1E40AF"),
        spaceAfter=12, alignment=1,
    )
    estilo_h2 = ParagraphStyle(
        "H2", parent=estilos["Heading2"],
        fontSize=12, textColor=colors.HexColor("#1E40AF"),
        spaceBefore=12, spaceAfter=6,
    )
    estilo_normal = ParagraphStyle(
        "Normal", parent=estilos["Normal"],
        fontSize=9, leading=12,
    )

    elementos = []

    # Capa / cabeçalho.
    elementos.append(Paragraph("Memorial de Cálculo Estrutural", estilo_titulo))
    elementos.append(Paragraph(
        f"<b>TRUSS-OPT 3D</b> — Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        estilo_normal,
    ))
    elementos.append(Spacer(1, 6 * mm))

    # 1. Dados de entrada.
    elementos.append(Paragraph("1. Dados de Entrada", estilo_h2))
    dados_entrada = [
        ["Parâmetro", "Valor"],
        ["Vão (L)", f"{_formatar_numero(requisicao.length)} m"],
        ["Altura (H)", f"{_formatar_numero(requisicao.height)} m"],
        ["Largura (W)", f"{_formatar_numero(requisicao.width)} m"],
        ["Divisões", f"{requisicao.divisions}"],
        ["Tipo de solo", requisicao.soil_type],
        ["Lâmina d'água", f"{_formatar_numero(requisicao.water_lamina)} mm"],
        ["Sapata (B × L)", f"{_formatar_numero(requisicao.footing_b)} × {_formatar_numero(requisicao.footing_l)} m"],
    ]
    if resposta.winning_material:
        dados_entrada.append(["Material otimizado", resposta.winning_material])
    tabela_entrada = Table(dados_entrada, colWidths=[6 * cm, 10 * cm])
    tabela_entrada.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
    ]))
    elementos.append(tabela_entrada)

    # 2. Casos de carga.
    elementos.append(Paragraph("2. Casos de Carga (NBR 6120)", estilo_h2))
    dados_cargas = [["Tipo", "Direção", "Valor (N)", "Nós aplicados"]]
    for caso in requisicao.load_cases:
        dados_cargas.append([
            caso.type,
            caso.direction,
            _formatar_numero(caso.value, 1),
            "Distribuído" if not caso.nodes else f"{len(caso.nodes)} nós",
        ])
    tabela_cargas = Table(dados_cargas, colWidths=[2 * cm, 2.5 * cm, 3 * cm, 8.5 * cm])
    tabela_cargas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elementos.append(tabela_cargas)

    # 3. Combinações ELU e ELS.
    elementos.append(Paragraph("3. Combinações de Carga (NBR 8681)", estilo_h2))
    elementos.append(Paragraph(
        "<b>ELU Normal:</b> 1.25·G₁ + 1.40·G₂ + 1.50·Q + 1.40·Vento<br/>"
        "<b>ELU Secundário:</b> 1.25·G₁ + 1.40·G₂ + 1.40·Q + 1.40·Vento<br/>"
        "<b>ELU Alívio:</b> 1.00·G₁ + 1.00·G₂ + 1.50·Q<br/>"
        "<b>ELS Flecha Total:</b> 1.00·G₁ + 1.00·G₂ + 1.00·Q<br/>"
        "<b>Manutenção (NBR 6120 Item 6.4):</b> 1 kN concentrado por nó do banzo superior.",
        estilo_normal,
    ))

    # 4. Tabela de esforços nas barras.
    elementos.append(PageBreak())
    elementos.append(Paragraph("4. Esforços e Verificações nas Barras (NBR 8800)", estilo_h2))
    elementos.append(Paragraph(
        "A tabela abaixo apresenta a envoltória de esforços para cada barra, "
        "com referência direta às equações da NBR 8800:2008 utilizadas.",
        estilo_normal,
    ))
    elementos.append(Spacer(1, 3 * mm))

    dados_barras = [["ID", "Grupo", "Perfil", "N (kN)", "U", "χ", "Q", "λ", "Status"]]
    for b in resposta.members:
        status = "OK" if b.utilization <= 1.0 else "VIOLADO"
        dados_barras.append([
            str(b.id),
            b.group[:20],
            b.profile,
            _formatar_numero(b.axial_force / 1000, 1),
            _formatar_numero(b.utilization, 3),
            _formatar_numero(b.fator_chi, 3),
            _formatar_numero(b.fator_q, 3),
            _formatar_numero(b.esbeltez, 0),
            status,
        ])
    tabela_barras = Table(dados_barras, colWidths=[1 * cm, 3.5 * cm, 3 * cm, 2 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm])
    tabela_barras.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elementos.append(tabela_barras)

    # 5. Equações NBR 8800 utilizadas.
    elementos.append(Paragraph("5. Equações NBR 8800:2008 Aplicadas", estilo_h2))
    elementos.append(Paragraph(
        "<b>Item 5.3.3.1 — Fator χ (flambagem global):</b><br/>"
        "χ = 0.658^λ₀² para λ₀ ≤ 1.5<br/>"
        "χ = 0.877/λ₀² para λ₀ > 1.5<br/>"
        "<br/>"
        "<b>Item 5.3.3.2 — Índice de esbeltez reduzido:</b><br/>"
        "λ₀ = √(A·Q·f<sub>y</sub> / N<sub>e</sub>)<br/>"
        "<br/>"
        "<b>Item 5.3.4.1 — Esbeltez máxima (compressão):</b> λ ≤ 200<br/>"
        "<b>Item 5.2.8.1 — Esbeltez máxima (tração):</b> λ ≤ 300<br/>"
        "<br/>"
        "<b>Item 5.5.1.2 — Interação N + M:</b><br/>"
        "Para N/N<sub>rd</sub> ≥ 0.2: N/N<sub>rd</sub> + 8/9·(M<sub>sd</sub>/M<sub>rd</sub>) ≤ 1.0<br/>"
        "Para N/N<sub>rd</sub> &lt; 0.2: N/(2·N<sub>rd</sub>) + M<sub>sd</sub>/M<sub>rd</sub> ≤ 1.0<br/>"
        "<br/>"
        "<b>Anexo F — Flambagem local (Fator Q):</b> largura efetiva para b/t > λ<sub>r</sub>.",
        estilo_normal,
    ))

    # 6. Vento (NBR 6123).
    if requisicao.parametros_vento:
        elementos.append(Paragraph("6. Cargas de Vento (NBR 6123:1988)", estilo_h2))
        pv = requisicao.parametros_vento
        elementos.append(Paragraph(
            f"<b>V₀:</b> {pv.v0_mps} m/s<br/>"
            f"<b>S1 · S2 · S3:</b> {pv.s1} · {pv.s2} · {pv.s3}<br/>"
            f"<b>V<sub>k</sub></b> = V₀·S1·S2·S3 = {pv.v0_mps * pv.s1 * pv.s2 * pv.s3:.2f} m/s<br/>"
            f"<b>q</b> = 0.613·V<sub>k</sub>² = {0.613 * (pv.v0_mps * pv.s1 * pv.s2 * pv.s3)**2:.2f} N/m²<br/>"
            f"<b>Ce - Ci:</b> {pv.ce_externo - pv.ci_interno}<br/>"
            f"<b>Direção:</b> {pv.direcao_vento_graus}°",
            estilo_normal,
        ))

    # 7. Resultado final.
    elementos.append(Paragraph("7. Resultado da Otimização", estilo_h2))
    elementos.append(Paragraph(
        f"<b>Peso total:</b> {_formatar_numero(resposta.total_weight)} kg<br/>"
        f"<b>Custo estimado:</b> R$ {_formatar_numero(resposta.total_cost)}<br/>"
        f"<b>Material vencedor:</b> {resposta.winning_material}<br/>"
        f"<b>Utilização máxima:</b> {_formatar_numero(resposta.max_utilization * 100, 1)}%<br/>"
        f"<b>Flecha máxima:</b> {_formatar_numero(resposta.max_deflection * 1000, 2)} mm "
        f"(limite L/{250} = {_formatar_numero(resposta.real_span / 250 * 1000, 2)} mm)<br/>"
        f"<b>Contra-flecha recomendada:</b> {_formatar_numero(resposta.precamber * 1000, 2)} mm<br/>"
        f"<b>Perfis distintos:</b> {resposta.num_perfis_distintos}<br/>"
        f"<b>Tempo de execução:</b> {_formatar_numero(resposta.tempo_execucao_segundos, 1)} s<br/>"
        f"<b>Gerações do GA:</b> {resposta.geracoes_executadas}<br/>"
        f"<b>Estrutura estável:</b> {'SIM' if resposta.is_structurally_stable else 'NÃO'}",
        estilo_normal,
    ))

    # 8. Lista de barras críticas.
    barras_criticas = sorted(resposta.members, key=lambda b: -b.utilization)[:5]
    if barras_criticas:
        elementos.append(Paragraph("8. Barras Mais Solicitadas", estilo_h2))
        for b in barras_criticas:
            elementos.append(Paragraph(
                f"<b>Barra {b.id}</b> ({b.group}, perfil {b.profile}): "
                f"N<sub>sd</sub> = {_formatar_numero(b.axial_force / 1000, 1)} kN, "
                f"N<sub>rd</sub> = {_formatar_numero(b.n_rd / 1000, 1)} kN, "
                f"U = {_formatar_numero(b.utilization, 3)}, "
                f"χ = {_formatar_numero(b.fator_chi, 3)}, "
                f"Q = {_formatar_numero(b.fator_q, 3)}, "
                f"λ = {_formatar_numero(b.esbeltez, 0)}.",
                estilo_normal,
            ))

    # Rodapé.
    elementos.append(Spacer(1, 10 * mm))
    elementos.append(Paragraph(
        "<i>Memorial gerado automaticamente por TRUSS-OPT 3D. As verificações seguem "
        "as normas NBR 8800:2008, NBR 6120:2019 e NBR 6123:1988. Em caso de divergência, "
        "prevalecem os textos originais das normas.</i>",
        ParagraphStyle("Rodape", parent=estilo_normal, fontSize=7, textColor=colors.grey),
    ))

    doc.build(elementos)
    return buffer.getvalue()


def gerar_memorial_docx(
    requisicao: RequisicaoOtimizacao,
    resposta: RespostaOtimizacao,
) -> bytes:
    """Gera o memorial de cálculo em formato DOCX."""
    doc = Document()

    # Cabeçalho.
    titulo = doc.add_heading("Memorial de Cálculo Estrutural", level=0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(
        f"TRUSS-OPT 3D — Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
    )

    # 1. Dados de entrada.
    doc.add_heading("1. Dados de Entrada", level=1)
    for rotulo, valor in [
        ("Vão (L)", f"{requisicao.length} m"),
        ("Altura (H)", f"{requisicao.height} m"),
        ("Largura (W)", f"{requisicao.width} m"),
        ("Divisões", f"{requisicao.divisions}"),
        ("Tipo de solo", requisicao.soil_type),
        ("Material otimizado", resposta.winning_material),
    ]:
        doc.add_paragraph(f"{rotulo}: {valor}", style="List Bullet")

    # 2. Casos de carga.
    doc.add_heading("2. Casos de Carga (NBR 6120)", level=1)
    tabela = doc.add_table(rows=1, cols=4)
    tabela.style = "Light Grid Accent 1"
    hdr = tabela.rows[0].cells
    hdr[0].text = "Tipo"
    hdr[1].text = "Direção"
    hdr[2].text = "Valor (N)"
    hdr[3].text = "Aplicação"
    for caso in requisicao.load_cases:
        linha = tabela.add_row().cells
        linha[0].text = caso.type
        linha[1].text = caso.direction
        linha[2].text = f"{caso.value:.1f}"
        linha[3].text = "Distribuído" if not caso.nodes else f"{len(caso.nodes)} nós"

    # 3. Combinações.
    doc.add_heading("3. Combinações de Carga (NBR 8681)", level=1)
    for combo in [
        "ELU Normal: 1.25·G₁ + 1.40·G₂ + 1.50·Q + 1.40·Vento",
        "ELU Secundário: 1.25·G₁ + 1.40·G₂ + 1.40·Q + 1.40·Vento",
        "ELU Alívio: 1.00·G₁ + 1.00·G₂ + 1.50·Q",
        "ELS Flecha: 1.00·G₁ + 1.00·G₂ + 1.00·Q",
        "Manutenção (NBR 6120 item 6.4): 1 kN por nó do banzo superior",
    ]:
        doc.add_paragraph(combo, style="List Bullet")

    # 4. Esforços nas barras.
    doc.add_heading("4. Esforços e Verificações nas Barras (NBR 8800)", level=1)
    tabela = doc.add_table(rows=1, cols=7)
    tabela.style = "Light Grid Accent 1"
    hdr = tabela.rows[0].cells
    for i, titulo_col in enumerate(["ID", "Grupo", "Perfil", "N (kN)", "U", "χ", "Status"]):
        hdr[i].text = titulo_col
    for b in resposta.members:
        linha = tabela.add_row().cells
        linha[0].text = str(b.id)
        linha[1].text = b.group
        linha[2].text = b.profile
        linha[3].text = f"{b.axial_force/1000:.1f}"
        linha[4].text = f"{b.utilization:.3f}"
        linha[5].text = f"{b.fator_chi:.3f}"
        linha[6].text = "OK" if b.utilization <= 1.0 else "VIOLADO"

    # 5. Equações.
    doc.add_heading("5. Equações NBR 8800:2008 Aplicadas", level=1)
    doc.add_paragraph(
        "Item 5.3.3.1 — Fator χ: χ = 0.658^λ₀² (λ₀ ≤ 1.5); χ = 0.877/λ₀² (λ₀ > 1.5).\n"
        "Item 5.3.3.2 — λ₀ = √(A·Q·fy / Ne).\n"
        "Item 5.3.4.1 — Esbeltez máxima (compressão): λ ≤ 200.\n"
        "Item 5.2.8.1 — Esbeltez máxima (tração): λ ≤ 300.\n"
        "Item 5.5.1.2 — Interação N+M: N/N_rd + 8/9·(M_sd/M_rd) ≤ 1.0 (se N/N_rd ≥ 0.2).\n"
        "Anexo F — Fator Q (flambagem local): largura efetiva para b/t > λ_r."
    )

    # 6. Resultado.
    doc.add_heading("6. Resultado da Otimização", level=1)
    for rotulo, valor in [
        ("Peso total", f"{resposta.total_weight:.2f} kg"),
        ("Custo estimado", f"R$ {resposta.total_cost:.2f}"),
        ("Material vencedor", resposta.winning_material),
        ("Utilização máxima", f"{resposta.max_utilization*100:.1f}%"),
        ("Flecha máxima", f"{resposta.max_deflection*1000:.2f} mm"),
        ("Contra-flecha", f"{resposta.precamber*1000:.2f} mm"),
        ("Estrutura estável", "SIM" if resposta.is_structurally_stable else "NÃO"),
    ]:
        doc.add_paragraph(f"{rotulo}: {valor}", style="List Bullet")

    # Serializa para bytes.
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def codificar_base64(conteudo: bytes) -> str:
    """Codifica bytes em base64 string (para armazenar no PostgreSQL)."""
    return base64.b64encode(conteudo).decode("ascii")


def decodificar_base64(conteudo_b64: str) -> bytes:
    """Decodifica base64 string para bytes."""
    return base64.b64decode(conteudo_b64.encode("ascii"))
