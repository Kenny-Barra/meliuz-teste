# Analisador de Testes A/B (Méliuz)

Sistema que lê os dados de um teste A/B de cashback e responde, de forma automática e direta, à pergunta central do time de Growth:

> **Qual variante de cashback devemos escalar para 100% do tráfego?**

Você fornece um CSV, o sistema calcula as métricas, decide qual variante escalar, escreve um relatório pronto para um gestor (em Markdown ou PDF) e registra o teste numa planilha de acompanhamento. Funciona com qualquer teste novo, sem alterar o código.

> **Nota sobre os dados:** os datasets originais fornecidos pela Méliuz não estão neste repositório, por serem material confidencial do teste. Para rodar os exemplos, basta adicioná-los na pasta `dados/` (veja `dados/LEIA-ME.txt`). O app e o Claude Code também aceitam qualquer outro CSV no mesmo formato.

---

## Vídeo explicativo

[![Assista ao vídeo](https://img.youtube.com/vi/gRsKhiAyh2I/maxresdefault.jpg)](https://youtu.be/gRsKhiAyh2I)

---

## Índice

1. [Visão geral](#1-visão-geral)
2. [As duas formas de usar](#2-as-duas-formas-de-usar)
3. [Começando rápido](#3-começando-rápido)
4. [Opção A: App web](#4-opção-a-app-web)
   - [Rodar localmente](#41-rodar-localmente)
   - [Publicar no Streamlit Cloud](#42-publicar-no-streamlit-cloud)
   - [As três abas](#43-as-três-abas)
5. [Opção B: Claude Code](#5-opção-b-claude-code)
6. [Conectar ao Google Sheets (Apps Script)](#6-conectar-ao-google-sheets-apps-script)
   - [Passo a passo](#61-passo-a-passo)
   - [Problemas comuns](#62-problemas-comuns)
7. [Ativar a inteligência artificial](#7-ativar-a-inteligência-artificial)
8. [A planilha de acompanhamento](#8-a-planilha-de-acompanhamento)
9. [Como o sistema decide](#9-como-o-sistema-decide)
10. [Resultados dos 3 testes entregues](#10-resultados-dos-3-testes-entregues)
11. [Organização dos arquivos](#11-organização-dos-arquivos)

---

## 1. Visão geral

Para cada teste, o sistema entrega:

- **Resposta direta:** qual variante escalar para 100% do tráfego.
- **Métricas por grupo:** GMV, comissão, cashback, margem líquida, margem % do GMV, ticket médio e taxa de cashback.
- **Teste estatístico:** compara cada variante com o controle (teste t de Welch) e mostra o p-value.
- **Detecção de anomalias:** valores negativos, datas duplicadas, grupos desbalanceados, cashback maior que comissão.
- **Relatório para gestor:** em Markdown e PDF (com tabelas formatadas).
- **Registro na planilha:** uma linha por teste, em CSV local e, opcionalmente, no Google Sheets.

---

## 2. As duas formas de usar

| | **Opção A: App web** | **Opção B: Claude Code** |
|---|---|---|
| Indicação | Recomendada (porta de entrada) | Alternativa (experiência com IA) |
| Para quem | Qualquer pessoa do time, sem precisar saber de IA | Quem já usa Claude Code e quer a experiência conversacional |
| Como usa | Abre um site e arrasta o CSV | Conversa no Claude Code |
| Instala algo? | Não (só abre o link) | Sim (Claude Code, uma vez) |
| Custo | Sem custo de IA (cálculo é código) | Consome tokens do seu plano |
| Relatório | Tela + download MD/PDF | Conversa + arquivos MD/PDF |
| Gráficos e histórico | Sim, visuais | Resumo na conversa + relatórios em arquivo |
| Inteligência artificial | Opcional (só a interpretação) | Conduz a conversa e interpreta |

As duas registram o teste na **mesma planilha**, usando o **mesmo Apps Script** (seção 6). Configure uma vez, use nas duas.

### Por que duas opções?

Criei as duas de propósito, porque elas resolvem necessidades diferentes:

**A Opção A (app web) é a mais econômica e a mais intuitiva.** O cálculo de um teste A/B (somar GMV, calcular margem, rodar o teste estatístico) é matemática determinística: não precisa de inteligência artificial para isso, e usar IA só encareceria sem nenhum ganho. O app web faz todo o cálculo com código puro, de graça, e a IA fica opcional, só para escrever a interpretação do relatório. Além disso, o app web é uma página simples: a pessoa abre um link, arrasta um arquivo e clica em um botão. É ideal para quem não tem familiaridade com IA, terminal ou linha de comando, que é a maioria de um time de negócio.

**A Opção B (Claude Code) é a experiência conversacional, "AI-Native".** Aqui a pessoa pede a análise em linguagem natural ("analisa esse arquivo e grava na planilha") e recebe a resposta interpretada na conversa. É mais fluida e demonstra o uso de IA como interface, mas tende a custar mais (cada conversa consome tokens do seu plano) e pressupõe ter o Claude Code instalado. Por isso ela é a alternativa, não a porta de entrada: mesmo na Opção B, quem calcula é o código do projeto, não a IA, justamente para manter a análise confiável e barata.

Em resumo: a mesma engrenagem de cálculo serve as duas. O app web entrega isso de um jeito acessível e sem custo de IA; o Claude Code entrega de um jeito conversacional para quem quer essa experiência.

---

## 3. Começando rápido

**Só ver funcionando:** abra o link do app publicado e arraste um dos CSVs do teste (os datasets originais não estão no repositório por serem confidenciais; veja `dados/LEIA-ME.txt`).

**Rodar no seu computador:**
```bash
cd app
pip install -r requirements.txt
streamlit run app.py
```

**Links do projeto** :
- App web no ar: [Streamlit](https://meliuz-teste-kennedy.streamlit.app/)
- Planilha pública: [Google Sheets](https://docs.google.com/spreadsheets/d/1tB9-ddrjvL4QuFyhnOUVoY5Lm0UbsZviqbq4tH4LzHc/edit?usp=sharing)

---

## 4. Opção A: App web

App em Streamlit. Calcula tudo localmente e, se você ligar a IA e/ou o Google Sheets, ganha interpretação por IA e gravação online.

### 4.1. Rodar localmente
```bash
cd app
pip install -r requirements.txt
streamlit run app.py
```
O site abre em `http://localhost:8501`.

### 4.2. Publicar no Streamlit Cloud
1. Suba este projeto para um repositório **público** no GitHub.
2. Acesse https://share.streamlit.io e entre com o GitHub.
3. **New app** → selecione o repositório → em **Main file path** escreva `app/app.py` → **Deploy**.
4. (Opcional) Em **Settings → Secrets**, cole as variáveis de IA e/ou Google Sheets no **formato TOML** (`CHAVE = "valor"`, com aspas). Veja os exemplos nas seções 6 e 7.

### 4.3. As três abas
- **Nova análise:** envie o CSV, preencha **nome** e **descrição**, clique em Analisar. Aparece a resposta direta (qual escalar para 100%), métricas, gráficos e o relatório, com download em **MD** e **PDF**.
- **Histórico:** lista completa, com **busca por nome**, **filtro por parceiro** e **filtro por data**. Clique em um teste para reabrir gráficos, métricas e relatório, ou para apagar.
- **Planilha geral:** mostra a planilha de acompanhamento, com uma coluna de status (🟢 local + planilha · 🟡 só local · 🔵 só na planilha · 🔴 conflito de nome) e filtros por nome e parceiro. Tem botão **Atualizar dados** e, quando o Google Sheets está conectado, o botão **Sincronizar com o Google Sheets**, que deixa os dois lados completos (envia o que é só local e importa o que está só na planilha). Para apagar, marque os testes na coluna **Apagar** da tabela e confirme; a remoção acontece no local e na planilha online ao mesmo tempo. Também há **download da planilha em CSV** e link para o Google Sheets.

---

## 5. Opção B: Claude Code

Aqui você conversa com o **Claude Code** e ele analisa os testes e grava na planilha em linguagem natural. O Claude Code roda na **sua máquina** (sua rede), então alcança o Apps Script normalmente e a gravação funciona, ao contrário do Claude na web, que é restrito.

Você pode usar o Claude Code de duas formas: pela **aba "Code" do app do Claude** (desktop) ou pelo Claude Code instalado no terminal. As duas rodam localmente. Abaixo está como instalar cada uma e, em seguida, o passo a passo de uso.

### Instalação, opção 1: app do Claude (mais fácil)

O app de desktop do Claude já traz a aba "Code", sem precisar mexer no terminal.

1. Acesse **https://claude.com/download** (site oficial; evite baixar de outros sites) e baixe o app para o seu sistema (Windows ou macOS).
2. Instale e faça login com sua conta (o Claude Code precisa de um plano Pro ou Max; o plano gratuito não inclui).
3. Aberto o app, no topo há três abas: **Chat**, **Cowork** e **Code**. Clique em **Code**.
4. É essa aba que você vai usar para a Opção B (o passo a passo de uso está logo abaixo).

### Instalação, opção 2: Claude Code no terminal

Se preferir o terminal puro, instale o Claude Code como ferramenta de linha de comando. O jeito mais simples (não exige Node.js):

- **macOS / Linux:**
  ```bash
  curl -fsSL https://claude.ai/install.sh | bash
  ```
- **Windows:** abra o **PowerShell** (não o "Prompt de Comando / CMD"; o comando abaixo é do PowerShell; se você vir o erro `'irm' não é reconhecido`, é porque está no CMD). No menu Iniciar, procure por "PowerShell", abra, e rode:
  ```powershell
  irm https://claude.ai/install.ps1 | iex
  ```

Depois feche e reabra o terminal, e confirme com `claude --version`. Na primeira vez, rode `claude` dentro da pasta do projeto e faça login.

> Alternativa por npm (caso já use Node.js 18+): `npm install -g @anthropic-ai/claude-code`. Não use `sudo`; se der erro de permissão, prefira o instalador acima.

### Instalar o Git e o Git Bash (Windows)

O Claude Code precisa do **Git** para funcionar e, no Windows, ele usa o **Git Bash** (um terminal que vem junto com o Git) para rodar os comandos. Para verificar se já tem, rode `git --version`. Se não tiver:

- **Windows:** baixe o **Git for Windows** em https://git-scm.com/download/win e instale (pode aceitar as opções padrão). Ele já inclui o Git Bash.
- **macOS:** rode `xcode-select --install` no terminal, ou baixe em https://git-scm.com/download/mac.
- **Linux (Ubuntu/Debian):** `sudo apt install git`.

**Passo extra no Windows (variável de ambiente):** se o Claude Code não encontrar o Git Bash automaticamente, ele pode pedir que você informe o caminho do `git-bash.exe`. Nesse caso, adicione esse caminho nas Variáveis de Ambiente do Windows:

1. No menu Iniciar, procure por **"Editar as variáveis de ambiente do sistema"** e abra.
2. Clique em **Variáveis de Ambiente**.
3. Crie uma nova variável (ou ajuste a que o Claude Code indicar) apontando para o `git-bash.exe`, que normalmente fica em `C:\Program Files\Git\git-bash.exe`.
4. Salve, feche e reabra o Claude Code para ele reconhecer.

Esse passo só é necessário no Windows e só se o Claude Code reclamar que não achou o Git Bash.

### Configurar o `.env` (a URL do Apps Script)

O Claude Code precisa saber a URL do seu Apps Script para gravar na planilha. Para isso, use o arquivo `.env`:

1. Na pasta `app/`, faça uma **cópia** do arquivo `.env.example` e renomeie a cópia para `.env`.
2. Abra o `.env` num editor de texto e preencha as linhas que interessam com os seus valores (a URL você gera na seção 6):
   ```
   GOOGLE_APPS_SCRIPT_URL=https://script.google.com/macros/s/SUA_URL/exec
   GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/SUA_PLANILHA/edit
   ```
3. Salve. O `run.py` e o `sync.py` leem esse arquivo automaticamente em toda execução, sem precisar configurar mais nada.

As linhas que você não for usar (por exemplo, as da IA) podem ficar como estão ou ser apagadas; o que não estiver preenchido é simplesmente ignorado.

### Passo a passo (aba "Code" do app do Claude)

1. **Tenha a pasta do projeto no seu computador.** Baixe e descompacte este projeto numa pasta (ex: `meliuz-ab-analyzer`).

2. **Configure o `.env`.** Como descrito acima, copie o `.env.example` para `.env` (na pasta `app/`) e preencha a URL do Apps Script.

3. **Abra a aba "Code"** no app do Claude e clique em **"Selecionar pasta..."**, apontando para a pasta do projeto. O Claude Code lê o arquivo `CLAUDE.md` automaticamente (são as instruções dele).

4. **Instale as dependências** (uma vez). Peça na conversa ou rode:
   ```bash
   cd app && pip install -r requirements.txt
   ```

5. **Use em linguagem natural:**
   - *"Analisa o dataset_01_parceiroA.csv e grava na planilha."*
   - *"Compara os três testes."*
   - *"Sincroniza com a planilha."* (deixa local e planilha completos nos dois sentidos)
   - *"O que já tem na planilha?"*
   - *"Apaga o teste do Parceiro C."*

   O Claude Code executa a análise (pelo `run.py`), grava na planilha e te explica o resultado na conversa, sempre começando por qual variante escalar para 100%.

> **Ao conectar a planilha pela primeira vez** (ou se local e planilha estiverem diferentes), peça *"sincroniza com a planilha"*. Isso roda o `app/sync.py`, que envia o que é só local e importa o que está só na planilha, assim você não perde nada. O `.env` guarda só o endereço da planilha; os dados ficam no `resultados.csv` e na própria planilha.

> **Dica de verificação:** na primeira vez, peça *"roda: curl -s -o /dev/null -w '%{http_code}' https://script.google.com"*. Se retornar um número (ex: 200 ou 302), sua rede alcança o Apps Script e a gravação vai funcionar.

### Alternativa: terminal puro

Se preferir rodar sem conversar, na pasta `app/` (com o `.env` configurado):
```bash
pip install -r requirements.txt
python run.py ../dados/dataset_01_parceiroA.csv "Nome do teste" "Descrição"
```

---

## 6. Conectar ao Google Sheets (Apps Script)

Este passo é **opcional**. Sem ele, o sistema salva tudo no `resultados.csv` (que você baixa pelo app, já formatado). Com ele, os testes vão para uma planilha online, e a Opção A passa a sincronizar nos dois sentidos.

O método usa o **Google Apps Script**: um script que mora dentro da própria planilha. **Não precisa de Google Cloud, conta de serviço ou arquivo JSON.**

### 6.1. Passo a passo
1. Crie (ou abra) sua planilha no Google Sheets. Crie-a direto em sheets.google.com (assim ela já é nativa, não um Excel importado).
2. No menu, vá em **Extensões → Apps Script**.
3. Apague tudo o que aparecer e cole **todo** o conteúdo do arquivo `apps_script.txt` (na raiz deste projeto).
4. Salve (ícone de disquete).
5. Clique em **Implantar → Nova implantação**.
6. Na engrenagem ao lado de "Selecionar tipo", escolha **App da Web**.
7. Configure: **Executar como:** Eu · **Quem pode acessar:** Qualquer pessoa.
8. Clique em **Implantar** e autorize: escolha sua conta → **Avançado** → **Acessar (não seguro)** → **Permitir**. (É seguro: é seu próprio script, na sua planilha.)
9. Copie a **URL que termina em `/exec`**.
10. Use essa URL:
    - **Opção A (rodando local):** copie o `.env.example` para `.env` dentro de `app/` e preencha `GOOGLE_APPS_SCRIPT_URL=...` e `GOOGLE_SHEET_URL=...`.
    - **Opção A (no Streamlit Cloud):** o Streamlit não usa `.env`; ele usa **secrets no formato TOML**. Vá em **Settings → Secrets** e cole as mesmas chaves nesse formato, com aspas:
      ```toml
      GOOGLE_APPS_SCRIPT_URL = "https://script.google.com/macros/s/SUA_URL/exec"
      GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/SUA_PLANILHA/edit"
      ```
    - **Opção B:** use o mesmo `.env` da Opção A local (veja a seção 5). O `run.py` e o `sync.py` leem esse arquivo automaticamente.

### 6.2. Problemas comuns
- **Não grava nada:** confirme que a URL termina em `/exec` (não `/dev`) e que em "Quem pode acessar" você escolheu **Qualquer pessoa**.
- **Editei o script e parou:** toda alteração exige uma **nova implantação** (ou Gerenciar implantações → nova versão). A URL antiga roda a versão antiga.
- **Travou em "não seguro":** é normal para scripts pessoais. Clique em **Avançado → Acessar (não seguro)**. Você está autorizando seu próprio script.
- **Datas/números aparecem diferentes entre linhas:** o `apps_script.txt` deste projeto já força as células como texto justamente para evitar isso. Se você usou uma versão antiga do script, reinstale com a atual e crie nova implantação.
- **Apagar não remove da planilha online:** atualize o `apps_script.txt` para a versão atual (como os nomes de teste são únicos, o delete casa a linha apenas pelo nome) e crie uma nova implantação.
- **A planilha abre como Excel (.xlsx):** ela foi criada por upload de Excel. Crie uma nova direto pelo Google Sheets.
- **Proteger com senha:** no topo do `apps_script.txt`, troque `var TOKEN = "";` por `var TOKEN = "suaSenha";`, reimplante e use o mesmo valor em `GOOGLE_APPS_SCRIPT_TOKEN` (no `.env`, ou nos Secrets do Streamlit no formato TOML).

---

## 7. Ativar a inteligência artificial

Esta é uma vaga AI-Native, então vale explicar **onde a IA entra e onde não entra**.

- **O cálculo é feito por código, não por IA.** Somar GMV, calcular margem, rodar o teste estatístico: isso é matemática determinística; código (pandas + scipy) é mais rápido, barato e confiável que pedir a um modelo.
- **A interpretação é onde a IA agrega.** Transformar os números numa leitura de negócio, apontar riscos e redigir em linguagem natural.

> Em resumo: **a IA não calcula, a IA interpreta.**

Na **Opção B**, o Claude Code conduz a conversa e interpreta, mas o cálculo é feito pelo código do projeto (o `run.py`). Na **Opção A**, o código calcula e a Claude API escreve a "Leitura executiva" do relatório, se a chave estiver configurada; se não, o relatório sai completo só com os números (com aviso).

**Como ativar na Opção A:**
1. Crie uma conta em https://console.anthropic.com
2. Em **API Keys**, gere uma chave (`sk-ant-...`) e adicione créditos em Billing.
3. Configure a chave:
   - **Rodando local:** no `.env` em `app/`, preencha `ANTHROPIC_API_KEY=sk-ant-...`.
   - **No Streamlit Cloud:** em **Settings → Secrets**, no formato TOML: `ANTHROPIC_API_KEY = "sk-ant-..."`.

**Custo:** o sistema envia só o resumo já calculado (não o CSV inteiro), então cada análise custa frações de centavo. É opcional, mas recomendado para esta vaga.

---

## 8. A planilha de acompanhamento

Cada teste vira **uma linha**, com colunas em português prontas para um gestor:

Nome do teste · Descrição · Parceiro · Início · Fim · Nº grupos · Variante a escalar · Decisão (100% do tráfego) · Confiança · Justificativa · GMV total (R$) · Margem total (R$) · Anomalias · Analisado em

O `resultados.csv` é salvo com separador `;` e UTF-8, então **abre formatado, cada valor na sua célula**, no Excel e no Google Sheets em português. Os valores são padronizados (datas em ISO, moedas em formato BR) e o Apps Script grava tudo como texto, garantindo que as colunas fiquem consistentes entre si e que a sincronização não duplique linhas.

---

## 9. Como o sistema decide

1. Calcula a **margem líquida** de cada grupo (comissão − cashback). É o que o Méliuz lucra.
2. Compara cada variante com o controle (Grupo 1) por um **teste t de Welch** sobre a margem diária.
3. Responde **sempre** no formato "escalar o Grupo X para 100%":
   - Maior margem **com** significância (p < 0,05) → confiança **alta**.
   - Maior margem **sem** significância → confiança **baixa**, sugere estender o teste.
   - Se o controle é o melhor → escalar o controle significa manter a configuração atual.

> Por que margem e não vendas (GMV)? Um grupo pode vender mais dando muito cashback e, ainda assim, o Méliuz lucrar menos. O que decide é a margem.

---

## 10. Resultados dos 3 testes entregues

| Parceiro | Período | Grupos | Decisão | Confiança | Margem total |
|---|---|---|---|---|---|
| A | Jan-Abr 2011 | 3 | Escalar Grupo 1 (manter atual) | alta | R$ 1.026.517 |
| B | Mai-Jun 2011 | 3 | Escalar Grupo 1 (manter atual) | alta | R$ 482.320 |
| C | Jul-Ago 2011 | 2 | Escalar Grupo 1 (manter atual) | alta | R$ 34.769 |

Nos três, o **Grupo 1 (cashback menor) tem a maior margem líquida**, com diferença estatisticamente significativa. Cashback mais alto trouxe mais vendas em alguns casos, mas não o bastante para compensar o valor distribuído; no Parceiro C, o Grupo 2 (cashback igual à comissão) zerou a margem. Recomendação: **escalar o Grupo 1 (manter a configuração atual) nos três parceiros** e investigar por que aumentar o cashback não converteu em vendas proporcionais. Relatórios completos em `relatorios/`.

---

## 11. Organização dos arquivos

```
meliuz-ab-analyzer/
├── README.md                  ← toda a explicação (este arquivo)
├── resultados.csv             ← planilha de acompanhamento (preenchida)
├── gerar_relatorios.py        ← regera os 3 relatórios e a planilha
├── apps_script.txt            ← script para colar no Google Sheets
├── CLAUDE.md                  ← instruções que o Claude Code lê (Opção B)
│
├── dados/                     ← onde vão os CSVs (não incluídos: confidenciais)
│   └── LEIA-ME.txt            ← como adicionar os datasets do teste
│
├── relatorios/                ← os 3 relatórios já gerados (MD)
│   ├── relatorio_parceiroA.md
│   ├── relatorio_parceiroB.md
│   └── relatorio_parceiroC.md
│
└── app/                       ← código (app web da Opção A + run.py da Opção B)
    ├── app.py                 ← app web (Streamlit)
    ├── analyzer.py            ← cálculos e decisão
    ├── report.py              ← relatório em MD e PDF
    ├── sheets.py              ← CSV + Google Sheets (sincronização)
    ├── run.py                 ← analisa e grava (Opção B / terminal)
    ├── sync.py                ← sincroniza local ↔ planilha (Opção B)
    ├── system_prompt.txt      ← instruções da IA
    ├── requirements.txt
    └── .env.example
```

**Tecnologias:** Python, pandas, scipy, Streamlit, fpdf2, Google Apps Script (Sheets sem Google Cloud), Claude API (interpretação opcional) e Claude Code (Opção B).
