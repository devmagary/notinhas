# SIGEduc Auto 🎓📊

> Automação inteligente, segura e simplificada para professores da **Rede Estadual da Bahia** no portal **SIGEduc**.

<p align="center">
  <a href="https://github.com/devmagary/notinhas/releases/latest/download/sigeduc-extensao.zip">
    <img src="https://img.shields.io/badge/📥%20BAIXAR%20EXTENSÃO%20PRONTA%20(.ZIP)-CLIQUE%20AQUI-success?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Baixar Extensão Pronta" height="46">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/extens%C3%A3o-v1.0.5-brightgreen?style=flat-square&logo=googlechrome" alt="Extensão v1.0.5">
  <img src="https://img.shields.io/badge/navegadores-Chrome%20%7C%20Edge%20%7C%20Brave%20%7C%20Opera-blue?style=flat-square" alt="Navegadores">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square&logo=python" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/dados-100%25%20locais%20(LGPD)-success?style=flat-square" alt="Privacidade LGPD">
  <img src="https://img.shields.io/badge/licen%C3%A7a-Livre%20%2F%20Educacional-orange?style=flat-square" alt="Licença Livre">
</p>

---

## 🧭 Escolha a Melhor Opção para a Sua Rotina

O projeto oferece **três formas flexíveis de uso** para atender a diferentes perfis de professores e necessidades:

| Comparativo | 🌐 Opção 1: Extensão Web (Recomendada) | 💻 Opção 2: App Desktop Python (GUI) | 🛠️ Opção 3: Terminal & Scraping (CLI) |
|---|---|---|---|
| **Para quem é?** | **95% dos professores no dia a dia** | Professores com chamadas acumuladas | Coordenação / Gestão de Dados |
| **Precisa de Python?** | ❌ **Não! (Zero dependências)** | ✔️ Sim (Python 3.8+) | ✔️ Sim (Python 3.8+) |
| **Ambiente de uso** | Direto no Chrome, Edge, Brave, Opera | Janela gráfica com CustomTkinter | Linha de comando / Terminal |
| **Lançamento de Notas via Excel** | ✔️ **Sim (100% automático)** | ✔️ Sim | ❌ Apenas extração |
| **Gera Modelo Excel em Branco** | ✔️ **Sim (Com fórmulas `=SOMA`)** | ❌ Não | ❌ Não |
| **Falta Vinculada (FV)** | ✔️ **Sim (Alinhamento por coluna)** | ✔️ Sim | ❌ Apenas leitura |
| **Lançamento de Frequência em Massa** | ⏳ Em desenvolvimento | ✔️ **Sim (Múltiplas datas por calendário)** | ✔️ Sim (`lancar_frequencia.py`) |
| **Extração Geral de Turmas e Notas** | ❌ Não | ❌ Não | ✔️ **Sim (`sigeduc_scraper.py`)** |

---

## 🌐 Opção 1: Extensão para Navegador (Instalação em 1 Minuto)

A extensão é a forma mais rápida de lançar notas: ela roda dentro do seu próprio navegador sem deslogar da sua conta e processa a planilha inteira localmente.

### ⚡ Instalação Rápida (Windows):
1. **[Clique aqui para Baixar a Extensão (`sigeduc-extensao.zip`)](https://github.com/devmagary/notinhas/releases/latest/download/sigeduc-extensao.zip)**.
2. Extraia a pasta `.zip` no seu computador.
3. Dê **duplo clique** no arquivo `instalar_extensao.bat`.
4. O instalador copiará a extensão para uma pasta permanente e abrirá a tela de extensões do seu navegador:
   - **Google Chrome:** `chrome://extensions`
   - **Microsoft Edge:** `edge://extensions`
   - **Brave Browser:** `brave://extensions`
   - **Opera / Opera GX:** `opera://extensions`
5. No navegador, ative a chave **"Modo do desenvolvedor"** (canto superior direito), clique em **"Carregar sem compactação"** e selecione a pasta da extensão!

> 💡 **Dica:** Clique no ícone de "Quebra-cabeça" na barra superior do navegador e fixe o **SIGEduc Auto** para acesso imediato.

### 🎯 Principais Recursos da Extensão:
- **Geração de Planilha Modelo em Branco (`.xlsx`):** Não tem planilha pronta? Entre na tela de notas com as avaliações criadas, abra a extensão e clique em **"Baixar Planilha Modelo"**. Ela baixa um Excel já formatado com o nome de todos os alunos e com a fórmula de soma nativa do Excel (`=SOMA(B2:D2)`).
- **Leitura Inteligente de Excel:** Arraste qualquer planilha com 1, 2, 3, 4 ou mais atividades. Detecta nomes e colunas automaticamente.
- **Tolerância Fonética de Nomes:** Reconhece alunos mesmo com acentos, cedilhas ou grafias diferentes (*Rebouças* vs *Reboucas*, *Luiz* vs *Luis*) sem jamais misturar alunos com mesmo prenome.
- **Falta Vinculada (FV) Automática:** Marca as checkboxes de FV estritamente para alunos ausentes na planilha.

---

## 💻 Opção 2: Aplicativo Desktop em Python (Interface Gráfica)

Ideal para professores que precisam realizar o **lançamento de frequência/chamada em lote** em múltiplas datas retroativas.

### Requisitos:
- **Python 3.8** ou superior instalado.

### Passo a Passo:
1. Clone este repositório ou baixe o código-fonte:
   ```bash
   git clone https://github.com/devmagary/notinhas.git
   cd notinhas
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Inicie o aplicativo:
   ```bash
   python sigeduc_gui.py
   ```
4. Na interface gráfica:
   - Escolha **Lançar Frequência** (selecionando as datas no calendário interativo) ou **Lançar Notas**.
   - Acompanhe a execução e os logs em tempo real na tela.

---

## 🛠️ Opção 3: Linha de Comando e Scraping Acadêmico

Para desenvolvedores ou relatórios completos de turmas:

### Lançamento de Frequência via CLI:
```bash
python lancar_frequencia.py
```

### Extração Geral de Dados Acadêmicos para Excel:
Extrai notas, faltas vinculadas e histórico de frequência de todas as turmas cadastradas para um relatório consolidado `.xlsx`:

```bash
# Execução interativa:
python sigeduc_scraper.py

# Apenas notas de todas as turmas:
python sigeduc_scraper.py --modo=notas --saida=todas_notas.xlsx

# Modo silencioso em segundo plano:
python sigeduc_scraper.py --headless --modo=todos --saida=relatorio_geral.xlsx
```

---

## 📁 Estrutura do Repositório

```
notinhas/
├── extensao-notas/             # 🌐 Extensão para navegadores Chromium (Manifest V3)
│   ├── manifest.json           # Configuração da extensão (v1.0.5)
│   ├── instalar_extensao.bat   # Instalador rápido de 1 clique para Windows
│   ├── content/                # Scripts injetados no SIGEduc (DOM & RichFaces)
│   ├── lib/                    # Algoritmos de casamento de nomes e leitura Excel
│   ├── popup/                  # Interface visual do popup da extensão
│   ├── scripts/                # Script de empacotamento para distribuição
│   ├── tests/                  # Suíte completa de testes automatizados (25 testes)
│   └── vendor/                 # Biblioteca SheetJS (XLSX) empacotada
├── sigeduc_gui.py              # 💻 Interface Gráfica Desktop em CustomTkinter
├── sigeduc_core.py             # Motor de automação Playwright para desktop
├── sigeduc_scraper.py          # Extrator e web scraper acadêmico para Excel
├── lancar_frequencia.py        # Interface CLI para chamada
├── requirements.txt            # Dependências Python do projeto
└── README.md                   # Este manual unificado
```

---

## 🔒 Segurança, Privacidade e LGPD

- **100% Processamento Local:** Nenhum dado de notas, frequência, nomes ou matrículas é enviado para servidores externos. Todo o processamento ocorre exclusivamente na memória do seu computador.
- **Senhas:** Quando utilizada a gravação automática com senha, esta é manipulada unicamente em memória temporária para confirmação no portal e jamais é salva em disco.
- **Privacidade por Padrão:** O arquivo `.gitignore` protege contra o envio acidental de arquivos `.xlsx`, `.csv` e logs locais com informações reais de estudantes ao repositório público.

---

## 📄 Licença

Projeto desenvolvido para apoio e valorização da atividade docente na rede pública de ensino. Uso livre para fins educacionais.
