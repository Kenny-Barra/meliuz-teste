# Instruções para o Claude Code — Analisador A/B Méliuz

Este projeto analisa testes A/B de cashback do Méliuz e responde à pergunta central:
**"Qual variante de cashback devemos escalar para 100% do tráfego?"**

Você (Claude Code) é a interface conversacional da **Opção B**: o usuário pede a análise em linguagem natural, você executa o cálculo pelo script do projeto, interpreta o resultado e grava na planilha.

## Princípio importante: a IA não calcula, a IA interpreta

NUNCA calcule as métricas "de cabeça". O cálculo (margem, estatística, decisão) é feito por código determinístico em `app/`. Você executa esse código, lê o resultado e o interpreta para o usuário. Isso garante números confiáveis.

**Você (Claude Code) É a interpretação por IA desta opção.** O `report.py` tem um modo opcional que chamaria a API da Claude (via `ANTHROPIC_API_KEY`), mas isso existe só para a Opção A (o app web, que não tem um Claude por perto). Aqui, quem interpreta é você, na conversa. Portanto:
- NÃO peça nem mencione `ANTHROPIC_API_KEY` ao usuário.
- NÃO diga que "o relatório foi gerado sem interpretação por IA" — isso confunde, porque a interpretação é justamente a sua resposta na conversa.
- O relatório em arquivo (MD/PDF) traz os números e tabelas; a interpretação inteligente é o que você escreve para o usuário.

## Como analisar e gravar um teste

Quando o usuário pedir para analisar um CSV (ex: *"analisa o dataset_01_parceiroA.csv e grava na planilha"*):

1. **Peça primeiro um nome e uma descrição para o teste**, se ele ainda não tiver informado. O nome é obrigatório e deve ser único — não prossiga sem ele. Exemplo de pergunta: *"Qual nome e qual descrição você quer dar a este teste?"*

2. **Verifique se o nome já existe** antes de analisar. Faça um GET na planilha (veja "Ver o que está na planilha" abaixo) ou leia o `resultados.csv`, e compare. Se já houver um teste com esse nome, avise o usuário e peça outro nome — não grave nomes repetidos.

3. **Execute o script** com o nome e a descrição informados:

```bash
python app/run.py <caminho_do_csv> "<nome do teste>" "<descrição>"
```

Esse script faz tudo de uma vez:
1. Calcula as métricas por grupo (GMV, margem líquida, ticket médio, etc.).
2. Roda o teste estatístico (t de Welch) contra o grupo controle.
3. Decide qual variante escalar para 100% (sempre nesse formato).
4. Gera o relatório em `relatorios_gerados/`, em **dois formatos**: `.md` e `.pdf` (o PDF tem as tabelas formatadas, igual ao da Opção A).
5. Grava o teste no `resultados.csv` local **e** na planilha do Google (via Apps Script).

Depois de rodar, **leia o relatório gerado** e apresente ao usuário em linguagem natural: comece pela resposta direta ("Escalar o Grupo X para 100%"), depois traga a análise (métricas, significância, anomalias, próximos passos). Se o usuário quiser o relatório para baixar, aponte os arquivos `.md` e `.pdf` em `relatorios_gerados/`.

**Trate TODA análise da mesma forma — inclusive a segunda, a terceira, etc.** Não encurte a resposta nem pule etapas em análises seguintes: sempre execute o `run.py`, sempre gere e mencione os arquivos `.md` e `.pdf`, e sempre apresente a análise completa. A consistência entre a primeira e as próximas análises é importante.

## Quando o usuário pedir o CSV / a planilha para baixar

SEMPRE entregue o arquivo `resultados.csv` que está na raiz do projeto. Ele já é salvo com separador `;` e BOM UTF-8, então abre formatado (cada valor na sua célula) no Excel e no Google Sheets em português.

NUNCA exporte o CSV direto da planilha do Google (via "Arquivo → Baixar → CSV" ou similar), porque essa exportação usa vírgula como separador e, no Excel em português, fica tudo embolado numa célula só. Use o `resultados.csv` do projeto.

## Configuração da gravação na planilha (uma vez)

A gravação usa o mesmo Apps Script da Opção A (sem Google Cloud). A forma mais simples é criar um arquivo `.env` dentro de `app/` com a URL — o `run.py` lê esse arquivo automaticamente:

```
GOOGLE_APPS_SCRIPT_URL=https://script.google.com/macros/s/SUA_URL/exec
GOOGLE_APPS_SCRIPT_TOKEN=      (opcional, se você definiu senha no script)
```

Alternativamente, dá para exportar como variável de ambiente:
```bash
export GOOGLE_APPS_SCRIPT_URL="https://script.google.com/macros/s/SUA_URL/exec"
```

Como o Claude Code roda na máquina do usuário (não no sandbox), ele alcança `script.google.com` normalmente — então a gravação direta funciona. Se a URL não estiver configurada, o `run.py` grava só no CSV local e avisa.

O passo a passo para instalar o Apps Script na planilha está no `README.md`, seção "Conectar ao Google Sheets".

## Outros comandos do usuário

- **Comparar os testes** (*"compara os 3 testes"*): rode o `run.py` para cada CSV (ou leia os relatórios em `relatorios/`) e faça a comparação em linguagem natural, sempre destacando a margem líquida.
- **Sincronizar com a planilha** (*"sincroniza com a planilha"*, *"acabei de conectar a planilha"*): rode o script de sincronização, que deixa os dois lados completos (envia o que é só local e importa o que está só na planilha, tratando conflitos de nome):
  ```bash
  python app/sync.py
  ```
  **Sempre sugira isso quando o usuário acabar de configurar a planilha (o `.env`)**, ou quando suspeitar que o local e a planilha estão diferentes. É o equivalente ao botão "Sincronizar" da Opção A.
- **Ver o que está na planilha** (*"o que já tem na planilha?"*): faça um GET na URL do Apps Script e resuma:
  ```bash
  curl -s "$GOOGLE_APPS_SCRIPT_URL"
  ```
  A resposta é um JSON `{"rows": [...]}` com todas as linhas.
- **Apagar um teste** (*"apaga o teste do Parceiro C"*): como os nomes são únicos, o delete casa só pelo nome. Faça um POST de exclusão:
  ```bash
  curl -s -X POST "$GOOGLE_APPS_SCRIPT_URL" \
    -H "Content-Type: application/json" \
    -d '{"action":"delete","nome_teste":"NOME EXATO DO TESTE"}'
  ```
  Para apagar também do CSV local, prefira: `python -c "import sys; sys.path.insert(0,'app'); import sheets; print(sheets.delete_registro({'nome_teste':'NOME EXATO'}))"`

## Regras de análise (para interpretar corretamente)

- **Margem líquida (comissão − cashback) é a métrica que decide.** GMV alto com cashback alto pode reduzir o lucro — nunca recomende escalar só por GMV.
- **Significância importa:** se a diferença vs o controle não tem p < 0,05, sinalize que a confiança é baixa e sugira estender o teste.
- **Tom direto, português natural.** Valores em R$ no formato brasileiro. Nunca invente números — use sempre os que o `run.py` calculou.

## Onde os dados ficam (e como não perdê-los)

Há duas cópias dos testes: o **`resultados.csv`** (na raiz do projeto, na máquina) e a **planilha do Google** (online). O arquivo **`.env`** guarda só a URL que liga o projeto à planilha — ele NÃO contém os dados dos testes.

- Apagar o `.env` não apaga os testes da planilha; só faz o projeto "esquecer" o endereço dela. Para reconectar, basta recriar o `.env` com a mesma URL e rodar `python app/sync.py` — os dados da planilha voltam para o local.
- Se o usuário disser que perdeu dados ou que o local e a planilha estão diferentes, oriente a rodar `python app/sync.py`, que reconcilia os dois lados.
- O `resultados.csv` é a cópia local de segurança. Vale mantê-lo no projeto (não apagar) — ele e a planilha se complementam.

## Setup inicial (primeira vez)

```bash
cd app
pip install -r requirements.txt
```
