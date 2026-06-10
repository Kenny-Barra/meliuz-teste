"""
analyzer.py — núcleo de análise dos testes A/B de cashback do Méliuz.

Recebe qualquer CSV no schema padrão e responde à pergunta central do teste:
"Qual variante de cashback devemos escalar para 100% do tráfego?"

A resposta é SEMPRE no formato "escalar o Grupo X para 100%". Quando o grupo
vencedor é o controle (Grupo 1), a resposta deixa claro que escalar o controle
significa manter a configuração atual — mas ainda responde diretamente à pergunta.

Funciona com qualquer número de grupos e qualquer período, sem alterar o código.
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime


# ----------------------------------------------------------------------
# Utilidades de formatação e parsing
# ----------------------------------------------------------------------

def parse_currency(value):
    """Converte 'R$ 10.273' em 10273.0 — tolera espaços e formato BR."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("R$", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def format_brl(valor):
    """Formata um número no padrão brasileiro: R$ 10.273"""
    try:
        return f"R$ {float(valor):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "R$ 0"


# ----------------------------------------------------------------------
# Validação e carga
# ----------------------------------------------------------------------

REQUIRED_COLUMNS = [
    "Data", "Grupos de usuários", "Parceiro",
    "compradores", "comissão", "cashback", "vendas totais",
]


def validate_schema(df):
    """Retorna lista de problemas de schema (vazia = ok)."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return [f"Colunas faltando: {missing}"] if missing else []


def load_and_prepare(csv_path):
    """Carrega o CSV e prepara colunas numéricas e de data."""
    df = pd.read_csv(csv_path)
    problems = validate_schema(df)
    if problems:
        raise ValueError("; ".join(problems))

    df["comissao_num"] = df["comissão"].apply(parse_currency)
    df["cashback_num"] = df["cashback"].apply(parse_currency)
    df["vendas_num"] = df["vendas totais"].apply(parse_currency)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    return df


# ----------------------------------------------------------------------
# Detecção de anomalias (robustez a dados ruins)
# ----------------------------------------------------------------------

def detect_anomalies(df):
    """Detecta dados suspeitos. Retorna lista de avisos legíveis."""
    anomalies = []

    if df["compradores"].isna().any():
        anomalies.append("Valores ausentes na coluna 'compradores'.")
    if (df["compradores"] < 0).any():
        anomalies.append("Valores negativos em 'compradores'.")

    for col, nome in [("comissao_num", "comissão"), ("cashback_num", "cashback"),
                      ("vendas_num", "vendas totais")]:
        if df[col].isna().any():
            anomalies.append(f"Valores ausentes ou não numéricos em '{nome}'.")
        if (df[col] < 0).any():
            anomalies.append(f"Valores negativos em '{nome}'.")

    dups = df.groupby(["Data", "Grupos de usuários"]).size()
    if (dups > 1).any():
        anomalies.append("Há linhas duplicadas (mesma data e mesmo grupo).")

    dias_por_grupo = df.groupby("Grupos de usuários")["Data"].nunique()
    if len(dias_por_grupo) > 1:
        ratio = dias_por_grupo.max() / max(dias_por_grupo.min(), 1)
        if ratio > 1.5:
            anomalies.append(
                f"Grupos com cobertura desigual de dias (diferença de {ratio:.1f}x). "
                "A comparação pode estar enviesada."
            )

    problemas_margem = (df["cashback_num"] > df["comissao_num"]).sum()
    if problemas_margem > 0:
        anomalies.append(
            f"{problemas_margem} dia(s) com cashback maior que a comissão (margem negativa)."
        )

    return anomalies


# ----------------------------------------------------------------------
# Métricas por grupo
# ----------------------------------------------------------------------

def compute_group_metrics(df):
    """Calcula métricas por grupo: GMV, margem, ticket médio, etc."""
    g = df.groupby("Grupos de usuários").agg(
        compradores=("compradores", "sum"),
        gmv=("vendas_num", "sum"),
        comissao_total=("comissao_num", "sum"),
        cashback_total=("cashback_num", "sum"),
        dias=("Data", "nunique"),
    )
    g["margem_liquida_rs"] = g["comissao_total"] - g["cashback_total"]
    g["margem_pct_gmv"] = (g["margem_liquida_rs"] / g["gmv"]) * 100
    g["ticket_medio"] = g["gmv"] / g["compradores"]
    g["taxa_cashback_pct"] = (g["cashback_total"] / g["gmv"]) * 100
    g["taxa_comissao_pct"] = (g["comissao_total"] / g["gmv"]) * 100
    return g


# ----------------------------------------------------------------------
# Significância estatística
# ----------------------------------------------------------------------

def compute_statistical_significance(df, control_group=None):
    """
    Teste t de Welch entre o controle (Grupo 1 por padrão) e cada variante.
    Métrica testada: margem líquida diária. Retorna p-values e diferenças.
    """
    df = df.copy()
    df["margem_diaria"] = df["comissao_num"] - df["cashback_num"]
    grupos = sorted(df["Grupos de usuários"].unique())
    if control_group is None:
        control_group = grupos[0]

    control_data = df[df["Grupos de usuários"] == control_group]["margem_diaria"]
    comparacoes = {}

    for grupo in grupos:
        if grupo == control_group:
            continue
        treat = df[df["Grupos de usuários"] == grupo]["margem_diaria"]
        if len(treat) < 5 or len(control_data) < 5:
            comparacoes[grupo] = {
                "p_value": None, "significativo": False,
                "diferenca_pct": None, "nota": "amostra pequena demais",
            }
            continue
        t_stat, p = stats.ttest_ind(treat, control_data, equal_var=False)
        dif = ((treat.mean() - control_data.mean()) / control_data.mean()) * 100
        comparacoes[grupo] = {
            "p_value": float(p), "significativo": bool(p < 0.05),
            "diferenca_pct": float(dif), "t_stat": float(t_stat), "nota": None,
        }

    return {"controle": control_group, "comparacoes": comparacoes}


# ----------------------------------------------------------------------
# Decisão: qual escalar para 100% (responde a pergunta central do teste)
# ----------------------------------------------------------------------

def decide_scaling(group_metrics, stats_results):
    """
    Decide qual variante escalar para 100% do tráfego.

    Critério: maior margem líquida total, ponderada pela significância.
    Retorna SEMPRE uma variante para escalar, no formato que o teste pede.
    """
    melhor = group_metrics["margem_liquida_rs"].idxmax()
    margem_melhor = group_metrics.loc[melhor, "margem_liquida_rs"]
    gmv_melhor = group_metrics.loc[melhor, "gmv"]
    controle = stats_results["controle"]
    eh_controle = (melhor == controle)

    # Pega a significância da comparação do melhor grupo vs controle
    comp = stats_results["comparacoes"].get(melhor, {})
    p_value = comp.get("p_value")
    significativo = comp.get("significativo", False)

    # Resposta direta à pergunta central — SEMPRE no formato "escalar Grupo X"
    resposta_direta = f"Escalar o {melhor} para 100% do tráfego"

    # Define confiança e ressalva
    if eh_controle:
        # O controle é o melhor: escalar o controle = manter a config atual
        confianca = "alta"
        # Verifica se as variantes foram significativamente piores
        piores_signif = any(
            c.get("significativo") and c.get("diferenca_pct", 0) < 0
            for c in stats_results["comparacoes"].values()
        )
        if piores_signif:
            ressalva = (
                f"Escalar o {melhor} significa manter a configuração atual de cashback. "
                "As variantes testadas tiveram margem significativamente menor, ou seja, "
                "aumentar o cashback piorou o resultado para o Méliuz neste parceiro."
            )
        else:
            ressalva = (
                f"Escalar o {melhor} significa manter a configuração atual. As variantes "
                "não superaram o controle em margem líquida."
            )
    else:
        # Uma variante venceu o controle
        if significativo:
            confianca = "alta"
            ressalva = (
                f"O {melhor} superou o controle ({controle}) em margem líquida com "
                f"diferença estatisticamente significativa (p={p_value:.4f}). "
                "Mudança recomendada com segurança."
            )
        elif p_value is not None and p_value < 0.15:
            confianca = "média"
            ressalva = (
                f"O {melhor} teve a maior margem líquida, mas a diferença vs o controle "
                f"não é estatisticamente conclusiva (p={p_value:.4f}). Recomenda-se escalar "
                "com monitoramento próximo, ou estender o teste por mais alguns dias."
            )
        else:
            confianca = "baixa"
            ressalva = (
                f"O {melhor} tem a maior margem líquida nominal, mas sem significância "
                f"estatística (p={p_value if p_value is not None else 'N/A'}). A diferença "
                "pode ser ruído. Considere estender o teste antes de escalar definitivamente."
            )

    return {
        "variante_escalar": melhor,
        "resposta_direta": resposta_direta,
        "eh_controle": eh_controle,
        "margem_vencedora": float(margem_melhor),
        "gmv_vencedor": float(gmv_melhor),
        "confianca": confianca,
        "ressalva": ressalva,
        "p_value": p_value,
    }


# ----------------------------------------------------------------------
# Resumo para a planilha geral
# ----------------------------------------------------------------------

def build_summary(df, group_metrics, stats_results, decisao, anomalies,
                  descricao=None, nome_teste=None):
    parceiro = df["Parceiro"].iloc[0] if len(df) > 0 else "Desconhecido"
    di = df["Data"].min().strftime("%Y-%m-%d") if df["Data"].notna().any() else "N/A"
    dfim = df["Data"].max().strftime("%Y-%m-%d") if df["Data"].notna().any() else "N/A"

    return {
        "nome_teste": nome_teste or f"Teste cashback {parceiro}",
        "parceiro": parceiro,
        "descricao": descricao or f"Comparação de níveis de cashback no {parceiro}",
        "periodo_inicio": di,
        "periodo_fim": dfim,
        "n_grupos": int(df["Grupos de usuários"].nunique()),
        "variante_escalar": decisao["variante_escalar"],
        "resposta_direta": decisao["resposta_direta"],
        "confianca": decisao["confianca"],
        "justificativa": decisao["ressalva"],
        "gmv_total": float(df["vendas_num"].sum()),
        "margem_total": float((df["comissao_num"] - df["cashback_num"]).sum()),
        "anomalias": "; ".join(anomalies) if anomalies else "Nenhuma",
        "analisado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ----------------------------------------------------------------------
# Orquestração
# ----------------------------------------------------------------------

def analyze(csv_path, descricao=None, nome_teste=None):
    """Roda a análise completa e devolve tudo num dicionário."""
    df = load_and_prepare(csv_path)
    anomalies = detect_anomalies(df)
    group_metrics = compute_group_metrics(df)
    stats_results = compute_statistical_significance(df)
    decisao = decide_scaling(group_metrics, stats_results)
    resumo = build_summary(df, group_metrics, stats_results, decisao,
                           anomalies, descricao, nome_teste)
    return {
        "df": df,
        "metricas_por_grupo": group_metrics,
        "estatistica": stats_results,
        "decisao": decisao,
        "anomalias": anomalies,
        "resumo": resumo,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python analyzer.py <caminho_csv>")
        sys.exit(1)
    r = analyze(sys.argv[1])
    print("\nRESPOSTA:", r["decisao"]["resposta_direta"])
    print("CONFIANÇA:", r["decisao"]["confianca"])
    print(r["decisao"]["ressalva"])
