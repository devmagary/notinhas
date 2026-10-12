# SIGEduc Auto — Extensão para Navegadores Chromium (Lançador de Notas)

Extensão de navegador compatível com **Google Chrome, Microsoft Edge, Brave e Opera** desenvolvida para automatizar o preenchimento de **notas avaliativas** e **faltas vinculadas (FV)** no portal **SIGEduc Bahia**, utilizando planilhas Excel (`.xlsx`) como fonte de dados.

---

## 🎯 Por que a Extensão?

1. **Sem Dependência de Python:** Não precisa de terminal, Python, Playwright ou drivers externos instalados.
2. **Utiliza sua Sessão Real:** Roda diretamente dentro do seu navegador habitual, sem risco de conflito de perfis ou deslogar da conta.
3. **Leitura Local de Excel:** Processa arquivos `.xlsx` diretamente no navegador com a biblioteca SheetJS, mantendo total privacidade (LGPD — nenhum dado sai do seu computador).
4. **Generalização Universal para Qualquer Turma/Professor:** Projetada para atender a toda a rede estadual (Ensino Médio regular, Educação Profissional/Cursos Técnicos, EJA, Tempo Integral). Adapta-se automaticamente a 1, 2, 3, 4, 5 ou mais atividades avaliativas.
5. **Detecção Dinâmica de Cabeçalhos e Colunas:** Reconhece cabeçalhos mesmo em planilhas com blocos institucionais profundos (até 25 linhas de metadados escolares) e identifica títulos como *DISCENTE*, *ESTUDANTE*, *P1*, *AV1*, *TRABALHO*, *SEMINÁRIO*, pulando colunas não-avaliativas intermediárias (*Faltas*, *Recuperação*) sem quebrar a sequência.
6. **Mapeamento Visual & Alerta de Divergência:** Mostra exatamente qual coluna do Excel alimenta cada atividade do SIGEduc (ex: `Coluna B (Prova) ➔ SIGEduc: Prova (4.0)`) e emite avisos proativos caso as contagens divirjam.
7. **Transparência de Alunos Não Correspondidos:** Informa com clareza quais estudantes estão no SIGEduc mas não constam na planilha (novos matriculados) e quais estão na planilha mas não no portal (transferidos/evadidos).
8. **Arquitetura de Reconciliação do DOM em 2 Passos:** Passagem sequencial assíncrona com micro-cadência configurável (40ms a 120ms) + auditoria imediata de live DOM, recuperando qualquer nota perdida por requisições parciais do RichFaces.
9. **Casamento Fonético e Proteção de Nomes:** Reconhece alunos mesmo com acentos/cedilha diferentes (*Rebouças* vs *Reboucas*, *Luiz* vs *Luis*, *Matheus* vs *Mateus*) e com símbolos especiais (ex: ícone de acessibilidade ♿) e impede rigorosamente a troca de notas entre estudantes com o mesmo prenome (ex: *Maria Vitória Santos* vs *Maria Vitória Tosta*).
10. **Falta Vinculada (FV) Automatizada:** Responde a pergunta de notas em branco e marca as caixas de FV correspondentes aos alunos ausentes na planilha.
11. **Aba de Logs e Diagnóstico em Tempo Real:** Terminal integrado de logs no próprio popup para inspeção detalhada de status, injeção de scripts e cópia de diagnósticos com um clique.

---

## 📦 Como Instalar / Atualizar no Navegador

A extensão utiliza o padrão **Manifest V3** e é compatível com qualquer navegador baseado em Chromium: **Google Chrome, Microsoft Edge, Brave e Opera**.

### ⚡ Método Rápido (Windows - 1 Clique):
1. Dê um **duplo clique** no arquivo `instalar_extensao.bat`.
2. Escolha o seu navegador digitando o número correspondente (1 para Chrome, 2 para Edge, 3 para Brave, 4 para Opera).
3. O script copia a extensão para uma pasta definitiva no seu computador e abre a página de extensões do navegador.
4. Na tela do navegador, ative o **"Modo do desenvolvedor"** e clique em **"Carregar sem compactação"**, selecionando a pasta aberta!

### 🛠️ Método Manual:
1. Abra o navegador (Chrome, Edge, Brave ou Opera).
2. Acesse a página de extensões:
   - **Google Chrome / Brave:** `chrome://extensions`
   - **Microsoft Edge:** `edge://extensions`
   - **Opera / Opera GX:** `opera://extensions`
3. Ative a chave **"Modo do desenvolvedor"** (*Developer mode*) no canto superior direito.
4. Se já tinha a extensão instalada:
   - Clique no ícone de **atualizar (seta circular 🔄)** no cartão do **SIGEduc Auto**.
5. Se for a primeira instalação:
   - Clique em **"Carregar sem compactação"** (*Load unpacked*).
   - Selecione a pasta da extensão (`extensao-notas`).
6. Pronto! O ícone **📊 SIGEduc Auto** aparecerá na barra de ferramentas do seu navegador (fixe-o para acesso rápido).

---

## 🚀 Como Usar no Dia a Dia

1. **Acesse o SIGEduc:**
   - Faça login normalmente no portal [SIGEduc Bahia](https://sigeduc.educacao.ba.gov.br/).
   - Entre na turma e vá até a tela de lançamento de notas:
     `Diário de Classe Digital` -> `Lançar Notas para Avaliações das Unidades`.
2. **Abra a Extensão:**
   - Clique no ícone do **SIGEduc Auto** na barra do navegador.
   - O indicador no topo confirmará: `🟢 Tela de Notas detectada: X estudantes, Y atividades na 1ª Unidade`.
3. **Selecione a Planilha:**
   - Arraste ou selecione seu arquivo `.xlsx`.
   - Se a planilha tiver várias abas (uma por turma), escolha a aba desejada no menu suspenso.
   - O sistema detecta automaticamente a coluna dos nomes e as colunas de notas.
   - Confira o painel de **Mapeamento de Atividades** que relaciona cada coluna da planilha à respectiva atividade do SIGEduc.
4. **Escolha a Unidade:**
   - Selecione `1ª Unidade`, `2ª Unidade`, `3ª Unidade` ou `4ª Unidade`.
   - A extensão sincroniza e ativa a aba correspondente no SIGEduc.
5. **Confira a Pré-visualização:**
   - A lista de conferência exibirá os estudantes casados e as notas extraídas.
   - Caso haja alunos sem par (transferidos ou novos), o painel amarelo de divergências permite inspecionar seus nomes.
6. **Preencha:**
   - Clique no botão **"🚀 Preencher Notas no SIGEduc"**.
   - As notas serão inseridas com cadência controlada e passarão pela auditoria de reconciliação automática.
7. **Gravação:**
   - Você pode revisar as notas na tela e clicar manualmente em **Gravar**, ou marcar a opção de gravar com senha diretamente no popup da extensão.
   - Se houver alunos sem nota e a opção de **Falta Vinculada (FV)** estiver marcada, a extensão também preenche as caixas de FV automaticamente.

---

## 📜 Aba de Logs & Diagnóstico

Se ocorrer qualquer dúvida de conexão ou instabilidade na rede:
1. Abra a extensão e clique na aba **"📜 Logs & Diagnóstico"** no topo.
2. Veja o diagnóstico em tempo real:
   - Status da aba ativa e do Content Script.
   - Quantidade de estudantes detectados na página e na planilha.
   - Quantidade de alunos casados pelo algoritmo fonético.
3. Use os botões de ação:
   - **`🔄 Testar Conexão / Reinjetar Script`**: Força a reconexão imediata e reinjeta os scripts de automação na aba do SIGEduc caso a página tenha ficado inativa.
   - **`🌐 Recarregar Página`**: Atualiza a página do SIGEduc diretamente pela extensão.
   - **`📋 Copiar`**: Copia o histórico completo de logs para a área de transferência.

---

## 📁 Estrutura de Arquivos

```
extensao-notas/
├── manifest.json              # Configuração Manifest V3 da extensão (v1.0.4)
├── README.md                  # Manual de uso e instalação
├── icons/                     # Ícones em tamanhos 16x16, 48x48 e 128x128
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
├── vendor/
│   └── xlsx.full.min.js       # SheetJS para leitura de planilhas Excel (.xlsx)
├── lib/
│   ├── nomes.js               # Algoritmo fonético e casamento estrito de nomes
│   └── excel.js               # Extrator de notas, detecção de cabeçalhos e colunas
├── content/
│   ├── content.js             # Content Script (preenchimento DOM, reconciliação e FV)
│   └── content.css            # Estilos de destaque para inputs preenchidos e toasts
├── popup/
│   ├── popup.html             # Interface gráfica com mapeamento visual e logs
│   ├── popup.css              # Estilos modernos da interface e terminal escuro
│   └── popup.js               # Controlador do popup, injeção dinâmica e Logger
├── scripts/
│   └── gerar_icones.js        # Script gerador de ícones PNG
└── tests/
    ├── mock_dom.js            # Ambiente DOM representativo do RichFaces para testes
    └── test_extension.js      # Suíte com 22 testes automatizados cobrindo 6 turmas reais
```

---

## 🧪 Testes Automatizados

Para rodar a suíte completa de testes unitários e de integração:

```bash
node extensao-notas/tests/test_extension.js
```
