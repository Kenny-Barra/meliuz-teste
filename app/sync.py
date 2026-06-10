"""
Sincroniza o CSV local com a planilha do Google, nos dois sentidos.

Uso:
    python sync.py

- Envia para a planilha os testes que estão só no local.
- Importa para o local os testes que estão só na planilha.
- Conflito de nome: se o mesmo nome existe nos dois lados, compara os dados;
  iguais -> mantém um só; diferentes -> renomeia o local com sufixo "(2)".

Precisa da variável GOOGLE_APPS_SCRIPT_URL configurada (no .env de app/ ou no
ambiente). Sem ela, não há planilha para sincronizar.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent


def carregar_env():
    for env_path in (Path(__file__).resolve().parent / ".env", ROOT / ".env"):
        if env_path.exists():
            for linha in env_path.read_text(encoding="utf-8").splitlines():
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, valor = linha.split("=", 1)
                os.environ.setdefault(chave.strip(),
                                      valor.strip().strip('"').strip("'"))


carregar_env()
import sheets


def main():
    if not sheets._sheets_configured():
        print("⚠️  GOOGLE_APPS_SCRIPT_URL não está configurada.")
        print("    Crie um arquivo .env em app/ com a URL do Apps Script e tente de novo.")
        sys.exit(1)

    sheets.ensure_csv_exists()
    print("🔁 Sincronizando local ↔ planilha...")
    enviados, importados, renomeados = sheets.sincronizar()

    if not (enviados or importados or renomeados):
        print("✅ Tudo já estava sincronizado — nada a fazer.")
        return

    if enviados:
        print(f"   ⬆️  {enviados} teste(s) enviado(s) para a planilha.")
    if importados:
        print(f"   ⬇️  {importados} teste(s) importado(s) para o local.")
    if renomeados:
        print(f"   ✏️  {renomeados} teste(s) com nome repetido (dados diferentes) renomeado(s).")
    print("✅ Sincronização concluída. Os dois lados estão completos.")


if __name__ == "__main__":
    main()
