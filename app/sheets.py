"""
sheets.py — planilha de acompanhamento (CSV local + Google Sheets).

Camada 1 — CSV local (resultados.csv): sempre funciona, sem configuração.
  Separador ';' e BOM UTF-8, abre formatado no Excel/Sheets em português.

Camada 2 — Google Sheets via Apps Script (opcional, sem Google Cloud):
  - escreve novas linhas (POST),
  - apaga linhas (POST),
  - lê a planilha inteira (GET) para sincronizar.

O Apps Script força as células como texto, então os valores voltam idênticos
aos enviados — o que garante a deduplicação correta na sincronização.
"""

import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "resultados.csv"
DELIMITER = ";"

COLUNAS = [
    "nome_teste", "descricao", "parceiro", "periodo_inicio", "periodo_fim",
    "n_grupos", "variante_escalar", "resposta_direta", "confianca",
    "justificativa", "gmv_total", "margem_total", "anomalias", "analisado_em",
]

CABECALHOS_LEGIVEIS = {
    "nome_teste": "Nome do teste",
    "descricao": "Descrição",
    "parceiro": "Parceiro",
    "periodo_inicio": "Início",
    "periodo_fim": "Fim",
    "n_grupos": "Nº grupos",
    "variante_escalar": "Variante a escalar",
    "resposta_direta": "Decisão (100% do tráfego)",
    "confianca": "Confiança",
    "justificativa": "Justificativa",
    "gmv_total": "GMV total (R$)",
    "margem_total": "Margem total (R$)",
    "anomalias": "Anomalias",
    "analisado_em": "Analisado em",
}


# ----------------------------------------------------------------------
# Formatação consistente dos valores (mesma regra para CSV e Sheets)
# ----------------------------------------------------------------------

def _fmt(col, valor):
    """Padroniza valores. Moedas em formato BR; demais como texto puro."""
    if col in ("gmv_total", "margem_total"):
        try:
            return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return str(valor)
    return str(valor)


def _normaliza_data(valor):
    """Converte datas em vários formatos para o padrão usado localmente.
    Ex: '2026-06-07T23:10:00.000Z' -> '2026-06-07 23:10'
        '2026-06-07 20:10' -> '2026-06-07 20:10' (mantém)
        '2011-04-02' -> '2011-04-02' (mantém)
    """
    s = str(valor).strip()
    if not s:
        return s
    # ISO com T e Z (formato cru do Google)
    if "T" in s:
        s = s.replace("Z", "").split(".")[0]  # remove .000 e Z
        s = s.replace("T", " ")
        # corta segundos se terminar em :00
        if s.endswith(":00") and s.count(":") == 2:
            s = s[:-3]
    return s.strip()


def _normaliza_numero(valor):
    """Converte número em qualquer formato para o padrão BR '18.814.125,00'."""
    s = str(valor).strip()
    if not s:
        return s
    # Já está em formato BR (tem vírgula decimal)?
    if "," in s:
        return s
    # Número cru (ex: '18814125' ou '18814125.0')
    try:
        n = float(s.replace(".", "")) if s.replace(".", "").isdigit() else float(s)
        return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return s


def _normaliza_registro(reg):
    """Padroniza um registro vindo do Sheets para casar com o formato local."""
    out = dict(reg)
    if "analisado_em" in out:
        out["analisado_em"] = _normaliza_data(out["analisado_em"])
    for col in ("periodo_fim", "periodo_inicio"):
        if col in out:
            out[col] = _normaliza_data(out[col])
    for col in ("gmv_total", "margem_total"):
        if col in out:
            out[col] = _normaliza_numero(out[col])
    return out


def _so_data(valor):
    """Extrai só a parte da data (YYYY-MM-DD), ignorando hora/fuso.
    '2011-01-01 02:00' -> '2011-01-01'; '2011-04-02T03:00:00Z' -> '2011-04-02'
    """
    s = str(valor).strip().replace("T", " ")
    return s.split(" ")[0].split(".")[0] if s else s


def _chave(reg):
    """
    Chave de deduplicação. Como os nomes de teste são únicos (o app impede
    nomes repetidos), a identidade de um teste é o próprio nome, normalizado.
    Isso evita duas situações: fundir testes de nomes diferentes que por acaso
    têm o mesmo parceiro/período, e duplicar o mesmo teste quando o Google
    altera o formato das datas.
    """
    return (str(reg.get("nome_teste", "")).strip().lower(),)


# ----------------------------------------------------------------------
# CSV local
# ----------------------------------------------------------------------

def ensure_csv_exists():
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=DELIMITER).writerow(
                [CABECALHOS_LEGIVEIS[c] for c in COLUNAS])


def append_to_csv(resumo):
    ensure_csv_exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, delimiter=DELIMITER).writerow([_fmt(c, resumo.get(c, "")) for c in COLUNAS])


def read_csv_rows():
    ensure_csv_exists()
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        linhas = list(csv.reader(f, delimiter=DELIMITER))
    if len(linhas) <= 1:
        return []
    return [{COLUNAS[i]: (l[i] if i < len(l) else "") for i in range(len(COLUNAS))}
            for l in linhas[1:]]


def get_csv_bytes():
    ensure_csv_exists()
    return CSV_PATH.read_bytes()


def delete_registro(reg):
    """
    Apaga um teste a partir do registro completo (vindo da lista exibida).
    Remove do CSV local (se existir lá) e da planilha online (se configurada).
    Cobre inclusive testes que só existem online.
    """
    nome = reg.get("nome_teste", "")
    quando = reg.get("analisado_em", "")
    removidos_local = 0

    # Remove do CSV local, se houver linha correspondente (mesma chave de teste)
    registros = read_csv_rows()
    alvo = _chave(reg)
    restantes = [r for r in registros if _chave(r) != alvo]
    removidos_local = len(registros) - len(restantes)
    if removidos_local:
        with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=DELIMITER)
            w.writerow([CABECALHOS_LEGIVEIS[c] for c in COLUNAS])
            for r in restantes:
                w.writerow([_fmt(c, r.get(c, "")) for c in COLUNAS])

    # Remove da planilha online (casa pelo nome, que é único)
    online_ok = False
    if _sheets_configured():
        online_ok = _post({"action": "delete", "nome_teste": nome})

    return {"local": removidos_local, "online": online_ok}


def delete_row(nome_teste, analisado_em):
    registros = read_csv_rows()
    # Encontra o(s) registro(s) alvo pelo nome + data da análise
    alvos_reg = [
        r for r in registros
        if str(r.get("nome_teste", "")).strip() == str(nome_teste).strip()
        and _normaliza_data(r.get("analisado_em", "")) == _normaliza_data(analisado_em)
    ]
    alvos = {_chave(r) for r in alvos_reg}
    restantes = [r for r in registros if _chave(r) not in alvos]
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=DELIMITER)
        w.writerow([CABECALHOS_LEGIVEIS[c] for c in COLUNAS])
        for r in restantes:
            w.writerow([_fmt(c, r.get(c, "")) for c in COLUNAS])

    # Remove também da planilha online, enviando parceiro+período para casar
    # a linha mesmo quando o Google alterou o formato das datas.
    if _sheets_configured():
        ref = alvos_reg[0] if alvos_reg else {}
        _post({
            "action": "delete",
            "nome_teste": nome_teste,
            "analisado_em": analisado_em,
            "parceiro": ref.get("parceiro", ""),
            "periodo_inicio": ref.get("periodo_inicio", ""),
            "periodo_fim": ref.get("periodo_fim", ""),
        })
    return len(registros) - len(restantes)


# ----------------------------------------------------------------------
# Google Sheets via Apps Script
# ----------------------------------------------------------------------

def _sheets_configured():
    return bool(os.environ.get("GOOGLE_APPS_SCRIPT_URL"))


def _post(payload):
    url = os.environ.get("GOOGLE_APPS_SCRIPT_URL")
    if not url:
        return False
    token = os.environ.get("GOOGLE_APPS_SCRIPT_TOKEN", "")
    if token:
        payload["token"] = token
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return '"ok"' in resp.read().decode("utf-8").replace(" ", "")
    except Exception as e:
        print(f"Aviso: falha ao enviar ao Apps Script: {e}")
        return False


def append_to_sheets(resumo):
    if not _sheets_configured():
        return False
    return _post({
        "action": "append",
        "headers": [CABECALHOS_LEGIVEIS[c] for c in COLUNAS],
        "row": [_fmt(c, resumo.get(c, "")) for c in COLUNAS],
    })


def read_sheets_rows():
    """Lê a planilha do Google (GET) e devolve registros no formato interno."""
    url = os.environ.get("GOOGLE_APPS_SCRIPT_URL")
    if not url:
        return []
    try:
        token = os.environ.get("GOOGLE_APPS_SCRIPT_TOKEN", "")
        full = url + ("?token=" + urllib.parse.quote(token) if token else "")
        with urllib.request.urlopen(full, timeout=20) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        linhas = dados.get("rows", [])
        if not linhas:
            return []
        cabecalho = linhas[0]
        legivel_para_chave = {v: k for k, v in CABECALHOS_LEGIVEIS.items()}
        registros = []
        for linha in linhas[1:]:
            reg = {}
            for i, valor in enumerate(linha):
                if i < len(cabecalho):
                    chave = legivel_para_chave.get(cabecalho[i], cabecalho[i])
                    reg[chave] = valor
            registros.append(_normaliza_registro(reg))
        return registros
    except Exception as e:
        print(f"Aviso: falha ao ler do Apps Script: {e}")
        return []


def read_all_synced():
    """Lista unificada: CSV local + planilha online, sem duplicar."""
    vistos, unificado = set(), []
    for r in read_csv_rows() + read_sheets_rows():
        k = _chave(r)
        if k in vistos:
            continue
        vistos.add(k)
        unificado.append(r)
    return unificado


def read_all_com_status():
    """
    Lista unificada com um campo extra '_status' indicando onde o teste está:
      'ambos'    -> está no CSV local e na planilha online (mesmo nome e dados)
      'so_local' -> está só localmente (ainda não enviado)
      'so_online'-> está só na planilha (veio de outra fonte)
      'conflito' -> mesmo nome nos dois lados, mas DADOS DIFERENTES
    Quando o Google Sheets não está configurado, tudo é 'so_local'.
    """
    locais = read_csv_rows()

    if not _sheets_configured():
        return [dict(r, _status="so_local") for r in locais]

    online = read_sheets_rows()
    online_por_nome = {str(r.get("nome_teste", "")).strip().lower(): r for r in online}

    resultado, nomes_vistos = [], set()
    for r in locais:
        nome = str(r.get("nome_teste", "")).strip().lower()
        if nome in online_por_nome:
            # Mesmo nome existe online: é "ambos" só se os dados baterem;
            # se os dados diferem, é conflito — mostra os DOIS lados.
            if _mesmo_teste(r, online_por_nome[nome]):
                resultado.append(dict(r, _status="ambos"))
                nomes_vistos.add(nome)
            else:
                resultado.append(dict(r, _status="conflito_local"))
                resultado.append(dict(online_por_nome[nome], _status="conflito_online"))
                nomes_vistos.add(nome)
        else:
            resultado.append(dict(r, _status="so_local"))
            nomes_vistos.add(nome)
    # Online que não tem o mesmo nome localmente
    for r in online:
        nome = str(r.get("nome_teste", "")).strip().lower()
        if nome in nomes_vistos:
            continue
        nomes_vistos.add(nome)
        resultado.append(dict(r, _status="so_online"))
    return resultado


def _mesmo_teste(a, b):
    """
    Verifica se dois registros representam o MESMO teste (não só o mesmo nome).
    Compara os dados que identificam a análise: parceiro, período, decisão,
    GMV e margem. Datas são comparadas só pela parte do dia (ignora fuso);
    números são normalizados para o formato BR antes de comparar.
    """
    if _so_data(a.get("periodo_inicio", "")) != _so_data(b.get("periodo_inicio", "")):
        return False
    if _so_data(a.get("periodo_fim", "")) != _so_data(b.get("periodo_fim", "")):
        return False
    if str(a.get("parceiro", "")).strip().lower() != str(b.get("parceiro", "")).strip().lower():
        return False
    if str(a.get("variante_escalar", "")).strip().lower() != str(b.get("variante_escalar", "")).strip().lower():
        return False
    if _normaliza_numero(a.get("gmv_total", "")) != _normaliza_numero(b.get("gmv_total", "")):
        return False
    if _normaliza_numero(a.get("margem_total", "")) != _normaliza_numero(b.get("margem_total", "")):
        return False
    return True


def _nome_unico(base, nomes_usados):
    """Gera um nome livre acrescentando sufixo (2), (3)... se já existir."""
    nome = str(base).strip()
    if nome.lower() not in nomes_usados:
        return nome
    i = 2
    while f"{nome} ({i})".lower() in nomes_usados:
        i += 1
    return f"{nome} ({i})"


def push_locais_para_sheets():
    """
    Envia ao Sheets os testes locais que ainda não estão online.

    Trata conflito de nome: se um teste local tem o mesmo NOME de um já online,
    compara os dados (parceiro, período, decisão, GMV, margem):
      - dados iguais  -> é o mesmo teste, não envia (mantém um só);
      - dados diferentes -> renomeia o local com sufixo "(2)" antes de enviar,
        atualizando também o nome no CSV local para manter os dois lados iguais.
    Retorna (enviados, renomeados).
    """
    if not _sheets_configured():
        raise RuntimeError("Google Sheets não está configurado.")

    online = read_sheets_rows()
    online_por_nome = {str(r.get("nome_teste", "")).strip().lower(): r for r in online}
    nomes_usados = set(online_por_nome.keys())

    locais = read_csv_rows()
    enviados, renomeados = 0, 0
    houve_renomeacao = False

    for r in locais:
        nome_local = str(r.get("nome_teste", "")).strip()
        chave = nome_local.lower()

        if chave in online_por_nome:
            # Mesmo nome já existe online — comparar os dados
            if _mesmo_teste(r, online_por_nome[chave]):
                continue  # é o mesmo teste, não duplica
            # Dados diferentes: renomeia o local antes de enviar
            novo_nome = _nome_unico(nome_local, nomes_usados)
            r["nome_teste"] = novo_nome
            houve_renomeacao = True
            renomeados += 1

        if append_to_sheets(r):
            enviados += 1
            nomes_usados.add(str(r.get("nome_teste", "")).strip().lower())

    # Se algum teste local foi renomeado, regrava o CSV com os nomes novos
    if houve_renomeacao:
        with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=DELIMITER)
            w.writerow([CABECALHOS_LEGIVEIS[c] for c in COLUNAS])
            for r in locais:
                w.writerow([_fmt(c, r.get(c, "")) for c in COLUNAS])

    return enviados, renomeados


def importar_sheets_para_local():
    """Traz para o CSV local os testes que existem só na planilha online."""
    if not _sheets_configured():
        raise RuntimeError("Google Sheets não está configurado.")
    locais = read_csv_rows()
    chaves_local = {_chave(r) for r in locais}
    importados = 0
    for r in read_sheets_rows():
        if _chave(r) in chaves_local:
            continue
        # Acrescenta ao CSV local (sem reenviar ao Sheets)
        append_to_csv(r)
        chaves_local.add(_chave(r))
        importados += 1
    return importados


def sincronizar():
    """
    Sincroniza nos dois sentidos:
      - envia para a planilha os testes que estão só no local (tratando
        conflito de nome: dados iguais não duplicam; diferentes são renomeados);
      - importa para o local os testes que estão só na planilha.
    Retorna (enviados, importados, renomeados).
    """
    if not _sheets_configured():
        raise RuntimeError("Google Sheets não está configurado.")
    enviados, renomeados = push_locais_para_sheets()
    importados = importar_sheets_para_local()
    return enviados, importados, renomeados


def salvar(resumo):
    append_to_csv(resumo)
    return {"csv": True, "sheets": append_to_sheets(resumo)}


def nomes_existentes():
    """Conjunto de nomes de teste já usados (local + online), em minúsculas."""
    nomes = set()
    for r in read_csv_rows():
        nomes.add(str(r.get("nome_teste", "")).strip().lower())
    for r in read_sheets_rows():
        nomes.add(str(r.get("nome_teste", "")).strip().lower())
    nomes.discard("")
    return nomes
