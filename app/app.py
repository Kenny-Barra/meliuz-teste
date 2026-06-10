"""
App web do Analisador de Testes A/B do Méliuz (Opção A).

Três abas:
  1. Nova análise  — upload do CSV, nome + descrição, resultado e relatório (MD/PDF)
  2. Histórico     — lista completa com filtro; cada teste reexibe gráficos e métricas
  3. Planilha geral — sincroniza CSV local + Google Sheets, mostra e exporta

A resposta à pergunta central ("qual variante escalar para 100%") aparece em
destaque no topo de cada análise.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from analyzer import (
    analyze, format_brl, load_and_prepare, detect_anomalies,
    compute_group_metrics, compute_statistical_significance, decide_scaling,
)
from report import generate, markdown_to_pdf_bytes
import sheets

ROOT = Path(__file__).resolve().parent.parent
HISTORICO_DIR = ROOT / "historico"
HISTORICO_DIR.mkdir(exist_ok=True)


def init_state():
    for k in ("resultado", "relatorio_md", "usou_ia", "motivo_ia", "csv_name"):
        st.session_state.setdefault(k, None)
    st.session_state.setdefault("flash", None)


def set_flash(escopo, tipo, texto):
    """Guarda uma mensagem para mostrar na aba indicada após o rerun."""
    st.session_state[f"flash_{escopo}"] = (tipo, texto)


def show_flash(escopo):
    """Exibe e limpa a mensagem pendente daquela aba, se houver."""
    chave = f"flash_{escopo}"
    flash = st.session_state.get(chave)
    if flash:
        tipo, texto = flash
        {"success": st.success, "info": st.info, "warning": st.warning,
         "error": st.error}.get(tipo, st.info)(texto)
        st.session_state[chave] = None


def _apagar_historico_por_nome(nome_teste):
    """Remove do histórico (pasta) a análise cujo nome de teste bate.
    Como os nomes são únicos, casa pelo nome guardado no meta.json."""
    import shutil
    alvo = str(nome_teste).strip().lower()
    if not alvo or not HISTORICO_DIR.exists():
        return 0
    removidos = 0
    for pasta in HISTORICO_DIR.iterdir():
        meta = pasta / "meta.json"
        if pasta.is_dir() and meta.exists():
            try:
                d = json.loads(meta.read_text(encoding="utf-8"))
                nome = str(d.get("resumo", {}).get("nome_teste", "")).strip().lower()
            except Exception:
                nome = ""
            if nome == alvo:
                shutil.rmtree(pasta, ignore_errors=True)
                removidos += 1
    return removidos


def _cb_apagar_planilha():
    """Callback do botão apagar (Planilha geral). Lê as linhas marcadas no
    data_editor, apaga, e limpa a seleção — tudo antes do rerun automático."""
    editor_state = st.session_state.get("pl_editor", {})
    edited = editor_state.get("edited_rows", {}) if isinstance(editor_state, dict) else {}
    marcados = [int(i) for i, ch in edited.items() if ch.get("Apagar")]
    filtrados = st.session_state.get("pl_filtrados", [])

    total_online, n = 0, 0
    for i in marcados:
        if 0 <= i < len(filtrados):
            reg = filtrados[i]
            res = sheets.delete_registro(reg)
            total_online += 1 if res.get("online") else 0
            # Apaga também do histórico (pelo nome do teste)
            _apagar_historico_por_nome(reg.get("nome_teste", ""))
            n += 1

    msg = f"✅ {n} teste(s) apagado(s) com sucesso."
    if sheets._sheets_configured():
        msg += f" ({total_online} removido(s) também da planilha online.)"
    msg += " Dados atualizados."
    set_flash("planilha", "success", msg)
    # Limpa o editor e a confirmação (renascem na próxima renderização)
    st.session_state.pop("pl_editor", None)
    st.session_state.pop("pl_del_conf", None)


def _cb_apagar_historico(pasta_str, resumo):
    """Callback do botão apagar (Histórico)."""
    import shutil
    shutil.rmtree(pasta_str, ignore_errors=True)
    sheets.delete_registro(resumo)
    set_flash("historico", "success", "✅ Teste apagado com sucesso. Dados atualizados.")


# ----------------------------------------------------------------------
# Persistência local do histórico
# ----------------------------------------------------------------------

def salvar_historico(csv_bytes, csv_name, resultado, relatorio_md):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta = HISTORICO_DIR / f"{ts}_{resultado['resumo']['parceiro'].replace(' ', '_')}"
    pasta.mkdir(exist_ok=True)
    (pasta / csv_name).write_bytes(csv_bytes)
    (pasta / "relatorio.md").write_text(relatorio_md, encoding="utf-8")
    (pasta / "meta.json").write_text(json.dumps({
        "csv_name": csv_name,
        "resumo": resultado["resumo"],
        "decisao": resultado["decisao"],
        "anomalias": resultado["anomalias"],
    }, default=str, ensure_ascii=False, indent=2))


def carregar_historico():
    items = []
    for pasta in sorted(HISTORICO_DIR.iterdir(), reverse=True):
        meta = pasta / "meta.json"
        if pasta.is_dir() and meta.exists():
            d = json.loads(meta.read_text(encoding="utf-8"))
            d["_pasta"] = str(pasta)
            items.append(d)
    return items


def reconstruir(csv_path, resumo):
    df = load_and_prepare(str(csv_path))
    gm = compute_group_metrics(df)
    sr = compute_statistical_significance(df)
    return {
        "df": df, "metricas_por_grupo": gm, "estatistica": sr,
        "decisao": decide_scaling(gm, sr),
        "anomalias": detect_anomalies(df), "resumo": resumo,
    }


# ----------------------------------------------------------------------
# Renderização compartilhada
# ----------------------------------------------------------------------

def render_decisao(decisao):
    st.markdown(f"### ➡️ {decisao['resposta_direta']}")
    cor = {"alta": st.success, "média": st.warning, "baixa": st.error}.get(
        decisao["confianca"], st.info
    )
    cor(f"**Confiança: {decisao['confianca']}** — {decisao['ressalva']}")


def render_metricas(gm, decisao):
    cols = st.columns(min(len(gm), 4))
    for i, (grupo, r) in enumerate(gm.iterrows()):
        with cols[i % len(cols)]:
            destaque = "🏆 " if grupo == decisao["variante_escalar"] else ""
            st.metric(destaque + grupo, format_brl(r["margem_liquida_rs"]),
                      f"GMV: {format_brl(r['gmv'])}")


def render_graficos(df, gm):
    t1, t2, t3 = st.tabs(["Margem por grupo", "GMV no tempo", "Margem % vs Cashback %"])
    with t1:
        st.bar_chart(pd.DataFrame({
            "Margem líquida (R$)": gm["margem_liquida_rs"],
            "GMV (R$)": gm["gmv"],
        }))
    with t2:
        st.line_chart(df.pivot_table(index="Data", columns="Grupos de usuários",
                                     values="vendas_num", aggfunc="sum"))
    with t3:
        st.bar_chart(gm[["margem_pct_gmv", "taxa_cashback_pct"]])


def render_resultado(resultado, relatorio_md, prefixo):
    render_decisao(resultado["decisao"])
    st.subheader("Métricas por grupo")
    render_metricas(resultado["metricas_por_grupo"], resultado["decisao"])
    st.dataframe(resultado["metricas_por_grupo"].round(2), use_container_width=True)
    st.subheader("Gráficos")
    render_graficos(resultado["df"], resultado["metricas_por_grupo"])
    if resultado["anomalias"]:
        st.warning("**Anomalias detectadas:**\n" + "\n".join(f"- {a}" for a in resultado["anomalias"]))
    if relatorio_md:
        with st.expander("Ver relatório completo"):
            st.markdown(relatorio_md)
        botoes_download(relatorio_md, resultado["resumo"]["parceiro"], prefixo)


def botoes_download(relatorio_md, parceiro, prefixo):
    slug = parceiro.replace(" ", "_")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📄 Baixar relatório (.md)", relatorio_md,
                           file_name=f"relatorio_{slug}.md", mime="text/markdown",
                           key=f"md_{prefixo}", use_container_width=True)
    with c2:
        try:
            pdf = markdown_to_pdf_bytes(relatorio_md)
            st.download_button("📕 Baixar relatório (.pdf)", pdf,
                               file_name=f"relatorio_{slug}.pdf", mime="application/pdf",
                               key=f"pdf_{prefixo}", use_container_width=True)
        except Exception as e:
            st.caption(f"PDF indisponível: {e}")
    with c3:
        st.download_button("📊 Baixar planilha geral (.csv)", sheets.get_csv_bytes(),
                           file_name="resultados_meliuz_ab.csv", mime="text/csv",
                           key=f"csv_{prefixo}", use_container_width=True)


# ----------------------------------------------------------------------
# Aba 1 — Nova análise
# ----------------------------------------------------------------------

def aba_nova_analise():
    show_flash("nova")
    st.header("Nova análise")
    st.caption("Envie o CSV de um teste A/B e receba a recomendação de qual variante escalar para 100%.")

    # Contador para reiniciar os campos após uma análise (sem apagar o resultado)
    st.session_state.setdefault("na_n", 0)
    n = st.session_state["na_n"]

    arq = st.file_uploader("Arraste o CSV ou clique para selecionar", type=["csv"],
                           key=f"na_file_{n}",
                           help="Colunas: Data, Grupos de usuários, Parceiro, compradores, comissão, cashback, vendas totais")
    c1, c2 = st.columns(2)
    nome = c1.text_input("Nome do teste *", key=f"na_nome_{n}",
                         placeholder="Ex: Cashback Parceiro A — Q1 2025")
    desc = c2.text_input("Descrição do teste *", key=f"na_desc_{n}",
                         placeholder="Ex: 5% vs 10% vs 15% de cashback")

    if arq and st.button("Analisar teste", type="primary", use_container_width=True):
        if not nome.strip() or not desc.strip():
            st.error("Nome e descrição são obrigatórios para registrar o teste na planilha.")
            return
        # Impede nome repetido (compara com todos os testes locais e online)
        if nome.strip().lower() in sheets.nomes_existentes():
            st.error(f"Já existe um teste com o nome '{nome.strip()}'. Escolha outro nome.")
            return
        prog = st.progress(0, text="Lendo arquivo...")
        try:
            csv_bytes = arq.getvalue()
            tmp = ROOT / "tmp_upload.csv"
            tmp.write_bytes(csv_bytes)
            prog.progress(30, text="Calculando métricas...")
            resultado = analyze(str(tmp), descricao=desc, nome_teste=nome)
            prog.progress(60, text="Gerando relatório...")
            relatorio_md, usou_ia, motivo = generate(resultado, descricao=desc)
            prog.progress(85, text="Salvando...")
            salvar_historico(csv_bytes, arq.name, resultado, relatorio_md)
            info = sheets.salvar(resultado["resumo"])
            prog.progress(100, text="Concluído!")
            prog.empty()
            tmp.unlink(missing_ok=True)

            st.session_state.update(resultado=resultado, relatorio_md=relatorio_md,
                                    usou_ia=usou_ia, motivo_ia=motivo, csv_name=arq.name)
            msg = "✅ Análise concluída e salva na planilha geral."
            if info["sheets"]:
                msg += " (gravada também no Google Sheets)"
            if usou_ia:
                msg += " 🧠 " + motivo
            else:
                msg += " ℹ️ " + motivo
            set_flash("nova", "success", msg)
            # Limpa os campos de entrada (mantém o resultado, que está em session_state)
            st.session_state["na_n"] += 1
            st.rerun()
        except Exception as e:
            prog.empty()
            st.error(f"Não foi possível analisar o arquivo: {e}")
            return

    if st.session_state.resultado:
        st.divider()
        render_resultado(st.session_state.resultado, st.session_state.relatorio_md, "novo")


# ----------------------------------------------------------------------
# Aba 2 — Histórico
# ----------------------------------------------------------------------

def aba_historico():
    show_flash("historico")
    st.header("Histórico de testes")
    st.caption("Todos os testes analisados. Clique para reabrir gráficos, métricas e relatório.")
    items = carregar_historico()
    if not items:
        st.info("Nenhuma análise ainda. Faça a primeira na aba 'Nova análise'.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Testes rodados", len(items))
    c2.metric("Com confiança alta", sum(1 for i in items if i["decisao"]["confianca"] == "alta"))
    c3.metric("Último teste", items[0]["resumo"]["analisado_em"][:10])
    st.divider()

    parceiros = sorted(set(i["resumo"]["parceiro"] for i in items))
    c1, c2, c3 = st.columns(3)
    with c1:
        busca = st.text_input("Buscar por nome do teste", placeholder="digite parte do nome")
    with c2:
        filtro_parceiro = st.multiselect("Parceiro", parceiros, default=[])
    with c3:
        datas = sorted(set(i["resumo"]["analisado_em"][:10] for i in items), reverse=True)
        filtro_data = st.multiselect("Data da análise", datas, default=[])

    def passa(item):
        nome = item["resumo"].get("nome_teste", "").lower()
        if busca and busca.lower() not in nome:
            return False
        if filtro_parceiro and item["resumo"]["parceiro"] not in filtro_parceiro:
            return False
        if filtro_data and item["resumo"]["analisado_em"][:10] not in filtro_data:
            return False
        return True

    visiveis = [i for i in items if passa(i)]
    if not visiveis:
        st.info("Nenhum teste corresponde aos filtros.")
        return

    for idx, item in enumerate(visiveis):
        resumo = item["resumo"]
        nome = resumo.get("nome_teste", resumo["parceiro"])
        cab = (f"**{nome}** · {resumo['parceiro']} · {resumo['analisado_em']} · "
               f"{item['decisao']['resposta_direta']}")
        with st.expander(cab):
            pasta = Path(item["_pasta"])
            csvs = list(pasta.glob("*.csv"))
            if not csvs:
                st.error("Arquivo original não encontrado.")
                continue
            try:
                resultado = reconstruir(csvs[0], resumo)
                rel = pasta / "relatorio.md"
                rel_md = rel.read_text(encoding="utf-8") if rel.exists() else None
                render_resultado(resultado, rel_md, f"hist{idx}")
                st.divider()
                st.markdown("**Arquivo original enviado:**")
                st.dataframe(pd.read_csv(csvs[0]).head(8), use_container_width=True)
                cc1, cc2 = st.columns([3, 1])
                with cc2:
                    conf = st.checkbox("Confirmar", key=f"conf{idx}",
                                       help="Marque para liberar o botão de apagar.")
                    st.button("🗑️ Apagar", key=f"del{idx}", use_container_width=True,
                              disabled=not conf,
                              on_click=_cb_apagar_historico,
                              args=(str(pasta), resumo))
            except Exception as e:
                st.error(f"Erro ao reabrir: {e}")


# ----------------------------------------------------------------------
# Aba 3 — Planilha geral (com sincronização)
# ----------------------------------------------------------------------

def aba_planilha():
    show_flash("planilha")
    st.header("Planilha geral de testes")
    st.caption("Une o que está salvo localmente com o que já existe na planilha do Google.")

    col_top1, col_top2 = st.columns([3, 1])
    with col_top2:
        if st.button("🔄 Atualizar dados", use_container_width=True):
            st.success("🔄 Dados atualizados.")

    if sheets._sheets_configured():
        st.success("🔗 Conectado ao Google Sheets — a lista inclui os testes que já estão na planilha online.")
        if st.button("🔁 Sincronizar com o Google Sheets",
                     help="Deixa os dois lados completos: envia o que é só local e importa o que está só na planilha."):
            try:
                enviados, importados, renomeados = sheets.sincronizar()
                partes = []
                if enviados:
                    partes.append(f"{enviados} enviado(s) para a planilha")
                if importados:
                    partes.append(f"{importados} importado(s) para o local")
                if partes:
                    msg = "✅ Sincronizado: " + " e ".join(partes) + "."
                    if renomeados:
                        msg += f" {renomeados} teste(s) com nome repetido (dados diferentes) foi(ram) renomeado(s) automaticamente."
                    st.success(msg + " Dados atualizados.")
                else:
                    st.info("ℹ️ Tudo já estava sincronizado — nada a fazer.")
            except Exception as e:
                st.error(f"Não foi possível sincronizar: {e}")
    else:
        st.caption("ℹ️ Google Sheets não configurado. Mostrando apenas os testes salvos localmente (CSV).")

    # Filtros (lidos antes da tabela)
    registros_iniciais = sheets.read_all_com_status()
    if not registros_iniciais:
        st.info("A planilha está vazia. Faça uma análise para popular.")
        return

    parceiros = sorted(set(r.get("parceiro", "") for r in registros_iniciais))
    f1, f2 = st.columns(2)
    with f1:
        fnome = st.text_input("Buscar por nome do teste", key="pl_busca",
                              placeholder="digite parte do nome")
    with f2:
        fparc = st.multiselect("Filtrar por parceiro", parceiros, default=[], key="pl_parc")

    if sheets._sheets_configured():
        st.caption("Status: 🟢 local + planilha · 🟡 só local (clique em 'Sincronizar') · 🔵 só na planilha · 🔴 conflito: mesmo nome com dados diferentes (mostra as duas versões)")

    def passa(r):
        if fnome and fnome.lower() not in r.get("nome_teste", "").lower():
            return False
        if fparc and r.get("parceiro", "") not in fparc:
            return False
        return True

    rotulo_status = {
        "ambos": "🟢 Local + Planilha",
        "so_local": "🟡 Só local (não enviado)",
        "so_online": "🔵 Só na planilha",
        "conflito_local": "🔴 Conflito — versão local",
        "conflito_online": "🔴 Conflito — versão da planilha",
    }

    filtrados = [r for r in registros_iniciais if passa(r)]
    if not filtrados:
        st.info("Nenhum teste corresponde aos filtros.")
        return
    # Guarda para o callback de apagar usar os índices corretos
    st.session_state["pl_filtrados"] = filtrados

    # Aviso de conflito: mesmo nome nos dois lados, mas dados diferentes
    nomes_conflito = {r.get("nome_teste", "") for r in filtrados
                      if r.get("_status") in ("conflito_local", "conflito_online")}
    if nomes_conflito:
        st.warning(
            f"🔴 {len(nomes_conflito)} nome(s) em conflito: existem no local e na planilha "
            "com dados diferentes (as duas versões aparecem na tabela). Clique em "
            "**Sincronizar com o Google Sheets** para renomear automaticamente a versão "
            "local (sufixo '(2)') e manter as duas."
        )

    # Monta a tabela com uma coluna "Apagar" (checkbox) na frente
    linhas = []
    for r in filtrados:
        linha = {
            "Apagar": False,
            "Status": rotulo_status.get(r.get("_status"), ""),
        }
        for col in sheets.COLUNAS:
            linha[sheets.CABECALHOS_LEGIVEIS[col]] = r.get(col, "")
        linhas.append(linha)
    df = pd.DataFrame(linhas)

    st.markdown("**Marque na coluna 'Apagar' os testes que deseja remover, depois clique no botão abaixo.**")
    edit = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        disabled=[c for c in df.columns if c != "Apagar"],
        column_config={
            "Apagar": st.column_config.CheckboxColumn("Apagar", help="Marque para apagar este teste", default=False),
        },
        key="pl_editor",
    )

    marcados = [i for i, v in enumerate(edit["Apagar"].tolist()) if v]

    c1, c2 = st.columns(2)
    c1.download_button("📥 Baixar planilha (.csv)", sheets.get_csv_bytes(),
                       file_name="resultados_meliuz_ab.csv", mime="text/csv",
                       use_container_width=True)
    import os
    url = os.environ.get("GOOGLE_SHEET_URL", "")
    if url:
        c2.link_button("🔗 Abrir no Google Sheets", url, use_container_width=True)
    else:
        c2.caption("Configure GOOGLE_SHEET_URL para o link direto.")

    # Apagar selecionados
    st.divider()
    st.caption("Apagar remove do app (CSV local) e da planilha do Google ao mesmo tempo.")
    confirmar = st.checkbox(
        f"Confirmo que quero apagar {len(marcados)} teste(s) marcado(s) — esta ação não pode ser desfeita.",
        key="pl_del_conf", disabled=not marcados)
    st.button("🗑️ Apagar selecionados", key="pl_del_btn",
              disabled=not (marcados and confirmar),
              on_click=_cb_apagar_planilha)


def main():
    st.set_page_config(page_title="Méliuz — Analisador A/B", page_icon="📊", layout="wide")
    init_state()
    st.title("📊 Analisador de testes A/B")
    st.caption("Méliuz · Growth · Qual variante de cashback escalar para 100%?")
    t1, t2, t3 = st.tabs(["🔬 Nova análise", "📚 Histórico", "📋 Planilha geral"])
    with t1:
        aba_nova_analise()
    with t2:
        aba_historico()
    with t3:
        aba_planilha()


if __name__ == "__main__":
    main()
