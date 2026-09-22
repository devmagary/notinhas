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
def extrair_turno(texto: str) -> str:
    """Extrai identificador conciso do turno (Mat, Vesp, Not, Int) de strings usando regex de fronteira."""
    t_up = str(texto or "").upper()
    if re.search(r"\b(MATUTINO|MAT|MANHA)\b", t_up):
        return "Mat"
    elif re.search(r"\b(VESPERTINO|VESP|VES|TARDE)\b", t_up):
        return "Vesp"
    elif re.search(r"\b(NOTURNO|NOT|NOITE)\b", t_up):
        return "Not"
    elif re.search(r"\b(INTEGRAL|INT)\b", t_up):
        return "Int"
    return ""


def formatar_nome_aba(turma: str, componente: str, sufixo: str, abas_existentes: set[str] | None = None, turno: str = "") -> str:
    """
    Gera um nome de aba válido para o Excel respeitando rigorosamente:
    - Inclusão do nome da Turma e do Turno (ex: 3A_Mat_Hist_U1, 2B_Vesp_Mat_U2);
    - Limite máximo de 31 caracteres;
    - Remoção dos caracteres proibidos: [ ] : ? * / \\
    - Prevenção de colisões com abas já existentes (adicionando sufixo _1, _2).
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
        comp_abrev = partes[0][:5].capitalize() if partes else "Disc"

    # Extrai o turno (Mat, Vesp, Not, Int) do parâmetro fornecido ou da turma
    turno_tag = extrair_turno(turno) or extrair_turno(turma)

    # Limpa ordinais antes da normalização NFKD para não transformar 'º' na letra 'O'
    turma_sem_ord = re.sub(r"[º°ª]", "", str(turma or ""))
    turma_limpa = limpar_ascii(turma_sem_ord)
    
    # Remove palavras estruturais e menções a turnos
    turma_sem_palavras = re.sub(
        r"\b(ANO|SERIE|SERIES|TURMA|MATUTINO|VESPERTINO|NOTURNO|INTEGRAL|MAT|VESP|NOT|INT|MANHA|TARDE|NOITE)\b",
        "",
        turma_limpa
    ).strip()

    # Procura padrão '3A' ou '1EMI'
    match_turma = re.search(r"(\d+)\s*([A-Z]{1,4})\b", turma_sem_palavras)
    # Procura padrão 'INFO 2' -> 'Info2'
    match_sigla_num = re.search(r"([A-Z]{2,})\s*(\d+)", turma_sem_palavras)

    if match_turma:
        turma_abrev = f"{match_turma.group(1)}{match_turma.group(2)}"
    elif match_sigla_num:
        turma_abrev = f"{match_sigla_num.group(1)[:4].capitalize()}{match_sigla_num.group(2)}"
    else:
        digs = re.findall(r"\d+", turma_sem_palavras)
        letras = re.findall(r"[A-Z]", turma_sem_palavras)
        if digs and letras:
            turma_abrev = f"{digs[0]}{letras[0]}"
        elif digs:
            turma_abrev = f"T{digs[0]}"
        else:
            turma_abrev = re.sub(r"[^A-Za-z0-9]", "", turma_sem_palavras)[:8] or "Turma"

    # Constrói o nome com Turma + Turno + Disciplina + Sufixo (ex: 3A_Mat_Hist_U1)
    if turno_tag:
        base = f"{turma_abrev}_{turno_tag}_{comp_abrev}_{sufixo}"
    else:
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

    def esta_no_painel_docente(self) -> bool:
        """
        Verifica com precisão se a página atual é a tela principal de turmas do docente.
        Garante que não estejamos em subpáginas de notas, frequência ou avaliações.
        """
        try:
            url = (self.page.url or "").lower()
            # Se a URL contém marcadores óbvios de subpáginas, NÃO é o painel de turmas
            if any(p in url for p in ["form_", "nota", "avaliacao", "frequencia", "calendario"]):
                return False

            tabelas = self.page.query_selector_all("table")
            for t in tabelas:
                txt = sc.normalizar_nome(t.inner_text() or "")
                # Tabela de turmas no SIGEduc contém colunas estruturais características
                if "TURMA" in txt and ("COMPONENTE" in txt or "DISCIPLINA" in txt) and any(k in txt for k in ["OFERTA", "SERIE", "ESCOLA", "PERIODICIDADE", "ANO"]):
                    return True
        except Exception:
            pass
        return False

    def navegar_diario_classe(self) -> bool:
        """Navega para a tela principal de turmas / Diário de Classe Digital de forma segura para o JSF."""
        logger.info("Navegando para o Diário de Classe Digital (Painel do Professor)...")

        # 1. Se já está no painel docente real, conclui imediatamente
        if self.esta_no_painel_docente():
            logger.info("✓ Já está no painel principal do professor com turmas disponíveis.")
            return True

        # 2. Tenta clicar no botão "Voltar" da tela atual (comum em telas de notas)
        try:
            btn_voltar = self.page.query_selector(
                "input[value*='Voltar'], button:has-text('Voltar'), a:has-text('Voltar'), input[type='button'][value*='Voltar'], input[type='submit'][value*='Voltar']"
            )
            if btn_voltar and btn_voltar.is_visible():
                logger.info("Acionando botão 'Voltar'...")
                btn_voltar.click()
                time.sleep(sc.ESPERA_CARREGAMENTO)
                self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                if self.esta_no_painel_docente():
                    logger.info("✓ Retornou ao painel via botão 'Voltar'.")
                    return True
        except Exception as e:
            logger.debug(f"Tentativa de botão Voltar: {e}")

        # 3. Tenta o link 'Menu Professor' ou 'verPortalDocente.do' (rota nativa do SIGEduc)
        try:
            link_menu = self.page.query_selector(
                "a:has-text('Menu Professor'), a[href*='verPortalDocente.do'], a:has-text('Portal do Docente'), a:has-text('Docente')"
            )
            if link_menu and link_menu.is_visible():
                logger.info("Acionando link 'Menu Professor'...")
                link_menu.click()
                time.sleep(sc.ESPERA_CARREGAMENTO)
                self.page.wait_for_load_state("domcontentloaded", timeout=12000)
                if self.esta_no_painel_docente():
                    logger.info("✓ Retornou ao painel via 'Menu Professor'.")
                    return True
        except Exception as e:
            logger.debug(f"Tentativa de Menu Professor: {e}")

        # 4. Procura links com texto 'Diário de Classe' ou 'Turmas'
        try:
            links = self.page.query_selector_all("a")
            for link in links:
                try:
                    txt = sc.normalizar_nome(link.inner_text() or "")
                    if "DIARIO DE CLASSE" in txt or "PORTAL DO DOCENTE" in txt:
                        link.click()
                        time.sleep(sc.ESPERA_CARREGAMENTO)
                        self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                        if self.esta_no_painel_docente():
                            return True
                except Exception:
                    continue
        except Exception:
            pass

        # 5. Fallback direto: navega para URL_FREQUENCIA
        logger.info("Carregando URL do portal docente diretamente...")
        try:
            self.page.goto(sc.URL_FREQUENCIA, wait_until="domcontentloaded", timeout=sc.TIMEOUT_PAGINA)
            time.sleep(sc.ESPERA_CARREGAMENTO)
            try:
                self.page.wait_for_selector("table", timeout=10000)
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Erro ao navegar para URL do portal: {e}")

        sucesso = self.esta_no_painel_docente()
        if sucesso:
            logger.info("✓ Painel principal do docente carregado.")
        else:
            logger.warning("⚠️ Não foi possível confirmar visualmente o retorno ao painel de turmas.")
        return sucesso

    def listar_turmas(self) -> list[dict[str, Any]]:
        """
        Mapeia todas as turmas disponíveis com metadados:
        Nome da Turma, Ano, Escola, Oferta de Ensino, Ano/Série, Turno, Periodicidade,
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
                        
                        # Inspeciona também a tag <img> filha (padrão real do SIGEduc JSF)
                        img = acao.query_selector("img")
                        img_title = (img.get_attribute("title") or "").upper() if img else ""
                        img_alt = (img.get_attribute("alt") or "").upper() if img else ""
                        img_src = (img.get_attribute("src") or "").upper() if img else ""
                        
                        tudo = f"{title} {alt} {txt_acao} {onclick} {img_title} {img_alt} {img_src}"

                        if any(k in tudo for k in ["NOTAS_LANCAR", "RESULTADO", "NOTA", "AVALIA", "BOLETIM"]):
                            btn_notas = acao
                        elif any(k in tudo for k in ["FREQUENCIA_LANCAR", "FREQUENCIA", "CHAMADA", "PRESENCA", "CALENDARIO"]):
                            btn_freq = acao
                    except Exception:
                        continue

                # Extrai dados das colunas
                textos_tds = [td.inner_text().strip() for td in tds]
                
                ano = ""
                escola = ""
                oferta = ""
                turma_nome = ""
                serie = ""
                periodicidade = "ANUAL"
                componente = ""
                qtd_alunos = 0

                # Detecta turno na linha ou nos textos
                turno_linha = extrair_turno(linha.inner_text())

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
                    "turno": turno_linha or extrair_turno(turma_nome),
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
        if not btn_notas:
            logger.error(f"Botão de notas não encontrado para a turma {turma_nome}.")
            return {}

        try:
            btn_notas.click()
            time.sleep(sc.ESPERA_CARREGAMENTO)
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as e:
            logger.error(f"Não foi possível clicar no botão de notas da turma {turma_nome}: {e}")
            return {}

        # Verifica se realmente saiu do painel docente
        if self.esta_no_painel_docente():
            logger.error(f"❌ O clique no botão de notas não abriu a tela de notas da turma {turma_nome}.")
            return {}

        # Aguarda tabela de notas
        try:
            self.page.wait_for_selector("table", timeout=sc.TIMEOUT_TABELA)
        except PWTimeout:
            logger.error("Tabela de notas não foi encontrada na tela.")
            return {}

        resultado_unidades: dict[int, pd.DataFrame] = {}

        # Mapeamento dos seletores diretos de cada tabela de unidade no DOM do SIGEduc
        seletores_tabelas_unidade = {
            1: [
                "table[id='formulario:result']", 
                "table[id*=':result']:not([id*='resultj']):not([id*='resultadoFinal'])",
                "#formulario\\:result",
                "#formulario\\:tab1 table"
            ],
            2: [
                "table[id='formulario:resultj_id_1']", 
                "table[id*=':resultj_id_1']",
                "#formulario\\:resultj_id_1",
                "#formulario\\:tab1j_id_1 table"
            ],
            3: [
                "table[id='formulario:resultj_id_2']", 
                "table[id*=':resultj_id_2']",
                "#formulario\\:resultj_id_2",
                "#formulario\\:tab1j_id_2 table"
            ],
            4: [
                "table[id='formulario:resultadoFinal']", 
                "table[id*='resultadoFinal']",
                "#formulario\\:resultadoFinal",
                "#formulario\\:resF table"
            ]
        }

        for unidade in unidades:
            logger.info(f"  Acessando {unidade}ª Unidade...")
            
            # Tenta localizar diretamente a tabela da unidade no DOM
            tabela_notas = None
            for sel in seletores_tabelas_unidade.get(unidade, []):
                tabela_notas = self.page.query_selector(sel)
                if tabela_notas:
                    break

            # Se não encontrou pelo seletor direto, ativa a aba via RichFaces
            if not tabela_notas:
                sc.garantir_unidade_ativa(self.page, unidade)
                time.sleep(1)
                for tab in self.page.query_selector_all("table"):
                    txt = sc.normalizar_nome(tab.inner_text() or "")
                    if "ALUNO" in txt or "MATRICULA" in txt or "ESTUDANTE" in txt:
                        tabela_notas = tab
                        break

            if not tabela_notas:
                logger.warning(f"  Tabela de notas não localizada para a {unidade}ª Unidade.")
                continue

            # Mapeia os cabeçalhos das atividades avaliativas (removendo popups de tooltips)
            cabecalhos_cols = ["Nº", "Matrícula", "Nome do Estudante"]
            th_elementos = tabela_notas.query_selector_all("thead th, tr:first-child th, tr:first-child td")
            
            atividades_encontradas = []
            for th in th_elementos:
                try:
                    # Remove popups de aviso/tooltip antes de extrair o texto
                    txt_th = th.evaluate("el => { const c = el.cloneNode(true); c.querySelectorAll('.popUp, span[style*=\"absolute\"]').forEach(e => e.remove()); return c.innerText; }").strip()
                except Exception:
                    txt_th = th.inner_text().strip()

                txt_norm = sc.normalizar_nome(txt_th)
                if any(ign in txt_norm for ign in ["FOTO", "NUMERO", "MATRICULA", "ALUNO", "NOME", "ACOES", "SITUACAO"]):
                    continue
                if txt_th:
                    atividades_encontradas.append(txt_th.replace("\n", " "))

            if not atividades_encontradas:
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

                # 1. Inputs de avaliações regulares/FV
                inputs_av = linha.query_selector_all("input.avaliacao, input[id*=':av__']")
                # 2. Input de recuperação
                inputs_rec = linha.query_selector_all("input[id*=':nuREC__']")
                # 3. Input de total da unidade
                inputs_tot = linha.query_selector_all("input[id*=':nu__']")

                valores_notas = []
                if inputs_av or inputs_rec or inputs_tot:
                    for inp in inputs_av:
                        v = inp.get_attribute("value") or ""
                        valores_notas.append(v.strip() if v.strip() else "-")
                    for inp in inputs_rec:
                        v = inp.get_attribute("value") or ""
                        valores_notas.append(v.strip() if v.strip() else "-")
                    for inp in inputs_tot:
                        v = inp.get_attribute("value") or ""
                        valores_notas.append(v.strip() if v.strip() else "-")
                else:
                    # Fallback para inputs genéricos ou células
                    inputs_genericos = linha.query_selector_all("input[type='text'], input:not([type='hidden']):not([type='checkbox'])")
                    if inputs_genericos:
                        for inp in inputs_genericos:
                            v = inp.get_attribute("value") or ""
                            valores_notas.append(v.strip() if v.strip() else "-")
                    else:
                        for td in tds[2:]:
                            val = td.inner_text().strip()
                            if val and not any(k in val.upper() for k in ["EDITAR", "SALVAR"]):
                                valores_notas.append(val)

                # Normaliza tamanho da lista para o número de colunas encontradas
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
        if not btn_freq:
            logger.error(f"Botão de frequência não encontrado para a turma {turma_nome}.")
            return pd.DataFrame()

        try:
            btn_freq.click()
            time.sleep(sc.ESPERA_CARREGAMENTO)
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as e:
            logger.error(f"Não foi possível clicar diretamente no botão de frequência: {e}")
            return pd.DataFrame()

        # Verifica se saiu do painel docente
        if self.esta_no_painel_docente():
            logger.error(f"❌ O clique no botão de frequência não abriu a tela de frequência da turma {turma_nome}.")
            return pd.DataFrame()

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
        headers_resumo = ["Nº", "Ano", "Escola", "Oferta de Ensino", "Ano/Série", "Turno", "Periodicidade", "Turma", "Componente Curricular", "Qtd Alunos"]
        ws_resumo.append(["RELATÓRIO ACADÊMICO CONSOLIDADO — SIGEDUC BAHIA"])
        ws_resumo.merge_cells("A1:J1")
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
                t.get("turno") or "Regular",
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
            turno = t_info.get("turno") or extrair_turno(turma_nome)

            # Abas de Notas
            unidades_dict = item.get("notas_unidades", {})
            for num_unidade, df_unidade in unidades_dict.items():
                if df_unidade.empty:
                    continue

                nome_aba = formatar_nome_aba(turma_nome, componente, f"U{num_unidade}", abas_existentes, turno=turno)
                ws = wb.create_sheet(title=nome_aba)

                # Linha 1: Título e Identificação da Turma
                ws.append([f"TURMA: {turma_nome} | TURNO: {turno or 'Regular'} | DISCIPLINA: {componente} | {num_unidade}ª UNIDADE"])
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
                nome_aba_freq = formatar_nome_aba(turma_nome, componente, "Freq", abas_existentes, turno=turno)
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
        1. Garante presença no painel docente e lista turmas.
        2. Para cada turma, re-obtém referências frescas do DOM, extrai Notas e/ou Frequência.
        3. Retorna garantidamente ao painel docente antes de prosseguir para a próxima turma.
        4. Consolida e gera a planilha Excel formatada.
        """
        self.navegar_diario_classe()
        turmas_iniciais = self.listar_turmas()
        if not turmas_iniciais:
            logger.warning("Nenhuma turma foi encontrada para extração.")
            return ""

        total_turmas = len(turmas_iniciais)
        logger.info(f"Total de turmas identificadas para processamento: {total_turmas}")
        dados_completos = []

        for idx in range(total_turmas):
            # Garante que está no painel docente antes de processar cada turma
            self.navegar_diario_classe()

            # Obtém referências frescas da tabela para evitar ElementHandle detached/stale
            turmas_frescas = self.listar_turmas()
            if idx >= len(turmas_frescas):
                logger.warning(f"Turma no índice {idx + 1} não encontrada na re-listagem.")
                break

            t = turmas_frescas[idx]
            turma_nome = t["nome_turma"]
            componente = t["componente_curricular"]

            logger.info(f"\n=======================================================")
            logger.info(f"Processando Turma [{idx + 1}/{total_turmas}]: {turma_nome} ({componente})")
            logger.info(f"=======================================================")

            turma_resultado = {"turma_info": t, "notas_unidades": {}, "frequencia_df": None}

            # Extração de Notas
            if modo in ["notas", "todos"]:
                notas = self.extrair_notas_turma(t)
                turma_resultado["notas_unidades"] = notas
                # Retorna ao painel docente após extrair notas
                self.navegar_diario_classe()

            # Extração de Frequência
            if modo in ["frequencia", "todos"]:
                if not self.esta_no_painel_docente():
                    self.navegar_diario_classe()
                # Re-obtém referências frescas para a mesma turma após retornar ao painel
                turmas_frescas_freq = self.listar_turmas()
                if idx < len(turmas_frescas_freq):
                    t_freq = turmas_frescas_freq[idx]
                    freq_df = self.extrair_frequencia_turma(t_freq)
                    turma_resultado["frequencia_df"] = freq_df
                # Retorna ao painel docente após extrair frequência
                self.navegar_diario_classe()

            dados_completos.append(turma_resultado)

        self.exportar_para_excel(dados_completos, caminho_saida)
        return caminho_saida


# =====================================================================
# CLI Interativo
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="Extração de Dados Acadêmicos do SIGEduc Bahia para Excel")
    parser.add_argument("--headless", action="store_true", help="Executa o navegador em modo silencioso/background")
    parser.add_argument("--modo", choices=["notas", "frequencia", "todos"], default=None, help="Modo de extração: notas, frequencia ou todos")
    parser.add_argument("--usuario", type=str, default="", help="Usuário do SIGEduc")
    parser.add_argument("--saida", type=str, default="relatorio_academico_sigeduc.xlsx", help="Caminho do arquivo Excel de saída")
    args = parser.parse_args()

    print("=" * 65)
    print("  SIGEDUC AUTO — MÓDULO DE EXTRAÇÃO & EXPORTAÇÃO EXCEL")
    print("=" * 65)

    # Pergunta interativa para o modo de extração (se não foi passado via argumento)
    modo = args.modo
    if not modo:
        print("\nEscolha o que deseja extrair do SIGEduc:")
        print("  [1] Notas e Resultados por Unidade")
        print("  [2] Frequência e Presença (Histórico Diário)")
        print("  [3] Completo (Notas + Frequência)")
        while True:
            escolha = input("\nDigite a opção desejada [1, 2 ou 3] (padrão: 1): ").strip()
            if not escolha or escolha == "1":
                modo = "notas"
                break
            elif escolha == "2":
                modo = "frequencia"
                break
            elif escolha == "3":
                modo = "todos"
                break
            else:
                print("⚠️ Opção inválida. Digite 1, 2 ou 3.")

    usuario = args.usuario
    senha = ""

    # Se não forneceu usuário via CLI, pergunta interativamente
    if not usuario:
        usuario = input("\nUsuário do SIGEduc (deixe vazio se já estiver logado): ").strip()

    if usuario:
        senha = getpass.getpass("Senha do SIGEduc: ")

    print(f"\nModo de Coleta Selecionado: {modo.upper()}")
    print(f"Arquivo de Saída: {args.saida}")
    print(f"Modo Headless: {'Sim (Background)' if args.headless else 'Não (Visível)'}\n")

    with SigeducScraper(headless=args.headless) as scraper:
        sucesso_login = scraper.login(usuario=usuario, senha=senha)
        if not sucesso_login:
            print("\n⚠️ Não foi possível confirmar a sessão automaticamente.")
            print("Por favor, faça login manualmente no Chrome aberto.")
            input("Pressione [ENTER] após estar no painel principal do SIGEduc...")

        arquivo_gerado = scraper.executar_extracao(modo=modo, caminho_saida=args.saida)
        if arquivo_gerado:
            print("\n" + "=" * 65)
            print(f"🎉 Processo concluído! Planilha gerada com sucesso:")
            print(f"📁 {os.path.abspath(arquivo_gerado)}")
            print("=" * 65)
        else:
            print("\n❌ Nenhuma planilha foi gerada.")


if __name__ == "__main__":
    main()
