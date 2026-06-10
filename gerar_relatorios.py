"""Gera os 3 relatórios reais (MD) e popula a planilha resultados.csv.

Observação: os datasets originais não vêm no repositório (são confidenciais da
Méliuz). Coloque os CSVs na pasta dados/ antes de rodar este script. Veja o
arquivo dados/LEIA-ME.txt para os nomes esperados.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "app"))

from analyzer import analyze
from report import generate
import sheets

testes = [
    ("dados/dataset_01_parceiroA.csv", "relatorios/relatorio_parceiroA.md",
     "Cashback Parceiro A — Jan-Abr 2011", "Teste de 3 níveis de cashback no Parceiro A"),
    ("dados/dataset_02_parceiroB.csv", "relatorios/relatorio_parceiroB.md",
     "Cashback Parceiro B — Mai-Jun 2011", "Teste de 3 níveis de cashback no Parceiro B"),
    ("dados/dataset_03_parceiroC.csv", "relatorios/relatorio_parceiroC.md",
     "Cashback Parceiro C — Jul-Ago 2011", "Teste de 2 variantes no Parceiro C (Grupo 2 com cashback máximo)"),
]

# Confere se os datasets estão presentes antes de começar
faltando = [csv_in for csv_in, *_ in testes if not (ROOT / csv_in).exists()]
if faltando:
    print("Os datasets originais não foram encontrados na pasta dados/.")
    print("Eles não vêm no repositório por serem confidenciais da Méliuz.")
    print("Coloque os arquivos abaixo na pasta dados/ e rode de novo:")
    for f in faltando:
        print(f"   - {f}")
    print("\n(Veja dados/LEIA-ME.txt para mais detalhes.)")
    sys.exit(1)

csv_path = ROOT / "resultados.csv"
if csv_path.exists():
    csv_path.unlink()

for csv_in, md_out, nome, desc in testes:
    r = analyze(csv_in, descricao=desc, nome_teste=nome)
    md, _, _ = generate(r, descricao=desc, use_claude_api=False)
    Path(md_out).write_text(md, encoding="utf-8")
    sheets.salvar(r["resumo"])
    print(f"  → {md_out} · {r['decisao']['resposta_direta']} ({r['decisao']['confianca']})")

print("Pronto.")
