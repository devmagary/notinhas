"""
Sigeduc Auto — Módulo Core
===========================
Funções utilitárias compartilhadas entre a GUI e o CLI.
Inclui: leitura de arquivos, comparação de nomes, controle do Playwright,
        logging, configuração persistente e constantes centralizadas.
"""

import sys
import os
import re
import time
import json
import logging
import unicodedata
import datetime
from pathlib import Path

# =============================================
# Instalação automática de dependências
# =============================================
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("Playwright não encontrado. Instalando...")
    os.system(f"{sys.executable} -m pip install playwright")
    os.system(f"{sys.executable} -m playwright install chromium")
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

try:
    import openpyxl
except ImportError:
    print("openpyxl não encontrado. Instalando...")
    os.system(f"{sys.executable} -m pip install openpyxl")
    import openpyxl


# =============================================
# Constantes Centralizadas (#19)
# =============================================
URL_FREQUENCIA = "https://sigeduc.educacao.ba.gov.br/sigeduc/portais/docente/docente.jsf"
PASTA_PROJETO = Path(__file__).parent
PERFIL_NAVEGADOR = PASTA_PROJETO / "perfil_navegador"
CONFIG_PATH = PASTA_PROJETO / "config.json"
LOG_PATH = PASTA_PROJETO / "sigeduc_auto.log"

TIMEOUT_TABELA = 10000       # ms — espera carregar tabela de alunos
TIMEOUT_PAGINA = 60000       # ms — espera carregar página completa
TIMEOUT_NETWORKIDLE = 15000  # ms — espera networkidle pós-gravação
TIMEOUT_CLICK = 1500         # ms — espera por clique em checkbox/input
ESPERA_CARREGAMENTO = 3      # s  — sleep após carregamento de página
ESPERA_POS_GRAVACAO = 2      # s  — sleep pós-gravação
ESPERA_PRE_CHECKBOX = 1      # s  — sleep antes de manipular checkboxes
SLOW_MO = 200                # ms — delay do Playwright entre ações
MAX_TENTATIVAS_CONTEUDO = 5  # tentativas para obter conteúdo da página
MAX_TENTATIVAS_DATA = 3      # tentativas para encontrar data no calendário

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]


# =============================================
# Logging Persistente (#20)
# =============================================
logger = logging.getLogger("sigeduc_auto")
logger.setLevel(logging.DEBUG)

# Evita adicionar handlers duplicados se o módulo for recarregado
if not logger.handlers:
    # Handler: arquivo de log
    fh = logging.FileHandler(str(LOG_PATH), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)

    # Handler: console (fallback, se não estiver usando a GUI)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)


# =============================================
# Configuração Persistente (#11)
# =============================================
def salvar_config(dados: dict):
    """Salva configurações do usuário em um arquivo JSON local."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.warning("Não foi possível salvar configurações.")


def carregar_config() -> dict:
    """Carrega configurações salvas do arquivo JSON."""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        logger.warning("Não foi possível carregar configurações anteriores.")
    return {}


# =============================================
# Comparação Robusta de Nomes (#1 e #15)
# =============================================
def normalizar_nome(nome: str) -> str:
    """Remove acentos, caracteres especiais e normaliza espaços."""
    # Normaliza unicode e remove marcas de combinação (acentos)
    nome = unicodedata.normalize("NFKD", nome)
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    # Remove tudo que não seja letra ou espaço
    nome = re.sub(r"[^A-Za-z\s]", "", nome)
    # Normaliza espaços e converte para maiúsculo
    return " ".join(nome.upper().split())


def nomes_correspondem(nome_tela: str, nome_lista: str) -> bool:
    """
    Compara dois nomes de forma robusta, evitando falsos positivos.
    
    Regras:
    - Match exato (após normalização) → True
    - Mesmas 2 primeiras palavras (nome + sobrenome) → True  
    - Se um é prefixo do outro em termos de PALAVRAS completas
      (ex: "MARIA SILVA" está contido em "MARIA SILVA SANTOS") → True
    - Substring parcial (ex: "MARIA" dentro de "MARIANA") → False
    """
    a = normalizar_nome(nome_tela)
    b = normalizar_nome(nome_lista)

    # 1. Match exato
    if a == b:
        return True

    partes_a = a.split()
    partes_b = b.split()

    # Proteção: nomes com menos de 2 partes não devem dar match parcial
    if not partes_a or not partes_b:
        return False

    # 2. Primeiro nome DEVE ser idêntico (elimina ANA vs MARIANA)
    if partes_a[0] != partes_b[0]:
        return False

    # 3. Mesmas 2 primeiras palavras (nome + primeiro sobrenome)
    if len(partes_a) >= 2 and len(partes_b) >= 2:
        if partes_a[0] == partes_b[0] and partes_a[1] == partes_b[1]:
            return True

    # 4. Um é prefixo do outro em palavras completas (mínimo 2 palavras no menor)
    menor = partes_a if len(partes_a) <= len(partes_b) else partes_b
    maior = partes_b if len(partes_a) <= len(partes_b) else partes_a

    if len(menor) >= 2:
        # Verifica se as palavras do menor são um prefixo sequencial do maior
        if maior[:len(menor)] == menor:
            return True

    return False


def encontrar_na_lista(nome_tela: str, nomes: list[str]) -> bool:
    """Verifica se o nome da tela corresponde a algum nome da lista."""
    return any(nomes_correspondem(nome_tela, n) for n in nomes)


# =============================================
# Leitura de Arquivos
# =============================================
def ler_nomes(caminho_arquivo: str) -> list[str]:
    """Lê nomes de um arquivo CSV/TXT ou XLSX (coluna A). (#8)"""
    if caminho_arquivo.lower().endswith(".xlsx"):
        return _ler_nomes_xlsx(caminho_arquivo)
    else:
        return _ler_nomes_texto(caminho_arquivo)


def _ler_nomes_texto(caminho_arquivo: str) -> list[str]:
    """Lê nomes do arquivo CSV/TXT (1ª coluna de cada linha)."""
    nomes = []

    # Tenta ler com diferentes codificações (comum CSV do Excel vir como latin-1)
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    conteudo = ""
    for enc in encodings:
        try:
            with open(caminho_arquivo, "r", encoding=enc) as f:
                conteudo = f.read()
            break
        except UnicodeDecodeError:
            continue

    for linha in conteudo.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        # Pega a primeira coluna (antes de vírgula ou ponto-e-vírgula)
        nome = linha.split(",")[0].split(";")[0].strip().upper()
        if len(nome) > 1:
            nomes.append(nome)

    return nomes


def _ler_nomes_xlsx(caminho_arquivo: str) -> list[str]:
    """Lê nomes da coluna A de um arquivo XLSX (a partir da linha 2)."""
    nomes = []
    wb = openpyxl.load_workbook(caminho_arquivo, data_only=True)
    try:
        planilha = wb.active
        for linha in planilha.iter_rows(min_row=2, max_col=1, values_only=True):
            if linha and linha[0]:
                nome = str(linha[0]).strip().upper()
                if len(nome) > 1:
                    nomes.append(nome)
    finally:
        wb.close()
    return nomes


def letra_para_indice(letra: str) -> int:
    """Converte letras de colunas do Excel (A, B, Z, AA) em índices (A=0, B=1)."""
    letra = letra.strip().upper()
    soma = 0
    for i, c in enumerate(reversed(letra)):
        if "A" <= c <= "Z":
            soma += (ord(c) - 64) * (26 ** i)
    return max(0, soma - 1)


def ler_notas_xlsx(caminho_arquivo: str, letras_colunas: list[str]) -> dict:
    """Lê as notas do arquivo XLSX e retorna { 'NOME': [nota1, nota2, ...] }. (#16 wb.close)"""
    notas = {}
    wb = openpyxl.load_workbook(caminho_arquivo, data_only=True)
    try:
        planilha = wb.active
        indices_colunas = [letra_para_indice(l) for l in letras_colunas]

        for linha in planilha.iter_rows(min_row=2, values_only=True):
            if not linha or not linha[0]:
                continue
            nome = str(linha[0]).strip().upper()

            valores = []
            for idx in indices_colunas:
                val = linha[idx] if len(linha) > idx else None
                if val is None or str(val).strip() in ("-", ""):
                    valores.append("")
                else:
                    valores.append(str(val).replace(".", ",").strip())

            notas[nome] = valores
    finally:
        wb.close()
    return notas


# =============================================
# Parsing e Validação de Datas (#7)
# =============================================
def parsear_datas(texto_datas: str) -> list[tuple[int, int]]:
    """Converte '11/03, 18/03, 01/04' em [(11,3), (18,3), (1,4)] com validação real."""
    datas = []
    ano_atual = datetime.date.today().year

    for parte in texto_datas.split(","):
        parte = parte.strip()
        if "/" not in parte:
            continue
        pedacos = parte.split("/")
        if len(pedacos) < 2:
            continue
        try:
            d, m = int(pedacos[0]), int(pedacos[1])
            # Valida se a data é real
            datetime.date(ano_atual, m, d)
            datas.append((d, m))
        except (ValueError, IndexError):
            logger.warning(f"  ⚠ Data inválida ignorada: {parte}")
    return datas


# =============================================
# Controle do Navegador (Playwright)
# =============================================
def obter_conteudo_seguro(page) -> str:
    """Obtém conteúdo da página com backoff exponencial. (#14)"""
    for i in range(MAX_TENTATIVAS_CONTEUDO):
        try:
            return page.content()
        except Exception:
            time.sleep(min(2 ** i, 8))
    return ""


def trazer_navegador_para_frente():
    """Traz o navegador Chrome do Sigeduc para o primeiro plano no Windows. (#17 ctypes fix)"""
    try:
        import ctypes
        EnumWindows = ctypes.windll.user32.EnumWindows
        # Corrigido: c_void_p em vez de c_pointer (que não existe)
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
        ShowWindow = ctypes.windll.user32.ShowWindow

        def foreach_window(hwnd, lParam):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if any(term in title for term in ["sigeduc", "docente", "frequência", "diário", "chrome"]):
                        ShowWindow(hwnd, 9)  # SW_RESTORE
                        SetForegroundWindow(hwnd)
                        return False
            return True

        EnumWindows(EnumWindowsProc(foreach_window), 0)
    except Exception:
        pass


def tratar_dialogo_confirmacao(page):
    """Configura handler para aceitar automaticamente os dialogs do site. (#13 truncamento fix)"""
    def handler(dialog):
        msg = dialog.message
        msg_display = f"{msg[:60]}..." if len(msg) > 60 else msg
        logger.info(f"  ✓ Diálogo detectado: '{msg_display}' → Aceitando.")
        dialog.accept()
    page.on("dialog", handler)


def aguardar_pos_gravacao(page):
    """Aguarda o site processar a gravação (redirect ou AJAX)."""
    logger.info("  Aguardando processamento do site...")
    try:
        page.wait_for_load_state("networkidle", timeout=TIMEOUT_NETWORKIDLE)
    except PWTimeout:
        pass
    time.sleep(ESPERA_POS_GRAVACAO)


# =============================================
# Detecção de Calendário
# =============================================
def e_tabela_calendario(tabela) -> bool:
    """Verifica se uma tabela possui características de um calendário mensal."""
    try:
        texto = (tabela.inner_text() or "").upper()
        dias_semana = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"]
        contador_dias = sum(1 for d in dias_semana if d in texto)
        if contador_dias >= 4:
            links = tabela.query_selector_all("a")
            if len(links) > 5:
                return True
    except Exception:
        pass
    return False


def garantir_pagina_calendario(page):
    """Verifica se estamos na página do calendário e navega se necessário."""
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PWTimeout:
        pass

    conteudo = obter_conteudo_seguro(page)
    if "Calendário" in conteudo:
        for tab in page.query_selector_all("table"):
            if e_tabela_calendario(tab):
                return True

    logger.info("  ⚠ Não estamos no calendário. Navegando de volta...")

    links = page.query_selector_all("a")
    for link in links:
        try:
            texto = link.inner_text().upper()
        except Exception:
            continue
        if "VOLTAR" in texto or "FREQUÊNCIA" in texto:
            link.click()
            time.sleep(ESPERA_CARREGAMENTO)
            try:
                page.wait_for_load_state("networkidle", timeout=TIMEOUT_TABELA)
            except PWTimeout:
                pass
            for tab in page.query_selector_all("table"):
                if e_tabela_calendario(tab):
                    return True

    logger.info("  Navegando para a URL do portal...")
    page.goto(URL_FREQUENCIA, wait_until="networkidle", timeout=TIMEOUT_PAGINA // 2)
    time.sleep(ESPERA_CARREGAMENTO)

    for tab in page.query_selector_all("table"):
        if e_tabela_calendario(tab):
            return True

    return False


def encontrar_dia_no_calendario(page, dia: int, mes: int) -> bool:
    """Encontra e clica no dia correto dentro do mês correto no calendário."""
    nome_mes = MESES[mes - 1]
    logger.info(f"  Procurando dia {dia} no mês de {nome_mes}...")

    tabelas = page.query_selector_all("table")
    for tabela in tabelas:
        try:
            texto_tabela = tabela.inner_text()
        except Exception:
            continue
        if nome_mes not in texto_tabela:
            continue

        links = tabela.query_selector_all("a")
        for link in links:
            try:
                if link.inner_text().strip() == str(dia):
                    logger.info(f"  ✓ Dia {dia} encontrado e clicável. Clicando...")
                    link.click()
                    return True
            except Exception:
                continue

    logger.warning(f"  ✗ Dia {dia} de {nome_mes} não é clicável no calendário.")
    return False


# =============================================
# Marcação de Presenças
# =============================================
def marcar_presencas(page, nomes: list[str], modo: str) -> int:
    """Marca ou desmarca os checkboxes de presença para os alunos da lista."""
    logger.info("  Aguardando tabela de alunos...")
    try:
        page.wait_for_selector("#tableAlunos tbody tr", timeout=TIMEOUT_TABELA)
    except PWTimeout:
        logger.warning("  ⚠ Tabela de alunos não carregou. Tentando continuar...")

    time.sleep(ESPERA_PRE_CHECKBOX)

    linhas = page.query_selector_all("#tableAlunos tbody tr")
    logger.info(f"  Alunos encontrados na tela: {len(linhas)}")

    marcados = 0
    for linha in linhas:
        celula_nome = linha.query_selector("td:nth-child(3)")
        if not celula_nome:
            continue

        nome_tela = celula_nome.inner_text().strip().upper()

        # Comparação robusta de nomes (#1)
        na_lista = encontrar_na_lista(nome_tela, nomes)

        checkboxes = linha.query_selector_all('input[type="checkbox"]')

        # Filtra apenas checkboxes habilitados
        habilitados = []
        tem_desabilitado = False
        for cb in checkboxes:
            try:
                if cb.is_disabled() or cb.get_attribute("disabled") is not None:
                    tem_desabilitado = True
                else:
                    habilitados.append(cb)
            except Exception:
                tem_desabilitado = True

        if tem_desabilitado:
            logger.info(f"  ⚠ {nome_tela}: Registro bloqueado/justificado (não alterado).")

        if len(habilitados) >= 1:
            if modo == "1":
                # Faltosos na lista: marcar falta na lista, presença no resto
                if na_lista:
                    for cb in habilitados:
                        try:
                            if not cb.is_checked(): cb.click(timeout=TIMEOUT_CLICK)
                        except Exception:
                            pass
                    marcados += 1
                else:
                    for cb in habilitados:
                        try:
                            if cb.is_checked(): cb.click(timeout=TIMEOUT_CLICK)
                        except Exception:
                            pass

            elif modo == "2":
                # Presentes na lista: presença na lista, falta no resto
                if na_lista:
                    for cb in habilitados:
                        try:
                            if cb.is_checked(): cb.click(timeout=TIMEOUT_CLICK)
                        except Exception:
                            pass
                else:
                    for cb in habilitados:
                        try:
                            if not cb.is_checked(): cb.click(timeout=TIMEOUT_CLICK)
                        except Exception:
                            pass
                    marcados += 1

            elif modo == "3":
                # Presença na lista, ignora o resto
                if na_lista:
                    for cb in habilitados:
                        try:
                            if cb.is_checked(): cb.click(timeout=TIMEOUT_CLICK)
                        except Exception:
                            pass
                    marcados += 1

            elif modo == "4":
                # Falta em quem NÃO está na lista, ignora a lista
                if not na_lista:
                    for cb in habilitados:
                        try:
                            if not cb.is_checked(): cb.click(timeout=TIMEOUT_CLICK)
                        except Exception:
                            pass
                    marcados += 1

    return marcados


# =============================================
# Lançamento de Notas
# =============================================
def lancar_notas(page, dados_notas: dict) -> int:
    """Preenche as notas na página para os alunos fornecidos no dicionário."""
    logger.info("  Aguardando tabela de notas...")
    try:
        page.wait_for_selector(
            "table tbody tr input:not([type='hidden']):not([type='checkbox']):not([type='radio'])",
            timeout=TIMEOUT_TABELA,
        )
    except Exception:
        logger.warning("  ⚠ Tabela de notas não carregou. Tentando continuar...")

    time.sleep(ESPERA_PRE_CHECKBOX)

    linhas = page.query_selector_all("table tbody tr")
    logger.info("  Verificando linhas na tabela para notas...")

    alunos_preenchidos = 0
    for linha in linhas:
        try:
            texto_linha = linha.inner_text().strip().upper()
        except Exception:
            continue

        if not texto_linha:
            continue

        # Comparação robusta de nomes (#15)
        aluno_encontrado = None
        for nome_xlsx in dados_notas.keys():
            if nomes_correspondem(texto_linha, nome_xlsx):
                aluno_encontrado = nome_xlsx
                break
            # Fallback: verifica se o nome do xlsx está contido na linha
            # (a linha pode ter número, matrícula + nome)
            nome_normalizado = normalizar_nome(nome_xlsx)
            linha_normalizada = normalizar_nome(texto_linha)
            if nome_normalizado in linha_normalizada:
                # Confere que não é substring (ex: MARIA em MARIANA)
                # Verifica se as palavras do nome existem como palavras completas na linha
                palavras_nome = nome_normalizado.split()
                palavras_linha = linha_normalizada.split()
                if len(palavras_nome) >= 2 and all(p in palavras_linha for p in palavras_nome):
                    aluno_encontrado = nome_xlsx
                    break

        if not aluno_encontrado:
            continue

        notas = dados_notas[aluno_encontrado]
        qtd_notas = len(notas)

        inputs_brutos = linha.query_selector_all(
            "input:not([type='hidden']):not([type='checkbox']):not([type='radio'])"
        )
        inputs = [inp for inp in inputs_brutos if inp.is_visible()]

        if len(inputs) >= qtd_notas:
            for i in range(qtd_notas):
                val = notas[i]
                if val != "":
                    try:
                        if not inputs[i].is_disabled() and inputs[i].get_attribute("disabled") is None:
                            inputs[i].fill(val, timeout=TIMEOUT_CLICK)
                    except Exception as e:
                        logger.warning(f"  ⚠ Erro ao preencher nota de {aluno_encontrado}: {e}")

            alunos_preenchidos += 1

    return alunos_preenchidos


# =============================================
# Gravação de Dados
# =============================================
def preencher_senha_e_gravar(page, senha: str) -> bool:
    """Preenche a senha do site e clica em Gravar. (#2 retorna False se campo não encontrado)"""
    # Encontra o campo de senha do Sigeduc
    campos_senha = page.query_selector_all('input[type="password"]')
    if campos_senha:
        campo = campos_senha[0]
        campo.fill(senha)
        logger.info("  ✓ Senha preenchida.")
    else:
        logger.error("  ✗ Campo de senha não encontrado! Abortando gravação.")
        return False

    time.sleep(0.5)

    # Procura o botão Gravar/Salvar
    for seletor_texto in ["Gravar", "gravar", "GRAVAR", "Salvar", "salvar", "Cadastrar"]:
        botoes = page.query_selector_all(
            f"button:has-text('{seletor_texto}'), a:has-text('{seletor_texto}'), input[value='{seletor_texto}']"
        )
        for btn in botoes:
            try:
                if btn.is_visible():
                    logger.info(f"  ✓ Botão '{seletor_texto}' encontrado. Clicando...")
                    btn.click()
                    return True
            except Exception:
                continue

    # Fallback: busca por texto no innerText
    todos = page.query_selector_all("button, input[type='submit'], input[type='button'], a")
    for el in todos:
        try:
            texto = (el.inner_text() or el.get_attribute("value") or "").upper()
        except Exception:
            continue
        if ("GRAVAR" in texto or "SALVAR" in texto) and el.is_visible():
            logger.info(f"  ✓ Botão encontrado via fallback: '{texto.strip()}'")
            el.click()
            return True

    logger.error("  ✗ Botão de Gravar NÃO encontrado!")
    return False
