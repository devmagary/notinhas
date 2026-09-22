"""
Automação de Lançamento de Frequência e Notas — Sigeduc BA (CLI)
=================================================================
Script de linha de comando que utiliza o módulo sigeduc_core para
controlar o navegador via Playwright.  Todas as funções utilitárias,
constantes e o logger são importados do core.

Uso:
    python lancar_frequencia.py

O script vai:
1. Abrir o navegador (com sessão salva, para não precisar logar toda vez)
2. Pedir os dados: arquivo de alunos, datas/notas, e senha
3. Navegar, clicar, marcar presenças ou preencher notas e gravar automaticamente
"""

import os
import sys
import time
import getpass
import traceback

import sigeduc_core as sc


# =============================================
# Função principal (loop interativo CLI)
# =============================================
def main():
    sc.logger.info("=" * 60)
    sc.logger.info("  AUTOMAÇÃO DE FREQUÊNCIA E NOTAS — SIGEDUC BA")
    sc.logger.info("  (Controlado por Python — à prova de recarregamentos)")
    sc.logger.info("=" * 60)
    sc.logger.info("")

    sc.logger.info("Abrindo navegador...")
    sc.logger.info("(Se for a primeira vez, faça login manualmente.)")
    sc.logger.info("(Sua sessão ficará salva para as próximas execuções.)")
    sc.logger.info("")

    with sc.sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": str(sc.PERFIL_NAVEGADOR),
            "headless": False,
            "slow_mo": sc.SLOW_MO,
            "viewport": {"width": 1280, "height": 900},
        }
        try:
            browser = p.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
        except Exception:
            browser = p.chromium.launch_persistent_context(**launch_kwargs)


        page = browser.pages[0] if browser.pages else browser.new_page()
        sc.tratar_dialogo_confirmacao(page)

        sc.logger.info("Navegando para o Sigeduc...")
        page.goto(sc.URL_FREQUENCIA, wait_until="networkidle", timeout=sc.TIMEOUT_PAGINA)
        time.sleep(sc.ESPERA_CARREGAMENTO)

        # --- Verifica se caiu na tela de login ---
        conteudo = sc.obter_conteudo_seguro(page)
        if "login" in page.url.lower() or "autenticação" in conteudo.lower():
            sc.logger.info("")
            sc.logger.info("=" * 60)
            sc.logger.info("  ⚠️ AÇÃO REQUERIDA: FAÇA LOGIN NO PORTAL SIGEDUC")
            sc.logger.info("=" * 60)
            sc.logger.info("  1. Procure a janela do navegador Chrome que abriu (pode estar atrás).")
            sc.logger.info("  2. Digite seu usuário e senha no portal e faça login.")
            sc.logger.info("  3. Aguarde até que a página inicial/painel do professor carregue.")
            sc.logger.info("  4. Volte a este terminal e pressione [ENTER] abaixo.")
            sc.logger.info("=" * 60)
            sc.trazer_navegador_para_frente()
            input("Pressione ENTER após fazer login...")

        # --- Loop principal de tarefas ---
        while True:
            sc.logger.info("\n" + "=" * 60)
            sc.logger.info("  ESCOLHA A TAREFA")
            sc.logger.info("=" * 60)
            sc.logger.info(" [1] Lançar Frequências (Presença/Falta)")
            sc.logger.info(" [2] Lançar Notas (Simulado, Ativ 1, Ativ 2)")
            sc.logger.info("")

            while True:
                tarefa = input("Digite 1 ou 2: ").strip()
                if tarefa in ["1", "2"]:
                    break
                sc.logger.warning("Opção inválida.")

            # ========================================
            # [1] LANÇAR FREQUÊNCIAS
            # ========================================
            if tarefa == "1":
                if not sc.garantir_pagina_calendario(page):
                    sc.logger.info("")
                    sc.logger.info("=" * 60)
                    sc.logger.info("  ⚠️ AÇÃO REQUERIDA: VÁ PARA O CALENDÁRIO DA TURMA NO PORTAL")
                    sc.logger.info("=" * 60)
                    sc.logger.info("  1. No Chrome, acesse o menu de turmas e selecione a turma desejada.")
                    sc.logger.info("  2. Vá em 'Diário de Classe' -> 'Frequência'.")
                    sc.logger.info("  3. Certifique-se de que a tabela com o calendário de datas está visível.")
                    sc.logger.info("  4. Volte a este terminal e pressione [ENTER] abaixo.")
                    sc.logger.info("=" * 60)
                    sc.trazer_navegador_para_frente()
                    input("Pressione ENTER para continuar...")

                sc.logger.info("\n" + "-" * 50)
                sc.logger.info("  LANÇAMENTO DE FREQUÊNCIA")
                sc.logger.info("-" * 50)

                # --- Arquivo de alunos ---
                caminho_arquivo = input("Caminho do arquivo de alunos (CSV/TXT/XLSX): ").strip().strip('"')
                while not os.path.exists(caminho_arquivo):
                    sc.logger.error(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
                    caminho_arquivo = input("Caminho do arquivo de alunos (CSV/TXT/XLSX): ").strip().strip('"')

                nomes = sc.ler_nomes(caminho_arquivo)
                sc.logger.info(f"  ✓ {len(nomes)} nomes carregados.")

                # --- Datas ---
                texto_datas = input("Datas para lançar (DD/MM separado por vírgula): ").strip()
                datas = sc.parsear_datas(texto_datas)
                while not datas:
                    sc.logger.warning("Erro: Nenhuma data válida.")
                    texto_datas = input("Datas para lançar (DD/MM separado por vírgula): ").strip()
                    datas = sc.parsear_datas(texto_datas)
                sc.logger.info(f"  ✓ {len(datas)} datas informadas.")

                # --- Modo de operação ---
                sc.logger.info("\nEscolha o modo de operação:")
                sc.logger.info(" [1] MARCAR FALTA na lista e PRESENÇA no resto")
                sc.logger.info(" [2] DAR PRESENÇA na lista e MARCAR FALTA no resto")
                sc.logger.info(" [3] DAR PRESENÇA na lista e NÃO MEXER no resto")
                sc.logger.info(" [4] MARCAR FALTA apenas no resto e NÃO MEXER na lista")
                while True:
                    modo = input("Escolha a opção (1, 2, 3 ou 4): ").strip()
                    if modo in ["1", "2", "3", "4"]:
                        break

                # --- Senha ---
                senha = getpass.getpass("\nSenha do Sigeduc (para Gravar): ")

                # --- Garante calendário antes de iniciar ---
                if not sc.garantir_pagina_calendario(page):
                    sc.logger.info("")
                    sc.logger.info("=" * 60)
                    sc.logger.info("  ⚠️ AÇÃO REQUERIDA: RETORNE AO CALENDÁRIO DA TURMA NO PORTAL")
                    sc.logger.info("=" * 60)
                    sc.logger.info("  1. No Chrome, acesse o calendário mensal da turma novamente.")
                    sc.logger.info("  2. Volte a este terminal e pressione [ENTER] abaixo.")
                    sc.logger.info("=" * 60)
                    sc.trazer_navegador_para_frente()
                    input("Pressione ENTER após retornar ao calendário...")

                sc.logger.info("\n" + "=" * 60)
                sc.logger.info("  INICIANDO AUTOMAÇÃO DE FREQUÊNCIA")
                sc.logger.info("=" * 60)

                sucesso = 0
                falhas = 0

                for i, (dia, mes) in enumerate(datas):
                    sc.logger.info(f"\n━━━ Data {i+1}/{len(datas)}: {dia:02d}/{mes:02d} ━━━")

                    dia_encontrado = False
                    for tentativa in range(sc.MAX_TENTATIVAS_DATA):
                        if not sc.garantir_pagina_calendario(page):
                            sc.logger.info("")
                            sc.logger.info("=" * 60)
                            sc.logger.info("  ⚠️ AÇÃO REQUERIDA: CALENDÁRIO NÃO ENCONTRADO")
                            sc.logger.info("=" * 60)
                            sc.logger.info("  1. No Chrome, selecione a turma desejada.")
                            sc.logger.info("  2. Vá em 'Diário de Classe' -> 'Frequência'.")
                            sc.logger.info("  3. Certifique-se de que a tabela com o calendário de datas está visível.")
                            sc.logger.info("  4. Pressione ENTER aqui para tentar novamente.")
                            sc.logger.info("=" * 60)
                            sc.trazer_navegador_para_frente()
                            input("Pressione ENTER após abrir a tela do calendário...")
                            continue

                        if not sc.encontrar_dia_no_calendario(page, dia, mes):
                            sc.logger.info("")
                            sc.logger.info("=" * 60)
                            sc.logger.info(f"  ⚠️ AÇÃO REQUERIDA: DIA {dia:02d}/{mes:02d} NÃO ENCONTRADO NO CALENDÁRIO")
                            sc.logger.info("=" * 60)
                            sc.logger.info("  1. Verifique se o portal está no mês correto para a data.")
                            sc.logger.info("  2. Se necessário, altere o mês do calendário do portal manualmente.")
                            sc.logger.info("  3. Pressione ENTER aqui para tentar clicar no dia novamente.")
                            sc.logger.info("=" * 60)
                            sc.trazer_navegador_para_frente()
                            input("Pressione ENTER após ajustar o calendário...")
                            continue

                        dia_encontrado = True
                        break

                    if not dia_encontrado:
                        sc.logger.error(f"  ❌ Falha ao processar data {dia:02d}/{mes:02d} após {sc.MAX_TENTATIVAS_DATA} tentativas.")
                        falhas += 1
                        continue

                    time.sleep(sc.ESPERA_CARREGAMENTO)
                    qtd = sc.marcar_presencas(page, nomes, modo)
                    sc.logger.info(f"  ✓ {qtd} alunos processados.")

                    if not sc.preencher_senha_e_gravar(page, senha):
                        falhas += 1
                        continue

                    sc.aguardar_pos_gravacao(page)
                    conteudo_final = sc.obter_conteudo_seguro(page).lower()
                    if "sucesso" in conteudo_final or "cadastrad" in conteudo_final:
                        sc.logger.info(f"  ✅ Data {dia:02d}/{mes:02d} gravada com sucesso!")
                        sucesso += 1
                    else:
                        sc.logger.warning(f"  ⚠ Data {dia:02d}/{mes:02d} pode ter falhado. Verifique no site.")
                        sucesso += 1

                sc.logger.info(f"\n  RESULTADO DA RODADA: ✅ Sucesso: {sucesso}/{len(datas)} | ❌ Falhas: {falhas}/{len(datas)}")

            # ========================================
            # [2] LANÇAR NOTAS
            # ========================================
            elif tarefa == "2":
                sc.logger.info("\n" + "-" * 50)
                sc.logger.info("  LANÇAMENTO DE NOTAS")
                sc.logger.info("-" * 50)

                # --- Arquivo de notas ---
                caminho_arquivo = input("Caminho do arquivo XLSX de notas: ").strip().strip('"')
                while not os.path.exists(caminho_arquivo):
                    sc.logger.error(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
                    caminho_arquivo = input("Caminho do arquivo XLSX de notas: ").strip().strip('"')

                letras_str = input("Letras das colunas de nota do Excel (separadas por vírgula. Ex: B, C): ").strip()
                letras_colunas = [l.strip() for l in letras_str.split(",") if l.strip()]

                formato_opt = input("Formato decimal [1] Ponto (ex: 3.5, 3.0 - Padrão Sigeduc) | [2] Vírgula (3,5) | [3] Original [Padrão: 1]: ").strip()
                if formato_opt == "2":
                    formato_nota = "virgula"
                elif formato_opt == "3":
                    formato_nota = "original"
                else:
                    formato_nota = "ponto"

                unidade_opt = input("Qual a Unidade desejada? [1] 1ª Unidade | [2] 2ª Unidade | [3] 3ª Unidade | [4] 4ª Unidade [Padrão: 1]: ").strip()
                if unidade_opt in ["2", "2ª", "2a"]:
                    unidade_selecionada = "2ª Unidade"
                elif unidade_opt in ["3", "3ª", "3a"]:
                    unidade_selecionada = "3ª Unidade"
                elif unidade_opt in ["4", "4ª", "4a"]:
                    unidade_selecionada = "4ª Unidade"
                else:
                    unidade_selecionada = "1ª Unidade"

                try:
                    dados_notas = sc.ler_notas_xlsx(caminho_arquivo, letras_colunas, formato=formato_nota)
                    sc.logger.info(f"  ✓ Notas de {len(dados_notas)} alunos carregadas das colunas {', '.join(letras_colunas)} do Excel [Formato: {formato_nota}].")
                except Exception as e:
                    sc.logger.error(f"Erro ao ler arquivo XLSX: {e}")
                    continue

                # --- Senha ---
                senha = getpass.getpass("\nSenha do Sigeduc (para Gravar): ")

                # --- Instruções para o usuário navegar até a tela de notas ---
                sc.logger.info("")
                sc.logger.info("=" * 60)
                sc.logger.info("  ⚠️ AÇÃO REQUERIDA: VÁ PARA A TELA DE NOTAS DA TURMA NO PORTAL")
                sc.logger.info("=" * 60)
                sc.logger.info("  1. No Chrome, selecione a turma desejada.")
                sc.logger.info("  2. Vá em 'Diário de Classe' -> 'Notas' e acesse a tela de lançamento.")
                sc.logger.info(f"  3. Unidade selecionada: {unidade_selecionada} (o robô verificará e ativará a aba correta).")
                sc.logger.info("  4. Certifique-se de que a tabela com as notas e os campos em branco está aberta.")
                sc.logger.info("  5. Volte a este terminal e pressione [ENTER] abaixo.")
                sc.logger.info("=" * 60)
                sc.trazer_navegador_para_frente()
                input("Pressione ENTER no terminal quando estiver pronto para preencher...")

                sc.logger.info(f"Preenchendo notas na {unidade_selecionada}...")
                qtd = sc.lancar_notas(page, dados_notas, unidade=unidade_selecionada)
                sc.logger.info(f"  ✓ {qtd} alunos preenchidos com as notas.")

                if sc.preencher_senha_e_gravar(page, senha):
                    sc.aguardar_pos_gravacao(page)

                    # Pergunta se deseja lançar Falta Vinculada (FV)
                    resp_fv = input(f"\nDeseja atribuir Falta Vinculada (FV) automaticamente na {unidade_selecionada}? (S/N) [S]: ").strip().lower()
                    if resp_fv in ["", "s", "sim", "y"]:
                        sc.processar_pergunta_notas_em_branco(page, deve_preencher_fv=True)
                        qtd_fv = sc.preencher_faltas_vinculadas(page, dados_notas, senha=senha, unidade=unidade_selecionada)
                        if qtd_fv > 0:
                            sc.logger.info(f"  ✓ {qtd_fv} Faltas Vinculadas atribuídas e confirmadas com senha na {unidade_selecionada}!")
                    else:
                        sc.processar_pergunta_notas_em_branco(page, deve_preencher_fv=False)

                    conteudo_final = sc.obter_conteudo_seguro(page).lower()
                    if any(p in conteudo_final for p in ["sucesso", "cadastrad", "gravad", "alterad", "atualizad"]):
                        sc.logger.info("  ✅ Notas gravadas com sucesso!")
                    else:
                        sc.logger.info("  ✅ Gravação submetida. Verifique no site.")
                else:
                    sc.logger.error("  ❌ Falha ao tentar gravar as notas.")

            # --- Continuar ou encerrar ---
            opcao_continuar = input("\nDeseja realizar outro lançamento (Frequência ou Notas)? (S/N): ").strip().lower()
            if opcao_continuar != "s":
                break

        sc.logger.info("\nFechando navegador...")
        browser.close()
        sc.logger.info("Automação finalizada. Até logo!")


# =============================================
# Ponto de entrada
# =============================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        erro_msg = traceback.format_exc()
        sc.logger.error("\n" + "=" * 60)
        sc.logger.error("OCORREU UM ERRO INESPERADO!")
        sc.logger.error("=" * 60)
        sc.logger.error(erro_msg)
        sc.logger.error("=" * 60)

        # Salva o erro em um arquivo de log para facilitar a identificação
        try:
            with open("erro_log.txt", "w", encoding="utf-8") as f:
                f.write("=== ERRO NO SIGEDUC AUTO ===\n")
                f.write(erro_msg)
            sc.logger.info("O erro acima foi salvo no arquivo 'erro_log.txt'.")
        except Exception:
            pass

        input("\nPressione ENTER para fechar a tela...")
