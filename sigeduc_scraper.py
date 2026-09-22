"""
Módulo de Extração de Dados e Web Scraping Acadêmico — SIGEduc Bahia
=====================================================================
Extrai dados acadêmicos do portal SIGEduc (Turmas, Notas, Avaliações, Pesos,
Faltas Vinculadas e Frequência diária) e consolida em planilha Excel (.xlsx)
estruturada com pandas e openpyxl.

Uso via linha de comando:
    python sigeduc_scraper.py
    python sigeduc_scraper.py --headless --modo=notas --saida=notas_turmas.xlsx
"""

import sys
import os
import re
import time
import getpass
import argparse
import logging
from pathlib import Path
from typing import Any

# Instalação / importação defensiva de dependências
try:
    import pandas as pd
except ImportError:
    os.system(f"{sys.executable} -m pip install pandas")
    import pandas as pd

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    os.system(f"{sys.executable} -m pip install openpyxl")
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import sigeduc_core as sc

# =====================================================================
# Configuração de Logging do Scraper
# =====================================================================
logger = logging.getLogger("sigeduc_scraper")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(ch)


# Garante codificação UTF-8 no console do Windows para evitar UnicodeEncodeError
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# =====================================================================
# Funções de Sanitização para o Excel
# =====================================================================
def formatar_nome_aba(turma: str, componente: str, sufixo: str, abas_existentes: set[str] | None = None) -> str:
    """
    Gera um nome de aba válido para o Excel respeitando rigorosamente:
    - Limite máximo de 31 caracteres;
    - Remoção dos caracteres proibidos: [ ] : ? * / \\
    - Prevenção de colisões com abas já existentes (adicionando sufixo _1, _2).
    - Preservação do número e letra da turma (ex: 3A, 2B, 1EMI).
    """
    import unicodedata

    def limpar_ascii(s: str) -> str:
        s = unicodedata.normalize("NFKD", str(s or ""))
        return "".join(c for c in s if not unicodedata.combining(c)).upper()

    # Dicionário de abreviações úteis para componentes curriculares comuns
    abrevs = {
        "HISTORIA": "Hist", "MATEMATICA": "Mat", "LINGUA PORTUGUESA": "Port",
        "PORTUGUES": "Port", "GEOGRAFIA": "Geo", "CIENCIAS": "Cien",
        "INFORMATICA": "Info", "EDUCACAO FISICA": "EdFis", "BIOLOGIA": "Bio",
        "QUIMICA": "Quim", "FISICA": "Fis", "FILOSOFIA": "Filo",
        "SOCIOLOGIA": "Socio", "ARTE": "Arte", "INGLES": "Ing", "ESPANHOL": "Esp"
    }

    comp_limpo = limpar_ascii(componente)
    comp_abrev = ""
    for k, v in abrevs.items():
        if k in comp_limpo:
            comp_abrev = v
            break
    if not comp_abrev:
        partes = [p for p in comp_limpo.split() if p not in sc.PREPOSICOES_NOME]
        comp_abrev = partes[0][:6].capitalize() if partes else "Disc"

    # Limpa ordinais antes da normalização NFKD para não transformar 'º' na letra 'O'
    turma_sem_ord = re.sub(r"[º°ª]", "", str(turma or ""))
    turma_limpa = limpar_ascii(turma_sem_ord)
    
    # Remove palavras estruturais como "ANO", "SERIE", "TURMA"
    turma_sem_palavras = re.sub(r"\b(ANO|SERIE|SERIES|TURMA|MATUTINO|VESPERTINO|NOTURNO|INTEGRAL)\b", "", turma_limpa)
    match_turma = re.search(r"(\d+)\s*([A-Z])\b", turma_sem_palavras)
    if match_turma:
        turma_abrev = f"{match_turma.group(1)}{match_turma.group(2)}"
    else:
        digs = re.findall(r"\d+", turma_limpa)
        letras = re.findall(r"[A-Z]", turma_sem_palavras)
        if digs and letras:
            turma_abrev = f"{digs[0]}{letras[-1]}"
        elif digs:
            turma_abrev = f"T{digs[0]}"
        else:
            turma_abrev = re.sub(r"[^A-Za-z0-9]", "", turma_limpa)[:6] or "Turma"

    # Formato padrão: "3A_Hist_U1" ou "3A_Hist_Freq"
    base = f"{turma_abrev}_{comp_abrev}_{sufixo}"
    
    # Remove caracteres estritamente proibidos pelo Excel: \ / ? * [ ] :
    base_limpa = re.sub(r'[:\\/?*\[\]]', '', base).strip()
    base_limpa = base_limpa[:31]
    if not base_limpa:
        base_limpa = f"Aba_{sufixo}"[:31]


    if abas_existentes is None:
        return base_limpa

    # Tratamento de colisão de nomes
    candidato = base_limpa
    contador = 1
    while candidato.upper() in {a.upper() for a in abas_existentes}:
        tag = f"_{contador}"
        candidato = f"{base_limpa[:31 - len(tag)]}{tag}"
        contador += 1

    abas_existentes.add(candidato)
    return candidato


# =====================================================================
# Classe Principal: SigeducScraper
# =====================================================================
class SigeducScraper:
    """
    Controlador de automação e scraping para o SIGEduc Bahia.
    Permite autenticação, mapeamento de turmas, extração de notas/frequência
    e exportação para planilha Excel formatada.
    """

    def __init__(self, headless: bool = False, slow_mo: int = 150, timeout: int = 30000):
        self.headless = headless
        self.slow_mo = slow_mo
        self.timeout = timeout
        self.playwright = None
        self.browser = None
        self.page = None

    def __enter__(self):
        self.iniciar_navegador()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fechar()

    def iniciar_navegador(self):
        """Inicia a instância do Chromium via Playwright com perfil persistente."""
        logger.info("Inicializando navegador Playwright Chromium...")
        self.playwright = sync_playwright().start()
        
        launch_kwargs = {
            "user_data_dir": str(sc.PERFIL_NAVEGADOR),
            "headless": self.headless,
            "slow_mo": self.slow_mo,
            "viewport": {"width": 1366, "height": 768},
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        try:
            self.browser = self.playwright.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
        except Exception:
            self.browser = self.playwright.chromium.launch_persistent_context(**launch_kwargs)

        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
        sc.tratar_dialogo_confirmacao(self.page)
        self.page.set_default_timeout(self.timeout)
        logger.info("Navegador pronto.")

    def fechar(self):
        """Encerra a sessão do navegador e libera recursos de forma garantida."""
        logger.info("Finalizando navegador...")
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        logger.info("Navegador encerrado.")

    def login(self, usuario: str = "", senha: str = "") -> bool:
        """
        Navega até o portal SIGEduc e realiza o login com espera explícita.
        Se a sessão já estiver ativa (cookies salvos), reaproveita sem solicitar senha.
        """
        logger.info("Acessando portal SIGEduc Bahia...")
        self.page.goto(sc.URL_FREQUENCIA, wait_until="domcontentloaded", timeout=sc.TIMEOUT_PAGINA)
        time.sleep(sc.ESPERA_CARREGAMENTO)

        conteudo = sc.obter_conteudo_seguro(self.page).lower()
        if "login" not in self.page.url.lower() and "autenticação" not in conteudo and "login.jsf" not in self.page.url:
            logger.info("✓ Sessão já autenticada detectada (perfil salvo).")
            return True

        # Se não forneceu credenciais e está na tela de login
        if not usuario or not senha:
            logger.warning("Portal solicita autenticação. Por favor, forneça usuário e senha.")
            return False

        logger.info("Inserindo credenciais de acesso...")
        try:
            # Espera explícita pelos campos de autenticação
            self.page.wait_for_selector("input[type='password']", timeout=12000)
            
            # Localiza campo de usuário (aceita variações de id/name)
            campo_user = self.page.query_selector("input[name*='user'], input[id*='usuario'], input[id*='username'], input[type='text']")
            campo_pass = self.page.query_selector("input[type='password']")

            if campo_user and campo_pass:
                campo_user.fill(usuario)
                campo_pass.fill(senha)

                btn_entrar = self.page.query_selector("input[type='submit'], button[type='submit'], input[value*='Entrar'], button:has-text('Entrar')")
                if btn_entrar:
                    btn_entrar.click()
                else:
                    campo_pass.press("Enter")

                # Espera explícita pelo painel docente ou link de logout
                try:
                    self.page.wait_for_selector(
                        "a:has-text('Sair'), a:has-text('Diário de Classe'), a:has-text('Docente'), #painel-docente", 
                        timeout=25000
                    )
                    logger.info("✓ Autenticação realizada com sucesso!")
                    time.sleep(sc.ESPERA_CARREGAMENTO)
                    return True
                except PWTimeout:
                    # Verifica mensagens de erro na tela
                    msg_el = self.page.query_selector(".rich-messages, .mensagem-erro, .ui-messages-error, .alerta")
                    if msg_el:
                        msg_txt = msg_el.inner_text().strip()
                        logger.error(f"❌ Erro retornado pelo SIGEduc: {msg_txt}")
                        raise RuntimeError(f"Falha de login no SIGEduc: {msg_txt}")
                    else:
                        raise RuntimeError("Timeout ao aguardar carregamento pós-login.")
        except Exception as e:
            logger.error(f"Erro durante a autenticação: {e}")
            raise
        return False

    def navegar_diario_classe(self) -> bool:
        """Navega para a tela principal de turmas / Diário de Classe Digital."""
        logger.info("Navegando para o Diário de Classe Digital...")
        
        # 1. Se já está na página do docente com turmas visíveis
        if self._tem_tabela_turmas():
            return True

        # 2. Procura pelo link do menu "Diário de Classe" ou "Diário de Classe Digital"
        links = self.page.query_selector_all("a")
        for link in links:
            try:
                txt = sc.normalizar_nome(link.inner_text())
                if "DIARIO DE CLASSE" in txt:
                    link.click()
                    time.sleep(sc.ESPERA_CARREGAMENTO)
                    self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                    if self._tem_tabela_turmas():
                        return True
            except Exception:
                continue

        # 3. Fallback: navega para a URL do portal docente
        self.page.goto(sc.URL_FREQUENCIA, wait_until="domcontentloaded", timeout=sc.TIMEOUT_PAGINA)
        time.sleep(sc.ESPERA_CARREGAMENTO)
        return self._tem_tabela_turmas()

    def _tem_tabela_turmas(self) -> bool:
        """Verifica se há tabela de turmas renderizada no DOM."""
        for tabela in self.page.query_selector_all("table"):
            txt = sc.normalizar_nome(tabela.inner_text() or "")
            if ("COMPONENTE" in txt or "DISCIPLINA" in txt) and ("TURMA" in txt or "ALUNO" in txt):
                return True
        return False

    def listar_turmas(self) -> list[dict[str, Any]]:
        """
        Mapeia todas as turmas disponíveis com metadados:
        Nome da Turma, Ano, Escola, Oferta de Ensino, Ano/Série, Periodicidade,
        Componente Curricular e Quantidade de Alunos.
        """
        self.navegar_diario_classe()
        logger.info("Mapeando turmas atribuídas no SIGEduc...")

        turmas = []
        tabelas = self.page.query_selector_all("table")
        
        for tabela in tabelas:
            txt_tabela = sc.normalizar_nome(tabela.inner_text() or "")
            if not (("COMPONENTE" in txt_tabela or "DISCIPLINA" in txt_tabela) and "TURMA" in txt_tabela):
                continue

            linhas = tabela.query_selector_all("tbody tr")
            if not linhas:
                linhas = tabela.query_selector_all("tr")

            for idx, linha in enumerate(linhas):
                tds = linha.query_selector_all("td")
                if len(tds) < 4:
                    continue

                texto_linha = sc.normalizar_nome(linha.inner_text() or "")
                if "COMPONENTE" in texto_linha and "TURMA" in texto_linha:
                    continue  # Linha de cabeçalho interno

                # Extrai links de ações dentro da linha
                links_acoes = linha.query_selector_all("a, input[type='image'], input[type='button'], button")
                btn_notas = None
                btn_freq = None

                for acao in links_acoes:
                    try:
                        title = (acao.get_attribute("title") or "").upper()
                        alt = (acao.get_attribute("alt") or "").upper()
                        txt_acao = acao.inner_text().strip().upper()
                        onclick = (acao.get_attribute("onclick") or "").upper()
                        tudo = f"{title} {alt} {txt_acao} {onclick}"

                        if any(k in tudo for k in ["RESULTADO", "NOTA", "AVALIA", "BOLETIM"]):
                            btn_notas = acao
                        elif any(k in tudo for k in ["FREQUENCIA", "CHAMADA", "PRESENCA", "CALENDARIO"]):
                            btn_freq = acao
                    except Exception:
                        continue

                # Extrai dados das colunas
                textos_tds = [td.inner_text().strip() for td in tds]
                
                # Procura padrões de dados nas colunas
                ano = ""
                escola = ""
                oferta = ""
                turma_nome = ""
                serie = ""
                periodicidade = "ANUAL"
                componente = ""
                qtd_alunos = 0

                for t in textos_tds:
                    if re.match(r"^202\d$", t):
                        ano = t
                    elif "COLÉGIO" in t.upper() or "ESCOLA" in t.upper() or "COL." in t.upper():
                        escola = t
                    elif any(k in t.upper() for k in ["ENSINO MÉDIO", "FUNDAMENTAL", "EJA", "TÉCNICO", "PROEJA"]):
                        oferta = t
                    elif re.search(r"\d+\s*[º°]?\s*[A-Z]", t.upper()) and not turma_nome:
                        turma_nome = t
                    elif any(s in t.upper() for s in ["1ª SÉRIE", "2ª SÉRIE", "3ª SÉRIE", "4ª SÉRIE", "ANO"]):
                        serie = t
                    elif t.isdigit() and int(t) > 0 and int(t) < 100:
                        qtd_alunos = int(t)

                # Se não identificou componente curricular especificamente, procura em células de texto
                for t in textos_tds:
                    if t and t not in [ano, escola, oferta, turma_nome, serie] and not t.isdigit() and len(t) > 3:
                        if not any(k in t.upper() for k in ["VOLTAR", "EDITAR", "SALVAR", "LANÇAR"]):
                            componente = t
                            break

                if not turma_nome and len(textos_tds) >= 2:
                    turma_nome = textos_tds[1]

                info_turma = {
                    "id": len(turmas) + 1,
                    "ano": ano or str(time.strftime("%Y")),
                    "escola": escola or "SIGEduc BA",
                    "oferta_ensino": oferta or "Ensino Médio",
                    "ano_serie": serie or "Série Regular",
                    "periodicidade": periodicidade,
                    "nome_turma": turma_nome or f"Turma {len(turmas) + 1}",
                    "componente_curricular": componente or "Componente Curricular",
                    "qtd_alunos": qtd_alunos,
                    "_btn_notas": btn_notas,
                    "_btn_freq": btn_freq,
                    "_linha": linha
                }
                turmas.append(info_turma)

        logger.info(f"✓ Total de turmas mapeadas: {len(turmas)}")
        return turmas

    def extrair_notas_turma(self, turma_info: dict, unidades: list[int] = [1, 2, 3, 4]) -> dict[int, pd.DataFrame]:
        """
        Navega para a tela de notas da turma e extrai as notas e atividades
        de cada uma das unidades selecionadas.
        """
        turma_nome = turma_info["nome_turma"]
        disc = turma_info["componente_curricular"]
        logger.info(f"━━━ Extraindo Notas da Turma: {turma_nome} ({disc}) ━━━")

        # Clica no botão/link de Lançar Resultados da turma
        btn_notas = turma_info.get("_btn_notas")
        if btn_notas:
            try:
                btn_notas.click()
                time.sleep(sc.ESPERA_CARREGAMENTO)
                self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception as e:
                logger.warning(f"Não foi possível clicar diretamente no botão de notas: {e}")

        # Aguarda tabela de notas
        try:
            self.page.wait_for_selector("table", timeout=sc.TIMEOUT_TABELA)
        except PWTimeout:
            logger.error("Tabela de notas não foi encontrada na tela.")
            return {}

        resultado_unidades: dict[int, pd.DataFrame] = {}

        for unidade in unidades:
            logger.info(f"  Acessando {unidade}ª Unidade...")
            sucesso_aba = sc.garantir_unidade_ativa(self.page, unidade)
            if not sucesso_aba:
                logger.warning(f"  ⚠ Não foi possível confirmar a aba da {unidade}ª Unidade.")

            time.sleep(1)

            # Localiza a tabela principal de notas
            tabela_notas = None
            for tab in self.page.query_selector_all("table"):
                txt = sc.normalizar_nome(tab.inner_text() or "")
                if "ALUNO" in txt or "MATRICULA" in txt or "ESTUDANTE" in txt:
                    tabela_notas = tab
                    break

            if not tabela_notas:
                logger.warning(f"  Tabela de notas não localizada para a {unidade}ª Unidade.")
                continue

            # Mapeia os cabeçalhos das atividades avaliativas
            cabecalhos_cols = ["Nº", "Matrícula", "Nome do Estudante"]
            th_elementos = tabela_notas.query_selector_all("thead th, tr:first-child th, tr:first-child td")
            
            atividades_encontradas = []
            for th in th_elementos:
                txt_th = th.inner_text().strip()
                txt_norm = sc.normalizar_nome(txt_th)
                if any(ign in txt_norm for ign in ["FOTO", "NUMERO", "MATRICULA", "ALUNO", "NOME", "ACOES", "SITUACAO"]):
                    continue
                if txt_th:
                    atividades_encontradas.append(txt_th.replace("\n", " "))

            if not atividades_encontradas:
                # Nomes padrão caso o cabeçalho seja genérico
                atividades_encontradas = ["Atividade 1", "Atividade 2", "Simulado", "Média"]

            colunas_finais = cabecalhos_cols + atividades_encontradas

            # Extrai os dados dos alunos
            linhas_alunos = tabela_notas.query_selector_all("tbody tr")
            if not linhas_alunos:
                linhas_alunos = tabela_notas.query_selector_all("tr")[1:]

            registros = []
            for num_ordem, linha in enumerate(linhas_alunos, 1):
                nome = sc.extrair_nome_da_linha(linha)
                if not nome or len(nome.split()) < 2:
                    continue

                # Extrai matrícula se houver célula numérica
                matricula = ""
                tds = linha.query_selector_all("td")
                for td in tds:
                    txt_td = td.inner_text().strip()
                    if txt_td.isdigit() and len(txt_td) >= 6:
                        matricula = txt_td
                        break

                # Extrai inputs de notas ou células de notas
                inputs_nota = linha.query_selector_all("input[type='text'], input:not([type='hidden']):not([type='checkbox'])")
                valores_notas = []

                if inputs_nota:
                    for inp in inputs_nota:
                        val = inp.get_attribute("value") or ""
                        val = val.strip()
                        # Formata ou mantém
                        valores_notas.append(val if val else "-")
                else:
                    # Se não há inputs editáveis, lê as células das notas diretamente
                    for td in tds[2:]:
                        val = td.inner_text().strip()
                        if val and not any(k in val.upper() for k in ["EDITAR", "SALVAR"]):
                            valores_notas.append(val)

                # Normaliza o tamanho da lista de notas para caber nas colunas
                qtd_esperada = len(atividades_encontradas)
                while len(valores_notas) < qtd_esperada:
                    valores_notas.append("-")
                valores_notas = valores_notas[:qtd_esperada]

                registro_linha = [num_ordem, matricula, nome] + valores_notas
                registros.append(registro_linha)

            df_unidade = pd.DataFrame(registros, columns=colunas_finais)
            resultado_unidades[unidade] = df_unidade
            logger.info(f"  ✓ {len(registros)} alunos extraídos na {unidade}ª Unidade.")

        return resultado_unidades

    def extrair_frequencia_turma(self, turma_info: dict) -> pd.DataFrame:
        """
        Navega para a tela de frequência da turma, mapeia o calendário e extrai
        o histórico de presenças e faltas por aluno.
        """
        turma_nome = turma_info["nome_turma"]
        disc = turma_info["componente_curricular"]
        logger.info(f"━━━ Extraindo Frequência da Turma: {turma_nome} ({disc}) ━━━")

        # Clica no botão/link de frequência
        btn_freq = turma_info.get("_btn_freq")
        if btn_freq:
            try:
                btn_freq.click()
                time.sleep(sc.ESPERA_CARREGAMENTO)
                self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception as e:
                logger.warning(f"Não foi possível clicar diretamente no botão de frequência: {e}")

        # Garante página de calendário
        if not sc.garantir_pagina_calendario(self.page):
            logger.warning("Não foi possível acessar o calendário de frequência da turma.")
            return pd.DataFrame()

        # Mapeia os dias com links disponíveis no calendário
        dias_aulas: list[tuple[int, int, str]] = []  # (dia, mes, data_str)
        tabelas = self.page.query_selector_all("table")

        for tabela in tabelas:
            if not sc.e_tabela_calendario(tabela):
                continue

            txt_tabela = sc.normalizar_nome(tabela.inner_text() or "")
            mes_num = 1
            for m_idx, m_nome in enumerate(sc.MESES, 1):
                if sc.normalizar_nome(m_nome) in txt_tabela:
                    mes_num = m_idx
                    break

            links_dias = tabela.query_selector_all("a")
            for link in links_dias:
                try:
                    txt_d = link.inner_text().strip()
                    if txt_d.isdigit():
                        d_int = int(txt_d)
                        data_formatada = f"{d_int:02d}/{mes_num:02d}"
                        dias_aulas.append((d_int, mes_num, data_formatada))
                except Exception:
                    continue

        # Ordena cronologicamente os dias
        dias_aulas.sort(key=lambda x: (x[1], x[0]))
        logger.info(f"  ✓ {len(dias_aulas)} datas de aula identificadas no calendário.")

        # Dicionário de registros dos alunos: {nome_aluno: {data: status}}
        mapa_alunos_freq: dict[str, dict[str, str]] = {}
        todos_nomes = []

        # Extrai registros para as datas (limite configurável para evitar timeouts excessivos)
        datas_processadas = []
        for dia, mes, data_str in dias_aulas:
            logger.info(f"  Verificando data {data_str}...")
            if not sc.garantir_pagina_calendario(self.page):
                break

            if not sc.encontrar_dia_no_calendario(self.page, dia, mes):
                continue

            time.sleep(2)
            datas_processadas.append(data_str)

            # Extrai linhas de alunos
            linhas = self.page.query_selector_all("#tableAlunos tbody tr, table tbody tr")
            for linha in linhas:
                nome = sc.extrair_nome_da_linha(linha)
                if not nome or len(nome.split()) < 2:
                    continue

                if nome not in mapa_alunos_freq:
                    mapa_alunos_freq[nome] = {}
                    todos_nomes.append(nome)

                # Analisa os checkboxes da linha
                cbs = linha.query_selector_all("input[type='checkbox']")
                if cbs:
                    # No SIGEduc, checkbox marcado normalmente representa FALTA
                    faltou = any(cb.is_checked() for cb in cbs)
                    status = "F" if faltou else "P"
                else:
                    # Se não tem checkbox, lê texto de status
                    txt_linha = sc.normalizar_nome(linha.inner_text())
                    if "FALTA" in txt_linha:
                        status = "F"
                    elif "PRESENCA" in txt_linha or "PRESENTE" in txt_linha:
                        status = "P"
                    else:
                        status = "P"

                mapa_alunos_freq[nome][data_str] = status

        if not mapa_alunos_freq:
            logger.warning("Nenhum dado de frequência pôde ser extraído.")
            return pd.DataFrame()

        # Monta DataFrame consolidado
        linhas_matriz = []
        for idx, nome in enumerate(todos_nomes, 1):
            registros_aluno = mapa_alunos_freq.get(nome, {})
            linha_dados = [idx, nome]
            total_faltas = 0
            total_aulas = len(datas_processadas)

            for d in datas_processadas:
                st = registros_aluno.get(d, "-")
                if st == "F":
                    total_faltas += 1
                linha_dados.append(st)

            total_presencas = total_aulas - total_faltas
            pct_freq = round((total_presencas / total_aulas) * 100, 1) if total_aulas > 0 else 100.0

            linha_dados.append(total_faltas)
            linha_dados.append(f"{pct_freq}%")
            linhas_matriz.append(linha_dados)

        colunas_freq = ["Nº", "Nome do Estudante"] + datas_processadas + ["Total de Faltas", "% Frequência"]
        df_freq = pd.DataFrame(linhas_matriz, columns=colunas_freq)
        logger.info(f"✓ Frequência extraída com sucesso: {len(df_freq)} alunos.")
        return df_freq

    def exportar_para_excel(self, dados_coletados: list[dict[str, Any]], caminho_saida: str):
        """
        Consolida todas as turmas, notas e frequências em um arquivo .xlsx
        com formatação corporativa, congelamento de painéis e abas tratadas.
        """
        logger.info(f"Gerando relatório Excel formatado: {caminho_saida}")
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove a aba vazia padrão criada pelo openpyxl
        abas_existentes: set[str] = set()

        # -------------------------------------------------------------
        # ABA 1: Resumo das Turmas Mapeadas
        # -------------------------------------------------------------
        ws_resumo = wb.create_sheet(title="Resumo_Turmas")
        abas_existentes.add("Resumo_Turmas")

        # Cabeçalho do Resumo
        headers_resumo = ["Nº", "Ano", "Escola", "Oferta de Ensino", "Ano/Série", "Periodicidade", "Turma", "Componente Curricular", "Qtd Alunos"]
        ws_resumo.append(["RELATÓRIO ACADÊMICO CONSOLIDADO — SIGEDUC BAHIA"])
        ws_resumo.merge_cells("A1:I1")
        ws_resumo["A1"].font = Font(name="Segoe UI", size=13, bold=True, color="1F4E79")
        ws_resumo["A1"].alignment = Alignment(horizontal="left", vertical="center")
        ws_resumo.row_dimensions[1].height = 28

        ws_resumo.append(headers_resumo)
        ws_resumo.row_dimensions[2].height = 24

        for item in dados_coletados:
            t = item["turma_info"]
            ws_resumo.append([
                t.get("id"),
                t.get("ano"),
                t.get("escola"),
                t.get("oferta_ensino"),
                t.get("ano_serie"),
                t.get("periodicidade"),
                t.get("nome_turma"),
                t.get("componente_curricular"),
                t.get("qtd_alunos")
            ])

        self._estilizar_planilha(ws_resumo, linha_cabecalho=2, congelar_painel="B3")

        # -------------------------------------------------------------
        # ABAS ESPECÍFICAS: Notas por Unidade e Frequência
        # -------------------------------------------------------------
        for item in dados_coletados:
            t_info = item["turma_info"]
            turma_nome = t_info["nome_turma"]
            componente = t_info["componente_curricular"]

            # Abas de Notas
            unidades_dict = item.get("notas_unidades", {})
            for num_unidade, df_unidade in unidades_dict.items():
                if df_unidade.empty:
                    continue

                nome_aba = formatar_nome_aba(turma_nome, componente, f"U{num_unidade}", abas_existentes)
                ws = wb.create_sheet(title=nome_aba)

                # Linha 1: Título e Identificação da Turma
                ws.append([f"TURMA: {turma_nome} | DISCIPLINA: {componente} | {num_unidade}ª UNIDADE"])
                col_max = len(df_unidade.columns)
                ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(col_max, 5))
                ws["A1"].font = Font(name="Segoe UI", size=12, bold=True, color="1F4E79")
                ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
                ws.row_dimensions[1].height = 26

                # Linha 2: Cabeçalho das Colunas
                ws.append(list(df_unidade.columns))
                ws.row_dimensions[2].height = 22

                # Linhas com os dados dos estudantes
                for row_data in df_unidade.itertuples(index=False):
                    ws.append(list(row_data))

                self._estilizar_planilha(ws, linha_cabecalho=2, congelar_painel="D3")

            # Aba de Frequência
            df_freq = item.get("frequencia_df")
            if df_freq is not None and not df_freq.empty:
                nome_aba_freq = formatar_nome_aba(turma_nome, componente, "Freq", abas_existentes)
                ws_freq = wb.create_sheet(title=nome_aba_freq)

                ws_freq.append([f"HISTÓRICO DE FREQUÊNCIA — TURMA: {turma_nome} | DISCIPLINA: {componente}"])
                col_max_f = len(df_freq.columns)
                ws_freq.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(col_max_f, 5))
                ws_freq["A1"].font = Font(name="Segoe UI", size=12, bold=True, color="1F4E79")
                ws_freq["A1"].alignment = Alignment(horizontal="left", vertical="center")
                ws_freq.row_dimensions[1].height = 26

                ws_freq.append(list(df_freq.columns))
                ws_freq.row_dimensions[2].height = 22

                for row_data in df_freq.itertuples(index=False):
                    ws_freq.append(list(row_data))

                self._estilizar_planilha(ws_freq, linha_cabecalho=2, congelar_painel="C3")

        # Salva o arquivo final
        wb.save(caminho_saida)
        logger.info(f"✅ Planilha salva com sucesso em: {caminho_saida}")

    def _estilizar_planilha(self, ws, linha_cabecalho: int = 1, congelar_painel: str = "B2"):
        """Aplica formatação visual profissional ao cabeçalho, bordas e largura das colunas."""
        cor_cabecalho = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        fonte_cabecalho = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        
        cor_zebra = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
        borda_cinza = Border(
            left=Side(style='thin', color='E5E7EB'),
            right=Side(style='thin', color='E5E7EB'),
            top=Side(style='thin', color='E5E7EB'),
            bottom=Side(style='thin', color='E5E7EB')
        )

        # Formata cabeçalho
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=linha_cabecalho, column=col_idx)
            cell.fill = cor_cabecalho
            cell.font = fonte_cabecalho
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Formata dados com zebra striping e bordas
        for row_idx in range(linha_cabecalho + 1, ws.max_row + 1):
            eh_par = (row_idx % 2 == 0)
            for col_idx in range(1, ws.max_column + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = borda_cinza
                if eh_par:
                    cell.fill = cor_zebra

                # Alinhamento inteligente: texto de nomes à esquerda, números/status centralizados
                val = str(cell.value or "")
                if col_idx in [2, 3] and any(c.isalpha() for c in val) and len(val) > 3:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="center", vertical="center")

        # Congelamento de painel
        if congelar_painel:
            ws.freeze_panes = congelar_painel

        # Autoajuste de largura de colunas
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.row == 1 and ws.cell(row=1, column=1).coordinate in ws.merged_cells:
                    continue  # Pula títulos mesclados da primeira linha
                val = str(cell.value or "")
                if len(val) > max_len and len(val) < 80:
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 11)

    def executar_extracao(self, modo: str = "todos", caminho_saida: str = "relatorio_academico_sigeduc.xlsx") -> str:
        """
        Fluxo orquestrado de ponta a ponta:
        1. Lista todas as turmas
        2. Extrai Notas e/ou Frequências conforme o modo
        3. Gera a planilha Excel final
        """
        turmas = self.listar_turmas()
        if not turmas:
            logger.warning("Nenhuma turma foi encontrada para extração.")
            return ""

        dados_completos = []

        for idx, t in enumerate(turmas, 1):
            logger.info(f"\n=======================================================")
            logger.info(f"Processando Turma [{idx}/{len(turmas)}]: {t['nome_turma']} ({t['componente_curricular']})")
            logger.info(f"=======================================================")

            turma_resultado = {"turma_info": t, "notas_unidades": {}, "frequencia_df": None}

            # Extração de Notas
            if modo in ["notas", "todos"]:
                notas = self.extrair_notas_turma(t)
                turma_resultado["notas_unidades"] = notas

            # Extração de Frequência
            if modo in ["frequencia", "todos"]:
                self.navegar_diario_classe()
                # Atualiza referência dos botões se a página recarregou
                turmas_atualizadas = self.listar_turmas()
                if idx - 1 < len(turmas_atualizadas):
                    t_atualizada = turmas_atualizadas[idx - 1]
                    freq_df = self.extrair_frequencia_turma(t_atualizada)
                    turma_resultado["frequencia_df"] = freq_df

            dados_completos.append(turma_resultado)

            # Retorna para o diário antes da próxima turma
            self.navegar_diario_classe()

        self.exportar_para_excel(dados_completos, caminho_saida)
        return caminho_saida


# =====================================================================
# CLI Interativo
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="Extração de Dados Acadêmicos do SIGEduc Bahia para Excel")
    parser.add_argument("--headless", action="store_true", help="Executa o navegador em modo silencioso/background")
    parser.add_argument("--modo", choices=["notas", "frequencia", "todos"], default="todos", help="Modo de extração")
    parser.add_argument("--usuario", type=str, default="", help="Usuário do SIGEduc")
    parser.add_argument("--saida", type=str, default="relatorio_academico_sigeduc.xlsx", help="Caminho do arquivo Excel de saída")
    args = parser.parse_args()

    print("=" * 65)
    print("  SIGEDUC AUTO — MÓDULO DE EXTRAÇÃO & EXPORTAÇÃO EXCEL")
    print("=" * 65)

    usuario = args.usuario
    senha = ""

    # Se não forneceu usuário via CLI, pergunta interativamente
    if not usuario:
        usuario = input("Usuário do SIGEduc (deixe vazio se já estiver logado): ").strip()

    if usuario:
        senha = getpass.getpass("Senha do SIGEduc: ")

    print(f"\nModo de Coleta: {args.modo.upper()}")
    print(f"Arquivo de Saída: {args.saida}")
    print(f"Modo Headless: {'Sim (Background)' if args.headless else 'Não (Visível)'}\n")

    with SigeducScraper(headless=args.headless) as scraper:
        sucesso_login = scraper.login(usuario=usuario, senha=senha)
        if not sucesso_login:
            print("\n⚠️ Não foi possível confirmar a sessão automaticamente.")
            print("Por favor, faça login manualmente no Chrome aberto.")
            input("Pressione [ENTER] após estar no painel principal do SIGEduc...")

        arquivo_gerado = scraper.executar_extracao(modo=args.modo, caminho_saida=args.saida)
        if arquivo_gerado:
            print("\n" + "=" * 65)
            print(f"🎉 Processo concluído! Planilha gerada com sucesso:")
            print(f"📁 {os.path.abspath(arquivo_gerado)}")
            print("=" * 65)
        else:
            print("\n❌ Nenhuma planilha foi gerada.")


if __name__ == "__main__":
    main()
