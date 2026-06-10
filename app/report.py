"""
report.py — gera o relatório do teste A/B em Markdown e PDF.

O relatório SEMPRE começa respondendo a pergunta central do teste
("qual variante escalar para 100%") e só depois traz a análise aprofundada.

Camadas:
- Relatório base (sem IA): resposta + tabelas + estatística + próximos passos.
- Interpretação por IA (opcional): se ANTHROPIC_API_KEY existir, a Claude API
  escreve uma leitura executiva qualitativa. Se não, o relatório sai completo
  só com os números (degradação graciosa).
"""

import os
from pathlib import Path
from analyzer import format_brl


def _pct(v, casas=1):
    try:
        return f"{float(v):.{casas}f}%".replace(".", ",")
    except (ValueError, TypeError):
        return "0,0%"


def _brl_int(v):
    return format_brl(v)


def build_metrics_table(group_metrics):
    header = (
        "| Grupo | Compradores | GMV | Comissão | Cashback | Margem líquida | Margem % GMV | Ticket médio |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for grupo, r in group_metrics.iterrows():
        compradores = f"{int(r['compradores']):,}".replace(",", ".")
        rows.append(
            f"| {grupo} | {compradores} | {_brl_int(r['gmv'])} | {_brl_int(r['comissao_total'])} | "
            f"{_brl_int(r['cashback_total'])} | {_brl_int(r['margem_liquida_rs'])} | "
            f"{_pct(r['margem_pct_gmv'])} | {_brl_int(r['ticket_medio'])} |"
        )
    return header + "\n".join(rows)


def build_stats_section(stats_results):
    controle = stats_results["controle"]
    linhas = [f"Grupo controle (referência): **{controle}**.\n"]
    if not stats_results["comparacoes"]:
        linhas.append("Apenas um grupo no teste — não há comparações estatísticas.")
        return "\n".join(linhas)

    linhas.append("| Comparação | Diferença de margem vs controle | p-value | Significativo (p<0,05)? |")
    linhas.append("|---|---|---|---|")
    for grupo, info in stats_results["comparacoes"].items():
        if info.get("nota"):
            linhas.append(f"| {grupo} vs {controle} | — | — | {info['nota']} |")
            continue
        sig = "Sim" if info["significativo"] else "Não"
        p = f"{info['p_value']:.4f}" if info["p_value"] is not None else "N/A"
        linhas.append(f"| {grupo} vs {controle} | {_pct(info['diferenca_pct'])} | {p} | {sig} |")
    return "\n".join(linhas)


def build_base_report(resultado, descricao=None):
    resumo = resultado["resumo"]
    metrics = resultado["metricas_por_grupo"]
    stats_r = resultado["estatistica"]
    decisao = resultado["decisao"]
    anomalias = resultado["anomalias"]

    m = []
    m.append(f"# Relatório do teste A/B — {resumo['nome_teste']}\n")

    # ---- RESPOSTA DIRETA À PERGUNTA CENTRAL (primeiro de tudo) ----
    m.append("## Decisão: qual variante escalar para 100%\n")
    m.append(f"### ➡️ {decisao['resposta_direta']}\n")
    m.append(f"**Nível de confiança:** {decisao['confianca']}\n")
    m.append(f"{decisao['ressalva']}\n")

    # ---- Ficha do teste ----
    m.append("## Ficha do teste\n")
    m.append(f"- **Parceiro:** {resumo['parceiro']}")
    m.append(f"- **Período:** {resumo['periodo_inicio']} a {resumo['periodo_fim']}")
    m.append(f"- **Variantes testadas:** {resumo['n_grupos']}")
    if descricao:
        m.append(f"- **Descrição:** {descricao}")
    m.append(f"- **GMV total no teste:** {_brl_int(resumo['gmv_total'])}")
    m.append(f"- **Margem líquida total:** {_brl_int(resumo['margem_total'])}\n")

    # ---- Análise aprofundada ----
    m.append("## Análise aprofundada\n")
    m.append("### Métricas por grupo\n")
    m.append(build_metrics_table(metrics) + "\n")
    m.append("### Significância estatística\n")
    m.append(build_stats_section(stats_r) + "\n")
    m.append(
        "_O p-value mede a chance de a diferença observada ser fruto do acaso. "
        "Abaixo de 0,05, consideramos a diferença real (estatisticamente significativa)._\n"
    )

    # ---- Observações ----
    m.append("### Observações sobre os dados\n")
    if anomalias:
        for a in anomalias:
            m.append(f"- ⚠️ {a}")
    else:
        m.append("Nenhuma anomalia detectada. Dados consistentes ao longo do período.")
    m.append("")

    # ---- Próximos passos ----
    m.append("### Próximos passos\n")
    if decisao["eh_controle"]:
        m.append(f"1. Manter o {decisao['variante_escalar']} (configuração atual) em 100% do tráfego do {resumo['parceiro']}.")
        m.append("2. Investigar por que aumentar o cashback não gerou GMV suficiente para compensar a margem perdida.")
        m.append("3. Testar variações mais sutis de cashback (passos menores) antes de descartar a alavanca.")
    else:
        m.append(f"1. Escalar o {decisao['variante_escalar']} para 100% do tráfego do {resumo['parceiro']}.")
        m.append("2. Monitorar GMV e margem nos 30 dias seguintes para confirmar o ganho em produção.")
        m.append("3. Testar novas variantes acima do nível vencedor para explorar o teto da curva de cashback.")
    m.append("")

    return "\n".join(m)


def enrich_with_claude(base_report, resultado, descricao=None):
    """Adiciona interpretação por IA. Retorna (relatorio, usou_ia, motivo)."""
    if "ANTHROPIC_API_KEY" not in os.environ:
        return base_report, False, "Chave da Claude API não configurada — relatório gerado sem a leitura por IA."
    try:
        from anthropic import Anthropic
        client = Anthropic()
        sp = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8")
        contexto = (
            f"Relatório técnico do teste:\n\n{base_report}\n\n"
            "Escreva apenas a seção '## Leitura executiva (por IA)' em markdown — 3 a 5 "
            "parágrafos que um gestor leria para entender o que os números significam para "
            "o negócio, o que é surpreendente e quais riscos considerar. Não repita as tabelas."
        )
        modelo = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        msg = client.messages.create(
            model=modelo, max_tokens=1500, system=sp,
            messages=[{"role": "user", "content": contexto}],
        )
        interpretacao = msg.content[0].text
        # Insere a leitura da IA logo após a decisão
        marcador = "## Ficha do teste"
        if marcador in base_report:
            partes = base_report.split(marcador, 1)
            relatorio = partes[0] + interpretacao.strip() + "\n\n" + marcador + partes[1]
        else:
            relatorio = base_report + "\n\n" + interpretacao
        return relatorio, True, "Leitura executiva gerada pela Claude API."
    except Exception as e:
        return base_report, False, f"Não foi possível usar a Claude API ({e}). Relatório gerado só com os números."


def generate(resultado, descricao=None, use_claude_api=True):
    """Gera o relatório. Retorna (markdown, usou_ia, motivo)."""
    base = build_base_report(resultado, descricao)
    if use_claude_api:
        return enrich_with_claude(base, resultado, descricao)
    return base, False, "Leitura por IA desativada nesta execução."


# ----------------------------------------------------------------------
# Geração de PDF (puro Python, sem dependências de sistema)
# ----------------------------------------------------------------------

def markdown_to_pdf_bytes(markdown_text, titulo="Relatório de teste A/B"):
    """
    Converte o relatório markdown em PDF usando fpdf2 (puro Python, funciona
    no Streamlit Cloud sem libs de sistema). Renderização simples e legível.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    W = pdf.epw

    def texto(s):
        s = (s.replace("—", "-").replace("–", "-").replace("➡️", ">")
              .replace("⚠️", "(!)").replace("“", '"').replace("”", '"')
              .replace("’", "'").replace("✦", "*"))
        return s.encode("latin-1", "replace").decode("latin-1")

    def escreve(altura, conteudo):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(W, altura, texto(conteudo))

    def desenha_tabela(linhas_tabela):
        """Renderiza uma tabela markdown como tabela real, com bordas e colunas."""
        # separa células, ignorando a linha de separador (|---|)
        linhas = []
        for lt in linhas_tabela:
            if set(lt.replace("|", "").replace("-", "").strip()) <= set(" :"):
                continue  # linha separadora
            celulas = [c.strip() for c in lt.strip().strip("|").split("|")]
            linhas.append(celulas)
        if not linhas:
            return
        n_col = max(len(r) for r in linhas)
        # larguras: primeira coluna mais larga, demais iguais
        primeira = W * 0.18
        resto = (W - primeira) / max(n_col - 1, 1)
        larguras = [primeira] + [resto] * (n_col - 1)

        line_h = 5
        for idx, linha in enumerate(linhas):
            # calcula altura necessária da linha (quebra de texto)
            pdf.set_font("Helvetica", "B" if idx == 0 else "", 7)
            alturas = []
            for j in range(n_col):
                txt = texto(linha[j] if j < len(linha) else "")
                n_linhas = len(pdf.multi_cell(larguras[j], line_h, txt, dry_run=True, output="LINES"))
                alturas.append(max(n_linhas, 1) * line_h)
            h = max(alturas)
            # checa quebra de página
            if pdf.get_y() + h > pdf.page_break_trigger:
                pdf.add_page()
            x0, y0 = pdf.get_x(), pdf.get_y()
            x = x0
            for j in range(n_col):
                txt = texto(linha[j] if j < len(linha) else "")
                pdf.set_xy(x, y0)
                if idx == 0:
                    pdf.set_fill_color(74, 21, 75)
                    pdf.set_text_color(255, 255, 255)
                    pdf.multi_cell(larguras[j], h, txt, border=1, align="C", fill=True,
                                   max_line_height=line_h)
                else:
                    pdf.set_text_color(0, 0, 0)
                    pdf.multi_cell(larguras[j], h, txt, border=1, align="C",
                                   max_line_height=line_h)
                x += larguras[j]
            pdf.set_xy(x0, y0 + h)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    linhas = markdown_text.split("\n")
    i = 0
    while i < len(linhas):
        l = linhas[i].rstrip()
        if not l:
            pdf.ln(3); i += 1; continue
        if l.startswith("|"):
            # agrupa todas as linhas consecutivas da tabela
            bloco = []
            while i < len(linhas) and linhas[i].lstrip().startswith("|"):
                bloco.append(linhas[i]); i += 1
            desenha_tabela(bloco)
            continue
        if l.startswith("# "):
            pdf.set_font("Helvetica", "B", 16); escreve(8, l[2:]); pdf.ln(1)
        elif l.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            escreve(7, l.replace("### ", "").replace("➡️", ">").strip())
        elif l.startswith("## "):
            pdf.set_font("Helvetica", "B", 13); pdf.ln(2); escreve(7, l[3:])
        elif l.startswith("- ") or l[:2] in ("1.", "2.", "3."):
            pdf.set_font("Helvetica", "", 10)
            escreve(6, "  " + l.replace("**", "").replace("⚠️", "(!)"))
        else:
            pdf.set_font("Helvetica", "", 10)
            escreve(6, l.replace("**", "").replace("_", "").replace("`", ""))
        i += 1

    return bytes(pdf.output())
