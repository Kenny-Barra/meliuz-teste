"""
Script local (alternativa por terminal, sem abrir o app web nem o Claude).

Uso:
    python run.py <caminho_csv> ["Nome do teste"] ["Descrição"]

Roda a análise, gera o relatório (MD) e grava na planilha (CSV local +
Google Sheets, se GOOGLE_APPS_SCRIPT_URL estiver configurado). Cria as
pastas de organização automaticamente.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent


def carregar_env():
    """Lê um arquivo .env (em app/ ou na raiz) e popula variáveis de ambiente.
    Simples, sem dependências: linhas no formato CHAVE=valor."""
    for env_path in (Path(__file__).resolve().parent / ".env", ROOT / ".env"):
        if env_path.exists():
            for linha in env_path.read_text(encoding="utf-8").splitlines():
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, valor = linha.split("=", 1)
                chave, valor = chave.strip(), valor.strip().strip('"').strip("'")
                # Não sobrescreve variáveis já definidas no ambiente
                os.environ.setdefault(chave, valor)


carregar_env()

from analyzer import analyze
from report import generate, markdown_to_pdf_bytes
import sheets


def main():
    if len(sys.argv) < 2:
        print('Uso: python run.py <caminho_csv> ["Nome"] ["Descrição"]')
        sys.exit(1)

    csv_path = sys.argv[1]
    nome = sys.argv[2] if len(sys.argv) > 2 else None
    desc = sys.argv[3] if len(sys.argv) > 3 else None

    if not nome or not nome.strip():
        print("❌ É obrigatório informar um nome para o teste.")
        print('   Uso: python run.py <caminho_csv> "Nome do teste" "Descrição"')
        sys.exit(1)

    # Bloqueia nome repetido (compara com testes locais e online)
    if nome.strip().lower() in sheets.nomes_existentes():
        print(f"❌ Já existe um teste com o nome '{nome.strip()}'. Escolha outro nome.")
        sys.exit(1)

    (ROOT / "relatorios_gerados").mkdir(exist_ok=True)
    sheets.ensure_csv_exists()

    print(f"📂 Analisando {csv_path}...")
    resultado = analyze(csv_path, descricao=desc, nome_teste=nome)
    relatorio, _, motivo = generate(resultado, descricao=desc)

    slug = resultado["resumo"]["parceiro"].replace(" ", "_")
    out_md = ROOT / "relatorios_gerados" / f"relatorio_{slug}.md"
    out_md.write_text(relatorio, encoding="utf-8")

    # Gera o relatório em PDF (mesmo do app da Opção A)
    out_pdf = ROOT / "relatorios_gerados" / f"relatorio_{slug}.pdf"
    try:
        out_pdf.write_bytes(markdown_to_pdf_bytes(relatorio))
        pdf_ok = True
    except Exception as e:
        pdf_ok = False
        print(f"⚠️  Não foi possível gerar o PDF: {e}")

    info = sheets.salvar(resultado["resumo"])

    d = resultado["decisao"]
    print(f"📝 Relatório (MD):  {out_md}")
    if pdf_ok:
        print(f"📕 Relatório (PDF): {out_pdf}")
    print(f"💾 CSV: ✅ | Sheets: {'✅' if info['sheets'] else '⏭️ não configurado'}")
    print("\n" + "=" * 54)
    print(f"RESPOSTA:  {d['resposta_direta']}")
    print(f"CONFIANÇA: {d['confianca']}")
    print("=" * 54)
    print(d["ressalva"])
    if resultado["anomalias"]:
        print("\n⚠️  Anomalias:")
        for a in resultado["anomalias"]:
            print(f"   - {a}")


if __name__ == "__main__":
    main()
