import sys
import os
import time
import threading
from tkinter import filedialog, messagebox

# Correção para o PyInstaller: obriga o Playwright a usar a pasta padrão do Windows 
# em vez da pasta temporária do executável onde os navegadores não estão embutidos.
if getattr(sys, 'frozen', False):
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(local_app_data, "ms-playwright")

# Auto-instalação do customtkinter e tkcalendar
try:
    import customtkinter as ctk
    from tkcalendar import Calendar
except ImportError:
    print("Pacotes visuais não encontrados. Instalando automaticamente...")
    os.system(f"{sys.executable} -m pip install customtkinter tkcalendar")
    import customtkinter as ctk
    from tkcalendar import Calendar

# Importa todas as funções lógicas do script original que criamos antes!
# Assim não precisamos reescrever a lógica do Playwright.
import sigeduc_core as sf

# Configuração visual do tema
ctk.set_appearance_mode("System")  # Segue o tema do Windows (Claro/Escuro)
ctk.set_default_color_theme("blue")

class RedirectText(object):
    """Redireciona os prints do terminal para uma caixa de texto do Tkinter."""
    def __init__(self, text_ctrl):
        self.output = text_ctrl

    def write(self, string):
        # Usamos .after() para ser thread-safe (a thread do navegador pode imprimir coisas)
        self.output.after(0, self._write, string)

    def _write(self, string):
        self.output.configure(state="normal")
        self.output.insert(ctk.END, string)
        self.output.see(ctk.END) # Rola automaticamente para o final
        self.output.configure(state="disabled")

    def flush(self):
        pass


class InstrucoesDialog(ctk.CTkToplevel):
    def __init__(self, parent, titulo, passos, tipo, event):
        super().__init__(parent)
        self.event = event
        self.title(titulo)
        self.geometry("520x420")
        self.resizable(False, False)
        
        # Mantém a janela sobre a janela principal e bloqueia o foco
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        
        # Centraliza o diálogo em relação à janela principal
        self.update_idletasks()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        
        width = 520
        height = 420
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Configuração do layout de grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        
        # Seleciona a cor do cabeçalho de acordo com o tipo
        header_colors = {
            "login": "#D97706",      # Laranja escuro / Âmbar
            "frequencia": "#2563EB", # Azul Royal
            "notas": "#7C3AED",      # Roxo
            "gravacao": "#059669"    # Esmeralda
        }
        color = header_colors.get(tipo, "#4B5563")
        
        # Frame do Cabeçalho
        self.header_frame = ctk.CTkFrame(self, fg_color=color, height=65, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_rowconfigure(0, weight=1)
        
        self.lbl_titulo = ctk.CTkLabel(
            self.header_frame, 
            text=titulo, 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), 
            text_color="white",
            anchor="w"
        )
        self.lbl_titulo.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Frame de Conteúdo
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, padx=25, pady=20, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self.lbl_intro = ctk.CTkLabel(
            self.content_frame,
            text="Siga as etapas abaixo no navegador Chrome que foi aberto:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
            justify="left"
        )
        self.lbl_intro.pack(fill="x", pady=(0, 15))
        
        # Adiciona cada passo com um círculo numerado elegante
        for i, passo in enumerate(passos, 1):
            passo_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            passo_frame.pack(fill="x", pady=6)
            
            # Número em formato de distintivo redondo
            num_lbl = ctk.CTkLabel(
                passo_frame,
                text=f" {i} ",
                fg_color=color,
                text_color="white",
                corner_radius=12,
                width=24,
                height=24,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
            )
            num_lbl.pack(side="left", padx=(0, 12))
            
            # Texto da instrução
            text_lbl = ctk.CTkLabel(
                passo_frame,
                text=passo,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                justify="left",
                wraplength=420,
                anchor="w"
            )
            text_lbl.pack(side="left", fill="x", expand=True)
            
        # Mensagem de alerta / Importante
        self.lbl_aviso = ctk.CTkLabel(
            self.content_frame,
            text="⚠️ Importante: Não feche a janela do Chrome aberta pelo aplicativo.",
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"),
            text_color="#DC2626",
            anchor="w"
        )
        self.lbl_aviso.pack(fill="x", pady=(20, 0))
        
        # Determina o texto do botão de ação
        btn_texts = {
            "login": "PRONTO, JÁ FIZ LOGIN",
            "frequencia": "JÁ ESTOU NO CALENDÁRIO DA TURMA",
            "notas": "JÁ ESTOU NA PÁGINA DE NOTAS",
            "gravacao": "GRAVAÇÃO MANUAL CONCLUÍDA"
        }
        btn_text = btn_texts.get(tipo, "CONFIRMAR E CONTINUAR")
        
        # Botão de Ação
        self.btn_confirmar = ctk.CTkButton(
            self,
            text=btn_text,
            fg_color=color,
            hover_color=self._escurecer_cor(color),
            height=42,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.confirmar
        )
        self.btn_confirmar.grid(row=2, column=0, padx=25, pady=20, sticky="ew")
        
        # Intercepta se o usuário tentar fechar pelo X do sistema
        self.protocol("WM_DELETE_WINDOW", self.confirmar)
        
    def confirmar(self):
        self.event.set()
        self.grab_release()
        self.destroy()
        
    def _escurecer_cor(self, hex_color):
        hex_hovers = {
            "#D97706": "#B45309",
            "#2563EB": "#1D4ED8",
            "#7C3AED": "#6D28D9",
            "#059669": "#047857"
        }
        return hex_hovers.get(hex_color, "#374151")


class SigeducGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sigeduc Auto - Interface Gráfica")
        self.geometry("850x700")
        
        self._definir_icone()
        
        # Grid layout da janela principal
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Abas (Operação e Logs)
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.tab_op = self.tabview.add("Operação")
        self.tab_log = self.tabview.add("Logs do Sistema")
        
        self.setup_aba_operacao()
        self.setup_aba_logs()
        
        # Redireciona todos os prints (sys.stdout) para a nossa aba de logs!
        sys.stdout = RedirectText(self.log_text)
        print("=== BEM-VINDO AO SIGEDUC AUTO ===")
        print("Preencha os dados na aba 'Operação' e clique em Iniciar.")
        print("Tudo o que o robô fizer aparecerá aqui em tempo real.\n")
        
    def _definir_icone(self):
        """Define o ícone da janela e barra de tarefas de forma segura."""
        try:
            if getattr(sys, 'frozen', False):
                icone_path = os.path.join(sys._MEIPASS, "icon.ico")
            else:
                icone_path = os.path.join(os.path.dirname(__file__), "icon.ico")
                
            self.iconbitmap(icone_path)
            # Para Tkinter em algumas versões do Windows, isso também ajuda na barra de tarefas
            import ctypes
            myappid = 'com.sigeduc.auto.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            pass # Ignora silenciosamente caso o ícone não exista ou dê erro
        
    def setup_aba_operacao(self):
        # --- SEÇÃO 1: TAREFA ---
        self.label_tarefa = ctk.CTkLabel(self.tab_op, text="1. Escolha a Tarefa:", font=ctk.CTkFont(weight="bold"))
        self.label_tarefa.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.tarefa_var = ctk.StringVar(value="frequencia")
        self.radio_freq = ctk.CTkRadioButton(self.tab_op, text="Lançar Frequência", variable=self.tarefa_var, value="frequencia", command=self.update_ui)
        self.radio_freq.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        
        self.radio_nota = ctk.CTkRadioButton(self.tab_op, text="Lançar Notas (Simulado, Ativ 1, Ativ 2)", variable=self.tarefa_var, value="notas", command=self.update_ui)
        self.radio_nota.grid(row=1, column=1, padx=20, pady=5, sticky="w")
        
        # --- SEÇÃO 2: ARQUIVO ---
        self.label_arquivo = ctk.CTkLabel(self.tab_op, text="2. Selecione o Arquivo de Dados (CSV, TXT ou XLSX):", font=ctk.CTkFont(weight="bold"))
        self.label_arquivo.grid(row=2, column=0, columnspan=2, padx=10, pady=(15, 0), sticky="w")
        
        self.entry_arquivo = ctk.CTkEntry(self.tab_op, width=500, placeholder_text="Caminho do arquivo...")
        self.entry_arquivo.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        self.btn_arquivo = ctk.CTkButton(self.tab_op, text="Procurar...", command=self.procurar_arquivo, width=100)
        self.btn_arquivo.grid(row=3, column=2, padx=10, pady=5, sticky="w")
        
        # --- SEÇÃO 3.A: DATAS (Só aparece para Frequência) ---
        self.frame_datas = ctk.CTkFrame(self.tab_op, fg_color="transparent")
        self.frame_datas.grid(row=4, column=0, columnspan=3, sticky="w")
        
        self.label_datas = ctk.CTkLabel(self.frame_datas, text="3. Datas para Lançar Frequência (ex: 11/03, 18/03):", font=ctk.CTkFont(weight="bold"))
        self.label_datas.grid(row=0, column=0, padx=10, pady=(15, 0), sticky="w")
        self.entry_datas = ctk.CTkEntry(self.frame_datas, width=400, placeholder_text="Ex: 01/04, 05/04")
        self.entry_datas.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.btn_calendario = ctk.CTkButton(self.frame_datas, text="📅 Abrir Calendário", command=self.abrir_calendario, width=130)
        self.btn_calendario.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # --- SEÇÃO 3.B: COLUNAS (Só aparece para Notas) ---
        self.frame_colunas = ctk.CTkFrame(self.tab_op, fg_color="transparent")
        self.label_colunas = ctk.CTkLabel(self.frame_colunas, text="3. Digite as Letras das colunas de nota do Excel (separadas por vírgula):", font=ctk.CTkFont(weight="bold"))
        self.label_colunas.grid(row=0, column=0, padx=10, pady=(15, 0), sticky="w")
        
        self.label_colunas_dica = ctk.CTkLabel(self.frame_colunas, text="Dica: Olhe para o site do Sigeduc e veja a ordem das notas pedidas.\nDigite as letras do seu Excel na MESMA ORDEM. Ex: Se pede Simulado e Ativ 1, e no Excel estão na B e C, digite: B, C", text_color="gray", justify="left")
        self.label_colunas_dica.grid(row=1, column=0, padx=10, pady=0, sticky="w")
        
        self.entry_colunas = ctk.CTkEntry(self.frame_colunas, width=400, placeholder_text="Ex: B, C, D ou Z, F")
        self.entry_colunas.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        # Formato decimal das notas
        self.label_formato_nota = ctk.CTkLabel(self.frame_colunas, text="Formato Decimal das Notas:", font=ctk.CTkFont(weight="bold"))
        self.label_formato_nota.grid(row=3, column=0, padx=10, pady=(10, 2), sticky="w")

        self.formato_nota_var = ctk.StringVar(value="ponto")
        self.frame_formato_opcoes = ctk.CTkFrame(self.frame_colunas, fg_color="transparent")
        self.frame_formato_opcoes.grid(row=4, column=0, padx=10, pady=2, sticky="w")

        self.radio_ponto = ctk.CTkRadioButton(self.frame_formato_opcoes, text="Ponto: 7.5 ou 7.0 (Padrão Sigeduc)", variable=self.formato_nota_var, value="ponto")
        self.radio_ponto.grid(row=0, column=0, padx=(0, 15), pady=2, sticky="w")

        self.radio_virgula = ctk.CTkRadioButton(self.frame_formato_opcoes, text="Vírgula: 7,5 ou 7,0", variable=self.formato_nota_var, value="virgula")
        self.radio_virgula.grid(row=0, column=1, padx=(0, 15), pady=2, sticky="w")

        self.radio_original = ctk.CTkRadioButton(self.frame_formato_opcoes, text="Original da planilha", variable=self.formato_nota_var, value="original")
        self.radio_original.grid(row=0, column=2, padx=(0, 10), pady=2, sticky="w")

        # Opção de Falta Vinculada (FV)
        self.chk_fv_var = ctk.BooleanVar(value=True)
        self.chk_fv = ctk.CTkCheckBox(
            self.frame_colunas,
            text="Atribuir Falta Vinculada (FV) nas notas em branco automaticamente",
            variable=self.chk_fv_var,
            font=ctk.CTkFont(weight="bold")
        )
        self.chk_fv.grid(row=5, column=0, padx=10, pady=(10, 2), sticky="w")

        # Seleção da Unidade Avaliativa
        self.label_unidade = ctk.CTkLabel(self.frame_colunas, text="Unidade Avaliativa:", font=ctk.CTkFont(weight="bold"))
        self.label_unidade.grid(row=6, column=0, padx=10, pady=(10, 2), sticky="w")

        self.unidade_var = ctk.StringVar(value="1ª Unidade")
        self.seg_unidade = ctk.CTkSegmentedButton(
            self.frame_colunas,
            values=["1ª Unidade", "2ª Unidade", "3ª Unidade", "4ª Unidade"],
            variable=self.unidade_var
        )
        self.seg_unidade.grid(row=7, column=0, padx=10, pady=2, sticky="w")

        
        # --- SEÇÃO 4: MODO DE OPERAÇÃO (Só aparece para Frequência) ---
        self.label_modo = ctk.CTkLabel(self.frame_datas, text="4. Modo de Operação (Quem está na lista?):", font=ctk.CTkFont(weight="bold"))
        self.label_modo.grid(row=2, column=0, padx=10, pady=(15, 0), sticky="w")
        
        self.modo_var = ctk.StringVar(value="1")
        self.radio_m1 = ctk.CTkRadioButton(self.frame_datas, text="[1] Faltosos: Dar Falta na Lista e Presença no resto", variable=self.modo_var, value="1")
        self.radio_m1.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.radio_m2 = ctk.CTkRadioButton(self.frame_datas, text="[2] Presentes: Dar Presença na Lista e Falta no resto", variable=self.modo_var, value="2")
        self.radio_m2.grid(row=4, column=0, padx=20, pady=5, sticky="w")
        self.radio_m3 = ctk.CTkRadioButton(self.frame_datas, text="[3] Dar Presença na Lista e Não Mexer no resto", variable=self.modo_var, value="3")
        self.radio_m3.grid(row=5, column=0, padx=20, pady=5, sticky="w")
        self.radio_m4 = ctk.CTkRadioButton(self.frame_datas, text="[4] Dar Falta no resto e Não Mexer na Lista", variable=self.modo_var, value="4")
        self.radio_m4.grid(row=6, column=0, padx=20, pady=5, sticky="w")
        
        # --- SEÇÃO 5: SENHA E GRAVAÇÃO ---
        self.frame_senha = ctk.CTkFrame(self.tab_op, fg_color="transparent")
        self.frame_senha.grid(row=5, column=0, columnspan=3, sticky="w", pady=(20,0))
        
        self.usar_senha_var = ctk.BooleanVar(value=True)
        self.chk_senha = ctk.CTkCheckBox(self.frame_senha, text="Preencher Senha e Gravar Automaticamente", variable=self.usar_senha_var, font=ctk.CTkFont(weight="bold"), command=self.update_ui)
        self.chk_senha.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.entry_senha = ctk.CTkEntry(self.frame_senha, show="*", width=200, placeholder_text="Senha do Sigeduc")
        self.entry_senha.grid(row=1, column=0, padx=35, pady=0, sticky="w")
        
        # --- SEÇÃO 6: BOTÃO INICIAR ---
        self.btn_iniciar = ctk.CTkButton(self.tab_op, text="▶ INICIAR AUTOMAÇÃO", command=self.iniciar_thread, fg_color="#2FA572", hover_color="#106A43", font=ctk.CTkFont(weight="bold", size=15), height=50, width=300)
        self.btn_iniciar.grid(row=6, column=0, columnspan=3, pady=(30, 10))
        
    def setup_aba_logs(self):
        self.log_text = ctk.CTkTextbox(self.tab_log, state="disabled", font=ctk.CTkFont(family="Consolas", size=13))
        self.log_text.pack(padx=10, pady=10, fill="both", expand=True)
        
    def update_ui(self):
        """Atualiza a tela de acordo com os radio buttons e checkboxes selecionados."""
        tarefa = self.tarefa_var.get()
        if tarefa == "notas":
            self.frame_datas.grid_remove() # Oculta opções de frequência
            self.frame_colunas.grid(row=4, column=0, columnspan=3, sticky="w") # Mostra colunas
        else:
            self.frame_colunas.grid_remove()
            self.frame_datas.grid()        # Mostra opções de frequência
            
        if self.usar_senha_var.get():
            self.entry_senha.configure(state="normal")
        else:
            self.entry_senha.configure(state="disabled")
            
    def procurar_arquivo(self):
        tarefa = self.tarefa_var.get()
        if tarefa == "frequencia":
            filetypes = (("Arquivos de Texto/CSV", "*.txt *.csv"), ("Todos os Arquivos", "*.*"))
        else:
            filetypes = (("Planilhas Excel", "*.xlsx"), ("Todos os Arquivos", "*.*"))
            
        filename = filedialog.askopenfilename(title="Selecione o arquivo com os alunos", filetypes=filetypes)
        if filename:
            self.entry_arquivo.delete(0, "end")
            self.entry_arquivo.insert(0, filename)
            
    def abrir_calendario(self):
        """Abre uma janela pop-up com um calendário para múltipla seleção."""
        top = ctk.CTkToplevel(self)
        top.title("Escolher Datas")
        top.geometry("380x480")
        top.transient(self) # Mantém sobre a janela principal
        top.grab_set()      # Bloqueia a principal até fechar essa
        
        lbl = ctk.CTkLabel(top, text="Selecione as datas clicando nelas:", font=ctk.CTkFont(weight="bold"))
        lbl.pack(pady=10)
        
        cal = Calendar(top, selectmode='day', date_pattern='dd/MM/yyyy')
        cal.pack(pady=10, padx=20, fill="both", expand=True)
        
        lbl_lista = ctk.CTkLabel(top, text="Datas Selecionadas:")
        lbl_lista.pack(pady=(10, 0))
        
        textbox = ctk.CTkTextbox(top, height=60, width=300)
        textbox.pack(pady=5)
        
        def dia_clicado(event):
            # selection_get() retorna um objeto datetime.date
            data_obj = cal.selection_get()
            if data_obj:
                data_str = data_obj.strftime("%d/%m")
                atual = textbox.get("1.0", "end").strip()
                # Adiciona apenas se não estiver na caixa ainda para evitar repetidos acidentais
                if data_str not in atual.split(", "):
                    if atual:
                        textbox.insert("end", ", " + data_str)
                    else:
                        textbox.insert("end", data_str)
                    
        cal.bind("<<CalendarSelected>>", dia_clicado)
        
        def confirmar():
            datas_escolhidas = textbox.get("1.0", "end").strip()
            if datas_escolhidas:
                atual_main = self.entry_datas.get().strip()
                if atual_main:
                    self.entry_datas.delete(0, "end")
                    self.entry_datas.insert(0, atual_main + ", " + datas_escolhidas)
                else:
                    self.entry_datas.insert(0, datas_escolhidas)
            top.destroy()
            
        btn_ok = ctk.CTkButton(top, text="Adicionar Datas", command=confirmar, fg_color="#2FA572", hover_color="#106A43")
        btn_ok.pack(pady=15)
            
    def iniciar_thread(self):
        """Dispara a automação em uma thread separada para não travar a janela visual."""
        # Desabilita o botão para evitar múltiplos cliques
        self.btn_iniciar.configure(state="disabled", text="EXECUTANDO...")
        
        # Opcional: Limpa o log a cada nova execução
        # self.log_text.configure(state="normal")
        # self.log_text.delete("1.0", "end")
        # self.log_text.configure(state="disabled")
        
        # Pula automaticamente para a aba de Logs para o usuário acompanhar
        self.tabview.set("Logs do Sistema")
        
        # Cria a thread e inicia
        t = threading.Thread(target=self.rodar_automacao)
        t.daemon = True # Se fechar o app, a thread morre junto
        t.start()
        
    def rodar_automacao(self):
        """Função principal que roda em background controlando o Sigeduc."""
        try:
            self._garantir_navegador()
            self._executar_logica_sigeduc()
        except Exception as e:
            import traceback
            print("\n" + "="*60)
            print("❌ OCORREU UM ERRO INESPERADO!")
            print(traceback.format_exc())
            print("="*60)
        finally:
            # Reativa o botão quando terminar (com sucesso ou erro)
            self.btn_iniciar.configure(state="normal", text="▶ INICIAR AUTOMAÇÃO")
            
    def _garantir_navegador(self):
        print("\nVerificando dependências do navegador (pode demorar na primeira vez)...")
        try:
            import subprocess
            from playwright._impl._driver import compute_driver_executable, get_driver_env
            cmd = list(compute_driver_executable()) + ["install", "chromium"]
            subprocess.run(
                cmd, 
                env=get_driver_env(), 
                check=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            print("Dependências verificadas.")
        except Exception as e:
            print(f"⚠️ Aviso ao verificar navegadores: {e}")

    def mostrar_instrucoes_sync(self, titulo, passos, tipo) -> None:
        """Exibe uma janela de instruções de forma síncrona e segura para threads."""
        event = threading.Event()
        self.after(0, self._criar_dialogo_instrucoes, titulo, passos, tipo, event)
        event.wait()

    def _criar_dialogo_instrucoes(self, titulo, passos, tipo, event):
        sf.trazer_navegador_para_frente()
        dialogo = InstrucoesDialog(self, titulo, passos, tipo, event)

    def _executar_logica_sigeduc(self):
        # 1. Captura todos os dados digitados na Interface
        tarefa = self.tarefa_var.get()
        caminho_arquivo = self.entry_arquivo.get().strip().strip('"')
        usar_senha = self.usar_senha_var.get()
        senha = self.entry_senha.get()
        modo = self.modo_var.get()
        
        print("\n" + "="*60)
        print("  INICIANDO PROCESSO")
        print("="*60)
        
        # Validação de arquivo
        if not os.path.exists(caminho_arquivo):
            print(f"❌ Erro: Arquivo '{caminho_arquivo}' não encontrado.")
            return
            
        nomes = []
        dados_notas = {}
        datas = []
        
        # Carregamento do Arquivo
        if tarefa == "frequencia":
            nomes = sf.ler_nomes(caminho_arquivo)
            if not nomes:
                print("❌ Erro: Nenhum nome encontrado no arquivo.")
                return
            print(f"✓ {len(nomes)} alunos carregados da lista.")
            
            texto_datas = self.entry_datas.get().strip()
            datas = sf.parsear_datas(texto_datas)
            if not datas:
                print("❌ Erro: Nenhuma data válida fornecida. Use o formato DD/MM.")
                return
            print(f"✓ {len(datas)} datas para lançar.")
        else:
            letras_str = self.entry_colunas.get().strip()
            if not letras_str:
                print("❌ Erro: Informe as letras das colunas (ex: B, C, D).")
                return
            letras_colunas = [l.strip() for l in letras_str.split(",") if l.strip()]
            
            formato_nota = self.formato_nota_var.get()
            unidade_selecionada = self.unidade_var.get() if hasattr(self, "unidade_var") else "1ª Unidade"
            try:
                dados_notas = sf.ler_notas_xlsx(caminho_arquivo, letras_colunas, formato=formato_nota)
                if not dados_notas:
                    print("❌ Erro: Nenhuma nota válida extraída do Excel.")
                    return
                print(f"✓ Notas de {len(dados_notas)} alunos extraídas das {len(letras_colunas)} colunas ({', '.join(letras_colunas)}) [Formato: {formato_nota}] | Unidade: {unidade_selecionada}.")
            except Exception as e:
                print(f"❌ Erro ao ler arquivo XLSX: {e}")
                return
                
        # Validação de senha
        if usar_senha and not senha:
            print("❌ Erro: Você marcou para gravar automaticamente, mas deixou a senha vazia.")
            return
            
        # ==========================================================
        # PLAYWRIGHT - CONTROLE DO NAVEGADOR
        # ==========================================================
        print("\nIniciando navegador Chrome...")
        with sf.sync_playwright() as p:
            launch_kwargs = {
                "user_data_dir": str(sf.PERFIL_NAVEGADOR),
                "headless": False,
                "slow_mo": 200,
                "viewport": {"width": 1280, "height": 900},
            }
            try:
                browser = p.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
            except Exception:
                browser = p.chromium.launch_persistent_context(**launch_kwargs)


            page = browser.pages[0] if browser.pages else browser.new_page()
            sf.tratar_dialogo_confirmacao(page)
            
            print("Navegando para o portal do Sigeduc...")
            page.goto(sf.URL_FREQUENCIA, wait_until="networkidle", timeout=60000)
            time.sleep(2)
            
            conteudo = sf.obter_conteudo_seguro(page)
            if "login" in page.url.lower() or "autenticação" in conteudo.lower():
                print("\n⚠️ FAÇA LOGIN NO NAVEGADOR!")
                print("Por favor, faça login no Chrome que acabou de abrir.")
                self.mostrar_instrucoes_sync(
                    "Login no Sigeduc Necessário",
                    [
                        "Localize a janela do navegador Chrome que acabou de abrir (pode estar atrás).",
                        "Digite seu usuário/senha e faça login no portal.",
                        "Aguarde o carregamento da página inicial/painel do professor.",
                        "Volte a esta janela e clique no botão abaixo para prosseguir."
                    ],
                    "login"
                )
                
            # --- FLUXO DE FREQUÊNCIA ---
            if tarefa == "frequencia":
                if not sf.garantir_pagina_calendario(page):
                    print("⚠️ Não foi possível encontrar o calendário automaticamente.")
                    self.mostrar_instrucoes_sync(
                        "Ir para o Calendário da Turma",
                        [
                            "No Chrome, acesse o menu de turmas e selecione a turma desejada.",
                            "Vá em 'Diário de Classe' -> 'Frequência'.",
                            "Certifique-se de que a tabela com o calendário de datas está visível na tela.",
                            "Volte aqui e clique no botão abaixo para que o robô possa prosseguir."
                        ],
                        "frequencia"
                    )
                    
                sucesso = 0
                falhas = 0
                for i, (dia, mes) in enumerate(datas):
                    print(f"\n━━━ Processando Data {i+1}/{len(datas)}: {dia:02d}/{mes:02d} ━━━")
                    
                    dia_encontrado = False
                    for tentativa in range(3):
                        if not sf.garantir_pagina_calendario(page):
                            print("⚠️ Calendário de frequência não encontrado no navegador.")
                            self.mostrar_instrucoes_sync(
                                "Calendário não Encontrado",
                                [
                                    "O robô não encontrou a página de frequência da turma.",
                                    "No Chrome, acesse sua turma e vá em 'Diário de Classe' -> 'Frequência'.",
                                    "Certifique-se de que a tabela com o calendário de datas está visível.",
                                    "Com o calendário na tela, clique no botão abaixo para tentar novamente."
                                ],
                                "frequencia"
                            )
                            continue
                            
                        if not sf.encontrar_dia_no_calendario(page, dia, mes):
                            print(f"⚠️ Dia {dia:02d}/{mes:02d} não encontrado ou não clicável no calendário.")
                            self.mostrar_instrucoes_sync(
                                "Dia não Encontrado no Calendário",
                                [
                                    f"O robô não conseguiu clicar no dia {dia:02d}/{mes:02d} no calendário.",
                                    "Verifique se você está no mês correto no calendário do portal.",
                                    "Se necessário, altere o mês do calendário do portal manualmente.",
                                    "Clique no botão abaixo para que o robô tente clicar no dia novamente."
                                ],
                                "frequencia"
                            )
                            continue
                        
                        dia_encontrado = True
                        break
                        
                    if not dia_encontrado:
                        print(f"❌ Falha ao processar a data {dia:02d}/{mes:02d} após 3 tentativas.")
                        falhas += 1
                        continue
                    
                    time.sleep(3)
                    print("  Marcando/desmarcando checkboxes...")
                    qtd = sf.marcar_presencas(page, nomes, modo)
                    print(f"  ✓ {qtd} alunos verificados/processados.")
                    
                    if usar_senha:
                        print("  Tentando gravar automaticamente...")
                        if not sf.preencher_senha_e_gravar(page, senha):
                            falhas += 1; continue
                        sf.aguardar_pos_gravacao(page)
                        conteudo_final = sf.obter_conteudo_seguro(page).lower()
                        if "sucesso" in conteudo_final or "cadastrad" in conteudo_final:
                            print(f"  ✅ Data {dia:02d}/{mes:02d} gravada com sucesso!")
                            sucesso += 1
                        else:
                            print(f"  ⚠ A gravação da data {dia:02d}/{mes:02d} pode ter falhado. Verifique.")
                            sucesso += 1
                    else:
                        print("  ⏸️ PAUSADO: A opção de senha automática está desmarcada.")
                        self.mostrar_instrucoes_sync(
                            f"Gravação Manual - Dia {dia:02d}/{mes:02d}",
                            [
                                "As faltas/presenças foram preenchidas nos campos pelo robô.",
                                "Revise os dados diretamente na tabela de alunos no Chrome.",
                                "Digite sua senha no site e clique no botão 'Gravar/Salvar' do portal.",
                                "Aguarde a gravação salvar, volte aqui e clique abaixo para prosseguir."
                            ],
                            "gravacao"
                        )
                        sucesso += 1
                        
                print(f"\n✅ FIM DA TAREFA: {sucesso} Datas concluidas | {falhas} Falhas")
                messagebox.showinfo("Concluído", f"Automação de frequência concluída!\n\nSucesso: {sucesso}\nFalhas: {falhas}")
                
            # --- FLUXO DE NOTAS ---
            else:
                print("\n⚠️ NAVEGAÇÃO MANUAL NECESSÁRIA PARA NOTAS")
                self.mostrar_instrucoes_sync(
                    "Ir para a Página de Notas",
                    [
                        "No Chrome, acesse o menu de turmas e selecione a turma desejada.",
                        "Acesse 'Diário de Classe' -> 'Notas'.",
                        f"Unidade selecionada: {unidade_selecionada} (o robô verificará e ativará a aba correta).",
                        "Certifique-se de que a tabela com os campos de notas está visível na tela.",
                        "Volte aqui e clique no botão abaixo para preencher as notas."
                    ],
                    "notas"
                )
                
                print(f"  Verificando aba da {unidade_selecionada} e preenchendo notas na tela...")
                qtd = sf.lancar_notas(page, dados_notas, unidade=unidade_selecionada)
                print(f"  ✓ {qtd} alunos receberam notas do Excel.")
                
                if usar_senha:
                    print("  Tentando gravar automaticamente...")
                    if sf.preencher_senha_e_gravar(page, senha):
                        sf.aguardar_pos_gravacao(page)

                        # Processa pergunta sobre notas em branco e tela de Falta Vinculada (FV)
                        qtd_fv = 0
                        if self.chk_fv_var.get():
                            print("  Processando pergunta de notas em branco e tela de Falta Vinculada (FV)...")
                            sf.processar_pergunta_notas_em_branco(page, deve_preencher_fv=True)
                            qtd_fv = sf.preencher_faltas_vinculadas(page, dados_notas, senha=senha, unidade=unidade_selecionada)
                            if qtd_fv > 0:
                                print(f"  ✓ {qtd_fv} Faltas Vinculadas atribuídas e confirmadas com senha!")
                        else:
                            sf.processar_pergunta_notas_em_branco(page, deve_preencher_fv=False)

                        conteudo_final = sf.obter_conteudo_seguro(page).lower()
                        msg_sucesso = "Notas gravadas com sucesso!"
                        if qtd_fv > 0:
                            msg_sucesso += f"\n({qtd_fv} Faltas Vinculadas confirmadas na {unidade_selecionada})"

                        if any(p in conteudo_final for p in ["sucesso", "cadastrad", "gravad", "alterad", "atualizad"]):
                            print(f"  ✅ {msg_sucesso}")
                            messagebox.showinfo("Concluído", msg_sucesso)
                        else:
                            print(f"  ✅ Gravação submetida! Verifique a confirmação no SIGEduc.")
                            messagebox.showinfo("Concluído", f"Gravação enviada com sucesso!\n{msg_sucesso}\nVerifique a confirmação no portal.")
                    else:
                        print("  ❌ Falha ao tentar gravar as notas.")
                else:
                    print("  ⏸️ PAUSADO: A opção de senha automática está desmarcada.")
                    self.mostrar_instrucoes_sync(
                        "Gravação Manual de Notas",
                        [
                            "As notas foram preenchidas nos campos da tela pelo robô.",
                            "Revise se as notas de cada aluno estão corretas no Chrome.",
                            "Clique no botão 'Gravar' no final da página.",
                            "No popup 'Confirme sua senha' que abrir, digite sua senha e clique em 'Confirmar'.",
                            "Aguarde o portal salvar as notas, depois volte aqui e clique abaixo."
                        ],
                        "gravacao"
                    )

                    # Pergunta interativa sobre Falta Vinculada (FV)
                    perguntar_fv = messagebox.askyesno(
                        "Lançar Faltas Vinculadas (FV)?",
                        f"Deseja que o robô preencha automaticamente as Faltas Vinculadas (FV) da {unidade_selecionada} para as notas em branco?"
                    )
                    if perguntar_fv:
                        print(f"  Lançando Faltas Vinculadas (FV) automaticamente na {unidade_selecionada}...")
                        sf.processar_pergunta_notas_em_branco(page, deve_preencher_fv=True)
                        qtd_fv = sf.preencher_faltas_vinculadas(page, dados_notas, senha="", unidade=unidade_selecionada)
                        print(f"  ✓ {qtd_fv} Faltas Vinculadas marcadas.")
                        self.mostrar_instrucoes_sync(
                            "Confirmar Senha para Faltas Vinculadas",
                            [
                                f"{qtd_fv} Faltas Vinculadas foram marcadas nas caixas da tela pelo robô na {unidade_selecionada}.",
                                "Clique no botão 'Gravar' no final da página de FV (se ainda não clicado).",
                                "No popup 'Confirme sua senha' que abrir, digite sua senha e clique em 'Confirmar'.",
                                "Aguarde o portal confirmar o sucesso e clique abaixo."
                            ],
                            "gravacao"
                        )
                        messagebox.showinfo("Concluído", f"Automação de FV concluída!\n{qtd_fv} Faltas Vinculadas atribuídas.")
                    else:
                        print("  Opção de FV ignorada pelo usuário. Respondendo 'Não' no portal...")
                        sf.processar_pergunta_notas_em_branco(page, deve_preencher_fv=False)
                    
            print("\nFechando navegador...")
            # O navegador fecha sozinho ao sair do bloco 'with'

if __name__ == "__main__":
    app = SigeducGUI()
    app.mainloop()
