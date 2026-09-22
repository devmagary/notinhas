"""
Interface Gráfica Moderna — Sigeduc Auto
========================================
Aplicativo desktop em CustomTkinter para automação de lançamento de frequência,
notas avaliativas e falta vinculada (FV) no portal SIGEduc Bahia.
"""

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

# Importação de pacotes visuais
try:
    import customtkinter as ctk
    from tkcalendar import Calendar
except ImportError:
    print("Pacotes visuais não encontrados. Instalando dependências...")
    os.system(f"{sys.executable} -m pip install customtkinter tkcalendar")
    import customtkinter as ctk
    from tkcalendar import Calendar

# Módulo lógico e utilitários
import sigeduc_core as sf

# Configuração inicial do tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class RedirectText(object):
    """Redireciona os prints do terminal para uma caixa de texto do CustomTkinter."""
    def __init__(self, text_ctrl):
        self.output = text_ctrl

    def write(self, string):
        self.output.after(0, self._write, string)

    def _write(self, string):
        self.output.configure(state="normal")
        self.output.insert(ctk.END, string)
        self.output.see(ctk.END)
        self.output.configure(state="disabled")

    def flush(self):
        pass


class InstrucoesDialog(ctk.CTkToplevel):
    """Diálogo modal moderno de instrução ao professor durante a automação."""
    def __init__(self, parent, titulo, passos, tipo, event):
        super().__init__(parent)
        self.event = event
        self.title(titulo)
        self.geometry("540x440")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        
        self.update_idletasks()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        
        width = 540
        height = 440
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        
        header_colors = {
            "login": "#D97706",
            "frequencia": "#2563EB",
            "notas": "#7C3AED",
            "gravacao": "#059669"
        }
        color = header_colors.get(tipo, "#2563EB")
        
        # Cabeçalho
        self.header_frame = ctk.CTkFrame(self, fg_color=color, height=65, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.lbl_titulo = ctk.CTkLabel(
            self.header_frame, 
            text=titulo, 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), 
            text_color="white",
            anchor="w"
        )
        self.lbl_titulo.grid(row=0, column=0, padx=22, pady=18, sticky="w")
        
        # Conteúdo
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, padx=25, pady=20, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self.lbl_intro = ctk.CTkLabel(
            self.content_frame,
            text="Siga as etapas abaixo na janela do Google Chrome:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
            justify="left"
        )
        self.lbl_intro.pack(fill="x", pady=(0, 15))
        
        for i, passo in enumerate(passos, 1):
            passo_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            passo_frame.pack(fill="x", pady=5)
            
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
            
            text_lbl = ctk.CTkLabel(
                passo_frame,
                text=passo,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                justify="left",
                wraplength=440,
                anchor="w"
            )
            text_lbl.pack(side="left", fill="x", expand=True)
            
        self.lbl_aviso = ctk.CTkLabel(
            self.content_frame,
            text="⚠️ Importante: Mantenha a janela do navegador aberta até concluir a tarefa.",
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"),
            text_color="#EF4444",
            anchor="w"
        )
        self.lbl_aviso.pack(fill="x", pady=(18, 0))
        
        btn_texts = {
            "login": "PRONTO, JÁ FIZ LOGIN",
            "frequencia": "JÁ ESTOU NO CALENDÁRIO DA TURMA",
            "notas": "JÁ ESTOU NA PÁGINA DE NOTAS",
            "gravacao": "GRAVAÇÃO MANUAL CONCLUÍDA"
        }
        btn_text = btn_texts.get(tipo, "CONFIRMAR E CONTINUAR")
        
        self.btn_confirmar = ctk.CTkButton(
            self,
            text=btn_text,
            fg_color=color,
            hover_color=self._escurecer_cor(color),
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.confirmar
        )
        self.btn_confirmar.grid(row=2, column=0, padx=25, pady=20, sticky="ew")
        
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
        return hex_hovers.get(hex_color, "#1F2937")


class SigeducGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SIGEDUC Auto — Painel Docente")
        self.geometry("900x740")
        self.minsize(860, 680)
        
        self._definir_icone()
        
        # Grid Principal
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Tabview
        self.grid_rowconfigure(2, weight=0)  # Status Bar
        self.grid_columnconfigure(0, weight=1)
        
        self.setup_header()
        
        # Abas Principais
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="nsew")
        
        self.tab_op = self.tabview.add("⚡ Operação")
        self.tab_log = self.tabview.add("📋 Logs em Tempo Real")
        self.tab_ajuda = self.tabview.add("ℹ️ Ajuda & Dicas")
        
        self.setup_aba_operacao()
        self.setup_aba_logs()
        self.setup_aba_ajuda()
        self.setup_status_bar()
        
        # Redirecionamento de Logs
        sys.stdout = RedirectText(self.log_text)
        print("=== SIGEDUC AUTO INICIADO ===")
        print("Selecione a tarefa, configure os parâmetros e clique em 'Iniciar Automação'.")
        print("Todos os eventos da execução serão exibidos aqui em tempo real.\n")
        
    def _definir_icone(self):
        """Define o ícone da aplicação no Windows."""
        try:
            if getattr(sys, 'frozen', False):
                icone_path = os.path.join(sys._MEIPASS, "icon.ico")
            else:
                icone_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icone_path):
                self.iconbitmap(icone_path)
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('sigeduc.auto.app.2')
        except Exception:
            pass

    def setup_header(self):
        """Cabeçalho superior com título, badge e alternador de tema."""
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        # Título e Subtítulo
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")
        
        lbl_app = ctk.CTkLabel(
            title_box, 
            text="SIGEDUC AUTO", 
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        lbl_app.pack(side="left")

        lbl_badge = ctk.CTkLabel(
            title_box,
            text=" v2.0 ",
            fg_color=("#3B82F6", "#1D4ED8"),
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold")
        )
        lbl_badge.pack(side="left", padx=8)

        lbl_desc = ctk.CTkLabel(
            title_box, 
            text="• Automação de Frequência, Notas & Falta Vinculada", 
            text_color="gray",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        lbl_desc.pack(side="left", padx=5)

        # Alternador de Tema
        theme_box = ctk.CTkFrame(header, fg_color="transparent")
        theme_box.grid(row=0, column=1, sticky="e")

        self.theme_seg = ctk.CTkSegmentedButton(
            theme_box,
            values=["Escuro", "Claro"],
            command=self.alternar_tema,
            height=28
        )
        self.theme_seg.set("Escuro")
        self.theme_seg.pack(side="right")

    def alternar_tema(self, escolha):
        if escolha == "Claro":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")

    def setup_aba_operacao(self):
        """Monta os cards da aba de Operação."""
        self.tab_op.grid_columnconfigure(0, weight=1)

        # --- CARD 1: SELEÇÃO DA TAREFA ---
        card_tarefa = ctk.CTkFrame(self.tab_op, corner_radius=10)
        card_tarefa.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        card_tarefa.grid_columnconfigure(0, weight=1)

        lbl_card1 = ctk.CTkLabel(
            card_tarefa, 
            text="1. SELECIONE A TAREFA", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#2563EB", "#60A5FA")
        )
        lbl_card1.pack(anchor="w", padx=15, pady=(10, 5))

        self.tarefa_var = ctk.StringVar(value="frequencia")
        self.seg_tarefa = ctk.CTkSegmentedButton(
            card_tarefa,
            values=["📅 Lançamento de Frequência", "📊 Lançamento de Notas & Falta Vinculada"],
            command=self._on_tarefa_changed,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.seg_tarefa.set("📅 Lançamento de Frequência")
        self.seg_tarefa.pack(fill="x", padx=15, pady=(5, 12))

        # --- CARD 2: ARQUIVO DE ENTRADA ---
        self.card_arquivo = ctk.CTkFrame(self.tab_op, corner_radius=10)
        self.card_arquivo.grid(row=1, column=0, padx=10, pady=8, sticky="ew")
        self.card_arquivo.grid_columnconfigure(0, weight=1)
        self.card_arquivo.grid_columnconfigure(1, weight=0)

        lbl_card2 = ctk.CTkLabel(
            self.card_arquivo, 
            text="2. ARQUIVO DE DADOS (PLANILHA OU LISTA)", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#2563EB", "#60A5FA")
        )
        lbl_card2.grid(row=0, column=0, columnspan=2, padx=15, pady=(10, 4), sticky="w")

        file_row = ctk.CTkFrame(self.card_arquivo, fg_color="transparent")
        file_row.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 5), sticky="ew")
        file_row.grid_columnconfigure(0, weight=1)
        file_row.grid_columnconfigure(1, weight=0)

        self.entry_arquivo = ctk.CTkEntry(
            file_row, 
            placeholder_text="Clique em 'Procurar...' ou cole o caminho do arquivo (.xlsx, .csv, .txt)",
            height=36
        )
        self.entry_arquivo.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_arquivo = ctk.CTkButton(
            file_row, 
            text="📂 Procurar...", 
            command=self.procurar_arquivo, 
            width=120,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.btn_arquivo.grid(row=0, column=1, sticky="e")

        self.lbl_status_arquivo = ctk.CTkLabel(
            self.card_arquivo,
            text="Nenhum arquivo selecionado.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray"
        )
        self.lbl_status_arquivo.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")

        # --- CARD 3: CONFIGURAÇÃO DE FREQUÊNCIA ---
        self.card_freq = ctk.CTkFrame(self.tab_op, corner_radius=10)
        self.card_freq.grid(row=2, column=0, padx=10, pady=8, sticky="ew")
        self.card_freq.grid_columnconfigure(0, weight=1)

        lbl_card3_f = ctk.CTkLabel(
            self.card_freq, 
            text="3. CONFIGURAÇÕES DE FREQUÊNCIA", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#2563EB", "#60A5FA")
        )
        lbl_card3_f.pack(anchor="w", padx=15, pady=(10, 4))

        # Datas
        datas_row = ctk.CTkFrame(self.card_freq, fg_color="transparent")
        datas_row.pack(fill="x", padx=15, pady=4)
        datas_row.grid_columnconfigure(0, weight=1)

        self.entry_datas = ctk.CTkEntry(
            datas_row, 
            placeholder_text="Datas no formato DD/MM (ex: 11/03, 18/03 ou separadas por espaço)",
            height=36
        )
        self.entry_datas.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_calendario = ctk.CTkButton(
            datas_row, 
            text="📅 Calendário", 
            command=self.abrir_calendario, 
            width=120,
            height=36,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.btn_calendario.grid(row=0, column=1, padx=(0, 6), sticky="e")

        self.btn_limpar_datas = ctk.CTkButton(
            datas_row,
            text="🧹 Limpar",
            command=self.limpar_datas_entry,
            width=80,
            height=36,
            fg_color=("#9CA3AF", "#4B5563"),
            hover_color=("#6B7280", "#374151")
        )
        self.btn_limpar_datas.grid(row=0, column=2, sticky="e")

        lbl_dica_datas = ctk.CTkLabel(
            self.card_freq,
            text="As datas serão ordenadas cronologicamente de forma automática.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray"
        )
        lbl_dica_datas.pack(anchor="w", padx=15, pady=(0, 8))

        # Modos de Frequência
        lbl_modo = ctk.CTkLabel(
            self.card_freq, 
            text="Modo de Lançamento (Quem está na lista do arquivo?):", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        lbl_modo.pack(anchor="w", padx=15, pady=(4, 2))

        self.modo_var = ctk.StringVar(value="1")
        modos_box = ctk.CTkFrame(self.card_freq, fg_color="transparent")
        modos_box.pack(fill="x", padx=15, pady=(2, 10))

        m1 = ctk.CTkRadioButton(modos_box, text="[1] Faltosos na Lista: Marca Falta na lista e Presença nos demais (Padrão)", variable=self.modo_var, value="1", command=self._on_modo_frequencia_changed)
        m1.pack(anchor="w", pady=3)
        m2 = ctk.CTkRadioButton(modos_box, text="[2] Presentes na Lista: Marca Presença na lista e Falta nos demais", variable=self.modo_var, value="2", command=self._on_modo_frequencia_changed)
        m2.pack(anchor="w", pady=3)
        m3 = ctk.CTkRadioButton(modos_box, text="[3] Apenas Presença: Marca Presença na lista e não altera os outros", variable=self.modo_var, value="3", command=self._on_modo_frequencia_changed)
        m3.pack(anchor="w", pady=3)
        m4 = ctk.CTkRadioButton(modos_box, text="[4] Apenas Falta: Marca Falta nos outros e não altera a lista", variable=self.modo_var, value="4", command=self._on_modo_frequencia_changed)
        m4.pack(anchor="w", pady=3)
        m5 = ctk.CTkRadioButton(modos_box, text="[5] 100% Presentes: Todos recebem presença na turma (dispensa arquivo)", variable=self.modo_var, value="5", command=self._on_modo_frequencia_changed)
        m5.pack(anchor="w", pady=3)

        # --- CARD 4: CONFIGURAÇÃO DE NOTAS & FALTA VINCULADA (FV) ---
        self.card_notas = ctk.CTkFrame(self.tab_op, corner_radius=10)
        self.card_notas.grid_columnconfigure(0, weight=1)

        lbl_card3_n = ctk.CTkLabel(
            self.card_notas, 
            text="3. CONFIGURAÇÕES DE NOTAS & FALTA VINCULADA (FV)", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#7C3AED", "#A78BFA")
        )
        lbl_card3_n.pack(anchor="w", padx=15, pady=(10, 4))

        # Unidade
        lbl_unidade = ctk.CTkLabel(self.card_notas, text="Unidade Avaliativa:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_unidade.pack(anchor="w", padx=15, pady=(4, 2))

        self.unidade_var = ctk.StringVar(value="1ª Unidade")
        self.seg_unidade = ctk.CTkSegmentedButton(
            self.card_notas,
            values=["1ª Unidade", "2ª Unidade", "3ª Unidade", "4ª Unidade"],
            variable=self.unidade_var,
            height=32
        )
        self.seg_unidade.pack(fill="x", padx=15, pady=(2, 8))

        # Colunas
        lbl_col = ctk.CTkLabel(
            self.card_notas, 
            text="Letras das Colunas no Excel (separadas por vírgula):", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        lbl_col.pack(anchor="w", padx=15, pady=(4, 2))

        self.entry_colunas = ctk.CTkEntry(self.card_notas, placeholder_text="Ex: B, C, D (na mesma ordem das atividades do SIGEduc)", height=36)
        self.entry_colunas.pack(fill="x", padx=15, pady=(2, 4))

        lbl_dica_col = ctk.CTkLabel(
            self.card_notas,
            text="Dica: Se a tela do portal pede Simulado e Trabalho, e no Excel estão nas colunas C e E, digite: C, E",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray"
        )
        lbl_dica_col.pack(anchor="w", padx=15, pady=(0, 8))

        # Formato Decimal e FV
        opcoes_row = ctk.CTkFrame(self.card_notas, fg_color="transparent")
        opcoes_row.pack(fill="x", padx=15, pady=(4, 10))
        opcoes_row.grid_columnconfigure(0, weight=1)
        opcoes_row.grid_columnconfigure(1, weight=1)

        # Formato
        formato_box = ctk.CTkFrame(opcoes_row, fg_color="transparent")
        formato_box.grid(row=0, column=0, sticky="w")

        lbl_fmt = ctk.CTkLabel(formato_box, text="Formato Decimal:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_fmt.pack(anchor="w", pady=(0, 2))

        self.formato_nota_var = ctk.StringVar(value="ponto")
        rb_ponto = ctk.CTkRadioButton(formato_box, text="Ponto: 7.5 (Padrão SIGEduc)", variable=self.formato_nota_var, value="ponto")
        rb_ponto.pack(anchor="w", pady=2)
        rb_virg = ctk.CTkRadioButton(formato_box, text="Vírgula: 7,5", variable=self.formato_nota_var, value="virgula")
        rb_virg.pack(anchor="w", pady=2)
        rb_orig = ctk.CTkRadioButton(formato_box, text="Original da planilha", variable=self.formato_nota_var, value="original")
        rb_orig.pack(anchor="w", pady=2)

        # Falta Vinculada Checkbox
        fv_box = ctk.CTkFrame(opcoes_row, fg_color="transparent")
        fv_box.grid(row=0, column=1, sticky="nw", padx=(20, 0))

        lbl_fv_title = ctk.CTkLabel(fv_box, text="Falta Vinculada (FV):", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_fv_title.pack(anchor="w", pady=(0, 4))

        self.chk_fv_var = ctk.BooleanVar(value=True)
        self.chk_fv = ctk.CTkCheckBox(
            fv_box,
            text="Preencher Falta Vinculada (FV) automaticamente",
            variable=self.chk_fv_var,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.chk_fv.pack(anchor="w", pady=2)

        lbl_fv_desc = ctk.CTkLabel(
            fv_box,
            text="Responde 'Sim' na tela pós-gravação e marca FV para avaliações em branco.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray",
            wraplength=280,
            justify="left"
        )
        lbl_fv_desc.pack(anchor="w", pady=(2, 0))

        # --- CARD 5: SEGURANÇA E GRAVAÇÃO ---
        card_senha = ctk.CTkFrame(self.tab_op, corner_radius=10)
        card_senha.grid(row=3, column=0, padx=10, pady=8, sticky="ew")
        card_senha.grid_columnconfigure(0, weight=1)

        lbl_card4 = ctk.CTkLabel(
            card_senha, 
            text="4. AUTENTICAÇÃO E GRAVAÇÃO", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#2563EB", "#60A5FA")
        )
        lbl_card4.pack(anchor="w", padx=15, pady=(10, 4))

        self.usar_senha_var = ctk.BooleanVar(value=True)
        self.chk_senha = ctk.CTkCheckBox(
            card_senha, 
            text="Preencher senha e gravar automaticamente no portal", 
            variable=self.usar_senha_var, 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), 
            command=self._on_usar_senha_changed
        )
        self.chk_senha.pack(anchor="w", padx=15, pady=(2, 6))

        senha_row = ctk.CTkFrame(card_senha, fg_color="transparent")
        senha_row.pack(fill="x", padx=15, pady=(0, 12))

        self.entry_senha = ctk.CTkEntry(
            senha_row, 
            show="*", 
            width=240, 
            height=36,
            placeholder_text="Senha do SIGEduc"
        )
        self.entry_senha.pack(side="left", padx=(0, 10))

        self.senha_visivel = False
        self.btn_ver_senha = ctk.CTkButton(
            senha_row,
            text="👁 Mostrar",
            width=90,
            height=36,
            command=self.toggle_ver_senha,
            fg_color=("#9CA3AF", "#4B5563"),
            hover_color=("#6B7280", "#374151")
        )
        self.btn_ver_senha.pack(side="left")

        # --- BOTÃO INICIAR ---
        self.btn_iniciar = ctk.CTkButton(
            self.tab_op, 
            text="▶  INICIAR AUTOMAÇÃO", 
            command=self.iniciar_thread, 
            fg_color="#059669", 
            hover_color="#047857", 
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), 
            height=48, 
            corner_radius=10
        )
        self.btn_iniciar.grid(row=4, column=0, padx=10, pady=(14, 10), sticky="ew")

        # Atualiza a visibilidade inicial
        self.update_ui()

    def setup_aba_logs(self):
        """Monta a aba de Logs do Sistema com console e barra de ferramentas."""
        self.tab_log.grid_columnconfigure(0, weight=1)
        self.tab_log.grid_rowconfigure(1, weight=1)

        # Barra de ferramentas do log
        log_tools = ctk.CTkFrame(self.tab_log, fg_color="transparent")
        log_tools.grid(row=0, column=0, padx=10, pady=(5, 5), sticky="ew")
        log_tools.grid_columnconfigure(0, weight=1)

        lbl_log_title = ctk.CTkLabel(
            log_tools, 
            text="Console de Execução em Tempo Real:", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        lbl_log_title.grid(row=0, column=0, sticky="w")

        btn_copy = ctk.CTkButton(
            log_tools, 
            text="📋 Copiar Logs", 
            width=110, 
            height=30, 
            command=self.copiar_logs,
            fg_color=("#3B82F6", "#1D4ED8")
        )
        btn_copy.grid(row=0, column=1, padx=(0, 8), sticky="e")

        btn_clear = ctk.CTkButton(
            log_tools, 
            text="🧹 Limpar", 
            width=90, 
            height=30, 
            command=self.limpar_logs,
            fg_color=("#9CA3AF", "#4B5563"),
            hover_color=("#6B7280", "#374151")
        )
        btn_clear.grid(row=0, column=2, sticky="e")

        # Caixa de texto do log
        self.log_text = ctk.CTkTextbox(
            self.tab_log, 
            state="disabled", 
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8
        )
        self.log_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def setup_aba_ajuda(self):
        """Monta a aba com instruções rápidas e dicas ao docente."""
        self.tab_ajuda.grid_columnconfigure(0, weight=1)

        info_frame = ctk.CTkScrollableFrame(self.tab_ajuda, corner_radius=10)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        dicas = [
            ("🔐 Sessão e Login Salvo", "Na primeira vez que rodar, faça login no Google Chrome que abrir. O perfil fica salvo localmente para que você não precise digitar o código de verificação toda vez."),
            ("📅 Lançamento de Frequência", "Digite as datas separadas por vírgula ou use o calendário integrado. O robô ordena as datas cronologicamente e nunca descarta a sua turma aberta."),
            ("👥 Modo [5] - 100% Presentes", "Se todos os alunos compareceram nas datas informadas, selecione o Modo 5. Não é necessário carregar nenhuma planilha ou arquivo de texto."),
            ("📊 Lançamento de Notas", "Indique a Unidade Avaliativa (1ª a 4ª) e digite as colunas do Excel correspondentes (ex: B, C). O robô verifica a aba da unidade ativa antes de lançar."),
            ("🚫 Falta Vinculada (FV)", "Se a opção de FV estiver marcada, após lançar as notas o robô responde 'Sim' para preencher notas em branco e marca FV automaticamente nas atividades sem nota."),
            ("🛡️ Proteção de Nomes Parecidos", "O sistema utiliza algoritmo fonético e análise estrita de sobrenomes, evitando cruzar notas de alunos com prenomes idênticos (ex: Maria Vitória).")
        ]

        for titulo, desc in dicas:
            card = ctk.CTkFrame(info_frame, corner_radius=8)
            card.pack(fill="x", pady=6, padx=5)

            lbl_t = ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=("#2563EB", "#60A5FA"))
            lbl_t.pack(anchor="w", padx=12, pady=(8, 2))

            lbl_d = ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(family="Segoe UI", size=12), justify="left", wraplength=760)
            lbl_d.pack(anchor="w", padx=12, pady=(0, 8))

    def setup_status_bar(self):
        """Barra de status no rodapé da janela."""
        self.status_bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="transparent")
        self.status_bar.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            self.status_bar,
            text="🟢 Pronto para iniciar | Navegador configurado com perfil salvo",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray",
            anchor="w"
        )
        self.lbl_status.grid(row=0, column=0, sticky="w")

    # --- Handlers de UI ---

    def _on_tarefa_changed(self, valor):
        if "Frequência" in valor:
            self.tarefa_var.set("frequencia")
        else:
            self.tarefa_var.set("notas")
        self.update_ui()

    def _on_modo_frequencia_changed(self):
        modo = self.modo_var.get()
        if modo == "5":
            self.entry_arquivo.configure(state="disabled")
            self.btn_arquivo.configure(state="disabled")
            self.lbl_status_arquivo.configure(
                text="✓ Modo 100% Presentes ativado: Seleção de arquivo dispensada!",
                text_color=("#059669", "#10B981")
            )
        else:
            self.entry_arquivo.configure(state="normal")
            self.btn_arquivo.configure(state="normal")
            self._atualizar_status_arquivo_atual()

    def _on_usar_senha_changed(self):
        if self.usar_senha_var.get():
            self.entry_senha.configure(state="normal")
            self.btn_ver_senha.configure(state="normal")
        else:
            self.entry_senha.configure(state="disabled")
            self.btn_ver_senha.configure(state="disabled")

    def toggle_ver_senha(self):
        if self.senha_visivel:
            self.entry_senha.configure(show="*")
            self.btn_ver_senha.configure(text="👁 Mostrar")
            self.senha_visivel = False
        else:
            self.entry_senha.configure(show="")
            self.btn_ver_senha.configure(text="🔒 Ocultar")
            self.senha_visivel = True

    def update_ui(self):
        """Alterna a exibição entre os cards de Frequência e Notas."""
        tarefa = self.tarefa_var.get()
        if tarefa == "notas":
            self.card_freq.grid_remove()
            self.card_notas.grid(row=2, column=0, padx=10, pady=8, sticky="ew")
            self.entry_arquivo.configure(placeholder_text="Selecione a planilha Excel de notas (.xlsx)...")
        else:
            self.card_notas.grid_remove()
            self.card_freq.grid(row=2, column=0, padx=10, pady=8, sticky="ew")
            self.entry_arquivo.configure(placeholder_text="Selecione o arquivo de alunos (.txt, .csv ou .xlsx)...")

        self._on_modo_frequencia_changed()
        self._on_usar_senha_changed()

    def procurar_arquivo(self):
        tarefa = self.tarefa_var.get()
        if tarefa == "frequencia":
            filetypes = (("Arquivos de Alunos", "*.txt;*.csv;*.xlsx"), ("Todos os Arquivos", "*.*"))
        else:
            filetypes = (("Planilhas Excel", "*.xlsx"), ("Todos os Arquivos", "*.*"))
            
        filename = filedialog.askopenfilename(title="Selecione o arquivo", filetypes=filetypes)
        if filename:
            self.entry_arquivo.delete(0, "end")
            self.entry_arquivo.insert(0, filename)
            self._atualizar_status_arquivo_atual()

    def _atualizar_status_arquivo_atual(self):
        caminho = self.entry_arquivo.get().strip().strip('"')
        if not caminho:
            self.lbl_status_arquivo.configure(text="Nenhum arquivo selecionado.", text_color="gray")
            return
        if not os.path.exists(caminho):
            self.lbl_status_arquivo.configure(text="❌ Arquivo não encontrado no disco.", text_color="#EF4444")
            return

        nome_base = os.path.basename(caminho)
        tarefa = self.tarefa_var.get()
        try:
            if tarefa == "frequencia":
                nomes = sf.ler_nomes(caminho)
                self.lbl_status_arquivo.configure(
                    text=f"✓ Arquivo carregado: {nome_base} ({len(nomes)} alunos identificados)",
                    text_color=("#059669", "#10B981")
                )
            else:
                self.lbl_status_arquivo.configure(
                    text=f"✓ Planilha selecionada: {nome_base}",
                    text_color=("#059669", "#10B981")
                )
        except Exception:
            self.lbl_status_arquivo.configure(text=f"✓ Arquivo selecionado: {nome_base}", text_color="gray")

    def limpar_datas_entry(self):
        self.entry_datas.delete(0, "end")

    def abrir_calendario(self):
        """Abre janela de calendário moderna com seleção múltipla, ordenação e limpeza."""
        top = ctk.CTkToplevel(self)
        top.title("Selecionar Datas")
        top.geometry("400x500")
        top.resizable(False, False)
        top.transient(self)
        top.grab_set()

        lbl = ctk.CTkLabel(top, text="Clique nos dias no calendário para adicionar:", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
        lbl.pack(pady=(12, 6))

        cal = Calendar(top, selectmode='day', date_pattern='dd/MM/yyyy')
        cal.pack(pady=5, padx=20, fill="both", expand=True)

        lbl_lista = ctk.CTkLabel(top, text="Datas Selecionadas (Ordenação Automática):", font=ctk.CTkFont(family="Segoe UI", size=12))
        lbl_lista.pack(pady=(8, 2))

        textbox = ctk.CTkTextbox(top, height=55, width=320, font=ctk.CTkFont(family="Consolas", size=12))
        textbox.pack(pady=4)

        # Pré-carrega o que já estiver digitado no campo principal
        atual_main = self.entry_datas.get().strip()
        if atual_main:
            datas_iniciais = sf.parsear_datas(atual_main)
            if datas_iniciais:
                textbox.insert("1.0", ", ".join(f"{d:02d}/{m:02d}" for d, m in datas_iniciais))

        def dia_clicado(event):
            data_obj = cal.selection_get()
            if data_obj:
                data_str = data_obj.strftime("%d/%m")
                atual = textbox.get("1.0", "end").strip()
                lista_existente = sf.parsear_datas(atual)
                pedacos = data_str.split("/")
                nova_tupla = (int(pedacos[0]), int(pedacos[1]))
                if nova_tupla not in lista_existente:
                    lista_existente.append(nova_tupla)
                    lista_existente.sort(key=lambda x: (x[1], x[0]))
                    textbox.delete("1.0", "end")
                    textbox.insert("1.0", ", ".join(f"{d:02d}/{m:02d}" for d, m in lista_existente))

        cal.bind("<<CalendarSelected>>", dia_clicado)

        def limpar():
            textbox.delete("1.0", "end")

        def confirmar():
            datas_escolhidas = textbox.get("1.0", "end").strip()
            if datas_escolhidas:
                combinadas = sf.parsear_datas(datas_escolhidas)
                self.entry_datas.delete(0, "end")
                self.entry_datas.insert(0, ", ".join(f"{d:02d}/{m:02d}" for d, m in combinadas))
            top.destroy()

        btn_row = ctk.CTkFrame(top, fg_color="transparent")
        btn_row.pack(pady=12)

        btn_limp = ctk.CTkButton(btn_row, text="Limpar", command=limpar, fg_color=("#9CA3AF", "#4B5563"), hover_color=("#6B7280", "#374151"), width=100)
        btn_limp.grid(row=0, column=0, padx=8)

        btn_ok = ctk.CTkButton(btn_row, text="Confirmar Datas", command=confirmar, fg_color="#059669", hover_color="#047857", width=140, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        btn_ok.grid(row=0, column=1, padx=8)

    def copiar_logs(self):
        conteudo = self.log_text.get("1.0", "end").strip()
        if conteudo:
            self.clipboard_clear()
            self.clipboard_append(conteudo)
            messagebox.showinfo("Sucesso", "Logs copiados para a área de transferência!")

    def limpar_logs(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # --- Execução em Background ---

    def iniciar_thread(self):
        self.btn_iniciar.configure(state="disabled", text="⏳ EXECUTANDO AUTOMAÇÃO...", fg_color="#D97706")
        self.lbl_status.configure(text="🟡 Executando automação no SIGEduc...", text_color="#F59E0B")
        self.tabview.set("📋 Logs em Tempo Real")

        t = threading.Thread(target=self.rodar_automacao)
        t.daemon = True
        t.start()

    def rodar_automacao(self):
        try:
            self._garantir_navegador()
            self._executar_logica_sigeduc()
        except Exception:
            import traceback
            print("\n" + "="*60)
            print("❌ OCORREU UM ERRO INESPERADO NA EXECUÇÃO:")
            print(traceback.format_exc())
            print("="*60)
            self.lbl_status.configure(text="🔴 Ocorreu um erro durante a automação. Veja os logs.", text_color="#EF4444")
        finally:
            self.btn_iniciar.configure(state="normal", text="▶  INICIAR AUTOMAÇÃO", fg_color="#059669")
            self.lbl_status.configure(text="🟢 Pronto para iniciar | Navegador configurado com perfil salvo", text_color="gray")

    def _garantir_navegador(self):
        print("\nVerificando dependências do navegador Chromium...")
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
            print("✓ Navegador pronto.")
        except Exception as e:
            print(f"⚠️ Aviso na verificação de navegador: {e}")

    def mostrar_instrucoes_sync(self, titulo, passos, tipo) -> None:
        event = threading.Event()
        self.after(0, self._criar_dialogo_instrucoes, titulo, passos, tipo, event)
        event.wait()

    def _criar_dialogo_instrucoes(self, titulo, passos, tipo, event):
        sf.trazer_navegador_para_frente()
        InstrucoesDialog(self, titulo, passos, tipo, event)

    def _executar_logica_sigeduc(self):
        tarefa = self.tarefa_var.get()
        caminho_arquivo = self.entry_arquivo.get().strip().strip('"')
        usar_senha = self.usar_senha_var.get()
        senha = self.entry_senha.get()
        modo = self.modo_var.get()

        print("\n" + "="*60)
        print("  INICIANDO AUTOMAÇÃO SIGEDUC")
        print("="*60)

        # Validação do arquivo
        if tarefa == "frequencia" and modo == "5":
            pass
        elif not os.path.exists(caminho_arquivo):
            print(f"❌ Erro: Arquivo '{caminho_arquivo}' não encontrado.")
            return

        nomes = []
        dados_notas = {}
        datas = []

        if tarefa == "frequencia":
            if modo == "5":
                nomes = []
                print("✓ Modo [5] Selecionado: 100% Presentes (todos os alunos da turma receberão presença).")
            else:
                nomes = sf.ler_nomes(caminho_arquivo)
                if not nomes:
                    print("❌ Erro: Nenhum nome encontrado no arquivo.")
                    return
                print(f"✓ {len(nomes)} alunos carregados da lista.")

            texto_datas = self.entry_datas.get().strip()
            datas = sf.parsear_datas(texto_datas)
            if not datas:
                print("❌ Erro: Nenhuma data válida fornecida. Use o formato DD/MM (ex: 11/03, 18/03).")
                return
            print(f"✓ {len(datas)} datas para lançar: {', '.join(f'{d:02d}/{m:02d}' for d, m in datas)}")

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

        if usar_senha and not senha:
            print("❌ Erro: Você marcou para gravar automaticamente, mas deixou a senha vazia.")
            return

        # Controle do Navegador
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
                self.mostrar_instrucoes_sync(
                    "Login no Sigeduc Necessário",
                    [
                        "Localize a janela do navegador Chrome que acabou de abrir.",
                        "Digite seu usuário/senha e faça login no portal.",
                        "Aguarde o carregamento do painel do professor.",
                        "Volte a esta janela e clique no botão abaixo para prosseguir."
                    ],
                    "login"
                )

            # FLUXO DE FREQUÊNCIA
            if tarefa == "frequencia":
                if not sf.garantir_pagina_calendario(page):
                    print("⚠️ Não foi possível encontrar o calendário automaticamente.")
                    self.mostrar_instrucoes_sync(
                        "Ir para o Calendário da Turma",
                        [
                            "No Chrome, acesse o menu de turmas e selecione a turma desejada.",
                            "Vá em 'Diário de Classe' -> 'Frequência'.",
                            "Certifique-se de que a tabela com o calendário de datas está visível na tela.",
                            "Volte aqui e clique no botão abaixo para que o robô prossiga."
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
                                    "No Chrome, vá em 'Diário de Classe' -> 'Frequência'.",
                                    "Certifique-se de que a tabela com o calendário está visível.",
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
                            falhas += 1
                            continue
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

                print(f"\n✅ FIM DA TAREFA: {sucesso} Datas concluídas | {falhas} Falhas")
                messagebox.showinfo("Concluído", f"Automação de frequência concluída!\n\nSucesso: {sucesso}\nFalhas: {falhas}")

            # FLUXO DE NOTAS
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


if __name__ == "__main__":
    app = SigeducGUI()
    app.mainloop()
