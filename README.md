# Sigeduc Auto

Automação em Python desenvolvida para simplificar e agilizar a rotina de professores no portal SIGEduc (Rede Estadual da Bahia). O sistema automatiza o lançamento em lote de frequências (presenças e faltas) e notas avaliativas lendo diretamente de planilhas Excel (XLSX) ou arquivos de texto (CSV/TXT).

---

## Funcionalidades

- **Lançamento de Frequência em Massa:** Permite selecionar múltiplas datas via calendário interativo ou digitação para preenchimento sequencial das listas de chamada.
- **Lançamento de Notas por Coluna:** Lê as notas de atividades (Simulado, Atividade 1, Atividade 2, etc.) na ordem indicada das colunas da planilha e preenche nos campos correspondentes do portal.
- **Seleção e Troca Automática de Unidade:** Controle para definir a unidade avaliativa (1ª, 2ª, 3ª ou 4ª Unidade). O robô verifica o componente de abas do SIGEduc e comuta automaticamente para a unidade correta caso o portal reinicie na primeira.
- **Atribuição de Falta Vinculada (FV):** Identifica notas em branco ou registros de ausência e marca as checkboxes de Falta Vinculada na tela de verificação de avaliações não realizadas.
- **Desambiguação Avançada de Nomes:** Sistema de correspondência com normalização Unicode (remoção de acentos e cedilha), tratamento fonético e verificação estrita de sobrenomes de família. Evita duplicações ou trocas de notas entre estudantes com prenomes iguais (por exemplo, Maria Vitória Santos Lisboa vs. Maria Vitória Tosta do Amaral).
- **Tratamento de Formato Decimal:** Suporte a notas com separador decimal por ponto (padrão do portal), vírgula ou formato original.
- **Gravação com Confirmação de Senha:** Suporte ao preenchimento automatizado de senha no novo popup modal de confirmação do SIGEduc, com opção de modo manual para revisão prévia.
- **Duas Opções de Interface:** Interface gráfica moderna (GUI) com acompanhamento de logs em tempo real e versão via terminal (CLI).

---

## Estrutura do Projeto

- `sigeduc_gui.py`: Interface gráfica para o usuário construída em CustomTkinter.
- `sigeduc_core.py`: Motor de automação com Playwright, tratamento de DOM, normalização de nomes e lógica de navegação.
- `sigeduc_scraper.py`: Módulo de web scraping para extração de dados acadêmicos (turmas, notas, atividades e frequência) e exportação em Excel estruturado.
- `lancar_frequencia.py`: Interface interativa de linha de comando (CLI).
- `requirements.txt`: Relação de dependências do projeto.
- `exemplo_alunos.txt`: Arquivo modelo com lista de estudantes para testes de frequência.


---

## Requisitos e Instalação

Necessário **Python 3.8** ou superior instalado.

1. Clone o repositório ou baixe os arquivos do projeto:
   ```bash
   git clone https://github.com/devmagary/notinhas.git
   cd notinhas
   ```

2. Instale as dependências listadas:
   ```bash
   pip install -r requirements.txt
   ```

3. Instale os navegadores do Playwright (se for a primeira utilização do Playwright na máquina):
   ```bash
   playwright install chromium
   ```

---

## Como Executar

### Interface Gráfica (Recomendado)

Execute o comando no terminal:
```bash
python sigeduc_gui.py
```

Passo a passo na interface:
1. Escolha a tarefa desejada: **Lançar Frequência** ou **Lançar Notas**.
2. Selecione o arquivo de dados (`.xlsx`, `.csv` ou `.txt`).
3. Para notas: informe as letras das colunas da planilha na mesma ordem da tela do SIGEduc (exemplo: `D, B, C`), selecione a **Unidade Avaliativa** e a opção de **Falta Vinculada (FV)**.
4. Para frequência: selecione as datas desejadas no calendário.
5. Marque a opção de gravação automática e informe a senha do portal (opcional).
6. Clique em **Iniciar Automação** e acompanhe a execução na janela do navegador e no painel de logs.

### Linha de Comando (CLI)

Para operar diretamente pelo terminal sem interface gráfica:
```bash
python lancar_frequencia.py
```

### Extração de Dados Acadêmicos para Excel (Scraping)

Para extrair as notas, atividades, faltas vinculadas e histórico de frequência de todas as turmas e gerar uma planilha Excel `.xlsx` multi-aba formatada:

```bash
# Execução interativa (pergunta interativamente o modo: Notas, Frequência ou Ambos, e credenciais seguras)
python sigeduc_scraper.py

# Apenas notas e resultados
python sigeduc_scraper.py --modo=notas --saida=notas_gerais.xlsx

# Apenas histórico de frequência
python sigeduc_scraper.py --modo=frequencia --saida=frequencia_geral.xlsx

# Execução completa em background (silenciosa)
python sigeduc_scraper.py --headless --modo=todos --saida=relatorio_completo.xlsx
```

---

## Segurança e Privacidade

- **Senhas:** A senha informada é utilizada exclusivamente em memória no momento da gravação no portal e não é gravada em arquivos locais nem enviada a servidores externos.
- **Proteção de Dados (LGPD):** O arquivo `.gitignore` vem configurado para ignorar planilhas reais de notas (`*.xlsx`, `*.csv`), logs locais e pastas de perfis de sessão do navegador (`perfil_navegador/`), impedindo a submissão acidental de dados pessoais de estudantes a repositórios públicos.

---

## Licença

Este projeto é de uso livre para fins educacionais e apoio à atividade docente.
