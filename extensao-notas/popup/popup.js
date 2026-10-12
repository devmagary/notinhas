/*
 * Controlador do Popup da Extensão SIGEduc Auto
 * Gerencia a interface, leitura de planilhas Excel, comunicação com o Content Script e Logs.
 */

(function () {
  "use strict";

  // Estado em memória da sessão
  let tabIdAtiva = null;
  let tabUrlAtiva = "";
  let estadoTelaSIGEduc = null;
  let workbookAtual = null;
  let colunasPlanilhaAtual = [];
  let dadosAlunosExtraidos = [];
  let unidadeSelecionada = 1;
  let filtroLogAtual = "todos";

  // =========================================================================
  // 1. Elementos do DOM
  // =========================================================================
  // Navegação
  const tabNavLancamento = document.getElementById("tab-nav-lancamento");
  const tabNavLogs = document.getElementById("tab-nav-logs");
  const viewLancamento = document.getElementById("view-lancamento");
  const viewLogs = document.getElementById("view-logs");
  const badgeLogCount = document.getElementById("badge-log-count");

  // Status Conexão
  const elStatusConexao = document.getElementById("status-conexao");
  const elStatusTexto = document.getElementById("status-conexao-texto");
  const btnRecarregarStatus = document.getElementById("btn-recarregar-status");

  // Passo 1: Excel
  const dropZone = document.getElementById("drop-zone");
  const inputArquivo = document.getElementById("input-arquivo");
  const boxArquivoInfo = document.getElementById("arquivo-info");
  const txtNomeArquivo = document.getElementById("txt-nome-arquivo");
  const btnRemoverArquivo = document.getElementById("btn-remover-arquivo");
  const selectAba = document.getElementById("select-aba");
  const selectColNome = document.getElementById("select-col-nome");
  const inputColunasNotas = document.getElementById("input-colunas-notas");
  const radiosFormato = document.querySelectorAll("input[name='formato-nota']");
  const boxMapeamentoColunas = document.getElementById("box-mapeamento-colunas");
  const alertaDivergenciaColunas = document.getElementById("alerta-divergencia-colunas");
  const listaMapeamentoColunas = document.getElementById("lista-mapeamento-colunas");
  const boxGerarModelo = document.getElementById("box-gerar-modelo");
  const txtModeloTitulo = document.getElementById("txt-modelo-titulo");
  const txtModeloDesc = document.getElementById("txt-modelo-desc");
  const btnBaixarModelo = document.getElementById("btn-baixar-modelo");

  // Passo 2: Unidade
  const segmentedUnidade = document.getElementById("segmented-unidade");

  // Passo 3: Preview
  const cardPreview = document.getElementById("card-preview");
  const cntCasados = document.getElementById("cnt-casados");
  const cntSemParTela = document.getElementById("cnt-sem-par-tela");
  const cntSemParExcel = document.getElementById("cnt-sem-par-excel");
  const cntTotalExcel = document.getElementById("cnt-total-excel");
  const boxAlunosDivergentes = document.getElementById("box-alunos-divergentes");
  const txtQtdDivergentes = document.getElementById("txt-qtd-divergentes");
  const listaAlunosDivergentes = document.getElementById("lista-alunos-divergentes");
  const previewTbody = document.getElementById("preview-tbody");

  // Passo 4: Ações e Gravação
  const chkAutoFV = document.getElementById("chk-auto-fv");
  const chkAutoGravar = document.getElementById("chk-auto-gravar");
  const boxSenha = document.getElementById("box-senha");
  const inputSenha = document.getElementById("input-senha");
  const selectDelayCadencia = document.getElementById("select-delay-cadencia");
  const btnPreencher = document.getElementById("btn-preencher");
  const btnPreencherFV = document.getElementById("btn-preencher-fv");
  const msgStatus = document.getElementById("mensagem-status");

  // Aba 2: Diagnóstico e Logs
  const diagAbaInfo = document.getElementById("diag-aba-info");
  const diagScriptStatus = document.getElementById("diag-script-status");
  const diagTelaDetectada = document.getElementById("diag-tela-detectada");
  const diagAlunosTela = document.getElementById("diag-alunos-tela");
  const diagExcelInfo = document.getElementById("diag-excel-info");
  const diagMatchInfo = document.getElementById("diag-match-info");
  const btnRetestarConexao = document.getElementById("btn-retestar-conexao");
  const btnRecarregarPaginaAba = document.getElementById("btn-recarregar-pagina-aba");
  const btnCopiarLogs = document.getElementById("btn-copiar-logs");
  const btnLimparLogs = document.getElementById("btn-limpar-logs");
  const logTerminal = document.getElementById("log-terminal");
  const filterPills = document.querySelectorAll(".sgn-filter-pill");

  // =========================================================================
  // 2. Sistema de Logger do Popup
  // =========================================================================
  const Logger = {
    itens: [],
    maxItens: 250,
    errosCount: 0,

    adicionar(tipo, mensagem, detalhe = null) {
      const agora = new Date();
      const hora = agora.toLocaleTimeString("pt-BR", { hour12: false });
      const item = {
        id: Date.now() + Math.random(),
        hora,
        tipo, // "info" | "sucesso" | "aviso" | "erro" | "dom" | "excel"
        mensagem,
        detalhe
      };

      if (tipo === "erro") {
        this.errosCount++;
      }

      this.itens.push(item);
      if (this.itens.length > this.maxItens) {
        this.itens.shift();
      }

      this.renderizarItem(item);
      this.atualizarBadge();
    },

    info(msg, det) { this.adicionar("info", msg, det); },
    sucesso(msg, det) { this.adicionar("sucesso", msg, det); },
    aviso(msg, det) { this.adicionar("aviso", msg, det); },
    erro(msg, det) { this.adicionar("erro", msg, det); },
    dom(msg, det) { this.adicionar("dom", msg, det); },
    excel(msg, det) { this.adicionar("excel", msg, det); },

    atualizarBadge() {
      if (this.errosCount > 0) {
        badgeLogCount.textContent = this.errosCount;
        badgeLogCount.style.display = "inline-block";
      } else {
        badgeLogCount.style.display = "none";
      }
    },

    limpar() {
      this.itens = [];
      this.errosCount = 0;
      this.atualizarBadge();
      logTerminal.innerHTML = '<div class="sgn-log-empty">Nenhum evento registrado ainda.</div>';
    },

    obterTextoFormatado() {
      return this.itens.map(item => {
        const detStr = item.detalhe ? " | Detalhe: " + JSON.stringify(item.detalhe) : "";
        return `[${item.hora}] [${item.tipo.toUpperCase()}] ${item.mensagem}${detStr}`;
      }).join("\n");
    },

    renderizarItem(item) {
      if (this.itens.length === 1) {
        logTerminal.innerHTML = "";
      }

      // Aplica filtro visual atual
      const deveExibir = (filtroLogAtual === "todos") || (item.tipo === filtroLogAtual);
      const row = document.createElement("div");
      row.className = "sgn-log-entry";
      row.dataset.tipo = item.tipo;
      if (!deveExibir) row.style.display = "none";

      row.innerHTML = `
        <span class="sgn-log-time">${item.hora}</span>
        <span class="sgn-log-tag tag-${item.tipo}">[${item.tipo.toUpperCase()}]</span>
        <span class="sgn-log-text">${item.mensagem}</span>
      `;

      logTerminal.appendChild(row);
      logTerminal.scrollTop = logTerminal.scrollHeight;
    },

    aplicarFiltro(filtro) {
      filtroLogAtual = filtro;
      const rows = logTerminal.querySelectorAll(".sgn-log-entry");
      rows.forEach(r => {
        if (filtro === "todos" || r.dataset.tipo === filtro) {
          r.style.display = "flex";
        } else {
          r.style.display = "none";
        }
      });
      logTerminal.scrollTop = logTerminal.scrollHeight;
    }
  };

  // =========================================================================
  // 3. Comunicação Segura com Content Script (com Reinjeção Automática)
  // =========================================================================
  async function enviarMensagemSegura(tipo, payload = {}) {
    if (!tabIdAtiva) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.id) {
        tabIdAtiva = tab.id;
        tabUrlAtiva = tab.url || "";
      } else {
        Logger.erro("Nenhuma aba ativa encontrada no navegador.");
        return { sucesso: false, erro: "Nenhuma aba ativa identificada." };
      }
    }

    const mensagem = { tipo, ...payload };

    // 1. Tenta envio direto
    try {
      const resposta = await new Promise((resolve, reject) => {
        chrome.tabs.sendMessage(tabIdAtiva, mensagem, (res) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(res);
          }
        });
      });

      if (resposta && resposta.sucesso !== false) {
        return { sucesso: true, dados: resposta };
      }
      return { sucesso: false, erro: resposta ? resposta.erro : "Resposta inválida." };
    } catch (errPrimeira) {
      Logger.aviso(`Comunicação direta (${tipo}) falhou: "${errPrimeira.message}". Reinjetando scripts na aba ${tabIdAtiva}...`);

      // 2. Se falhar, injeta dinamicamente via chrome.scripting
      try {
        await chrome.scripting.insertCSS({
          target: { tabId: tabIdAtiva, allFrames: true },
          files: ["content/content.css"]
        });

        await chrome.scripting.executeScript({
          target: { tabId: tabIdAtiva, allFrames: true },
          files: ["lib/nomes.js", "content/content.js"]
        });

        Logger.dom("Content script e CSS reinjetados via chrome.scripting.");

        // Aguarda 150ms para registro dos listeners no navegador
        await new Promise(r => setTimeout(r, 150));

        // 3. Tenta enviar novamente
        const respostaSegunda = await new Promise((resolve, reject) => {
          chrome.tabs.sendMessage(tabIdAtiva, mensagem, (res) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(res);
            }
          });
        });

        if (respostaSegunda && respostaSegunda.sucesso !== false) {
          Logger.sucesso(`Comunicação restabelecida com sucesso após reinjeção (${tipo})!`);
          return { sucesso: true, dados: respostaSegunda };
        }
        return { sucesso: false, erro: respostaSegunda ? respostaSegunda.erro : "Resposta inválida após reinjeção." };
      } catch (errSegunda) {
        Logger.erro(`Falha persistente na comunicação (${tipo}): ${errSegunda.message}`);
        return { sucesso: false, erro: errSegunda.message };
      }
    }
  }

  // =========================================================================
  // 4. Verificação de Aba e Inicialização
  // =========================================================================
  async function inicializar() {
    configurarEventosUI();
    Logger.info("SIGEduc Auto Popup inicializado.");
    await verificarAbaAtiva();
  }

  async function verificarAbaAtiva() {
    definirStatus("Verificando conexão com o SIGEduc...", "aviso");
    diagScriptStatus.textContent = "🟡 Testando...";

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) {
        definirStatus("Nenhuma aba ativa identificada.", "erro");
        diagAbaInfo.textContent = "Nenhuma aba ativa";
        diagScriptStatus.textContent = "🔴 Indisponível";
        Logger.erro("Não foi possível identificar a aba ativa.");
        return;
      }

      tabIdAtiva = tab.id;
      tabUrlAtiva = tab.url || "";
      diagAbaInfo.textContent = `Aba #${tabIdAtiva} (${extrairHost(tabUrlAtiva)})`;

      Logger.info(`Aba ativa identificada: ID ${tabIdAtiva} - URL: ${tabUrlAtiva}`);

      if (!tabUrlAtiva.includes("sigeduc") && !tabUrlAtiva.includes("educacao.ba.gov.br")) {
        definirStatus("Abra o portal SIGEduc Bahia para utilizar a extensão.", "erro");
        diagScriptStatus.textContent = "⚠️ URL fora do SIGEduc";
        btnPreencher.disabled = true;
        Logger.aviso(`A página atual não é do portal SIGEduc: ${tabUrlAtiva}`);
        return;
      }

      // Envia PING inicial com suporte a reinjeção automática
      const resPing = await enviarMensagemSegura("PING");
      if (!resPing.sucesso) {
        definirStatus("Falha de conexão com a página (ver aba de logs).", "erro");
        diagScriptStatus.textContent = "🔴 Desconectado";
        Logger.erro(`Falha ao obter resposta do Content Script: ${resPing.erro}`);
        return;
      }

      const dadosPing = resPing.dados;
      estadoTelaSIGEduc = dadosPing;
      diagScriptStatus.textContent = `🟢 Ativo (v${dadosPing.versao || "1.0"})`;
      Logger.sucesso(`Content Script ativo e respondendo na tela '${dadosPing.tela}' (${dadosPing.qtdAlunosTela} estudantes detectados).`);

      processarEstadoTela(dadosPing);
    } catch (err) {
      definirStatus("Erro de comunicação: " + err.message, "erro");
      diagScriptStatus.textContent = "🔴 Erro";
      Logger.erro(`Exceção ao verificar aba: ${err.message}`);
    }
  }

  function extrairHost(url) {
    try {
      const u = new URL(url);
      return u.hostname;
    } catch (e) {
      return url.slice(0, 30);
    }
  }

  function definirStatus(mensagem, tipo = "aviso") {
    elStatusTexto.textContent = mensagem;
    elStatusConexao.className = `sgn-badge sgn-badge-${tipo}`;
  }

  function processarEstadoTela(estado) {
    diagTelaDetectada.textContent = formatarNomeTela(estado.tela);
    diagAlunosTela.textContent = `${estado.qtdAlunosTela} na tabela`;

    if (estado.tela === "notas") {
      definirStatus(`🟢 Tela de Notas detectada: ${estado.qtdAlunosTela} estudantes na ${estado.unidadeAtiva}ª Unidade.`, "sucesso");
      selecionarUnidadeUI(estado.unidadeAtiva);
      btnPreencherFV.style.display = "none";
      if (boxGerarModelo && !workbookAtual) {
        boxGerarModelo.style.display = "flex";
        const turmaLabel = estado.turma ? `Turma: ${estado.turma}` : "Turma detectada";
        txtModeloDesc.textContent = `${turmaLabel} (${estado.qtdAlunosTela} estudantes) • Baixe a planilha com as atividades desta tela.`;
      }
    } else if (estado.tela === "fv") {
      definirStatus(`🟡 Tela de Falta Vinculada (FV) detectada: ${estado.qtdAlunosTela} estudantes.`, "aviso");
      btnPreencherFV.style.display = "block";
      if (boxGerarModelo) boxGerarModelo.style.display = "none";
    } else if (estado.tela === "turmas") {
      definirStatus("🟡 Painel de turmas aberto. Clique em 'Lançar Notas' na turma desejada.", "aviso");
      btnPreencherFV.style.display = "none";
      if (boxGerarModelo) boxGerarModelo.style.display = "none";
    } else {
      definirStatus("🟡 Navegue até a tela de lançamento de notas no SIGEduc.", "aviso");
      btnPreencherFV.style.display = "none";
      if (boxGerarModelo) boxGerarModelo.style.display = "none";
    }

    atualizarPrevisualizacao();
  }

  function formatarNomeTela(tela) {
    switch (tela) {
      case "notas": return "Lançar Notas";
      case "fv": return "Falta Vinculada (FV)";
      case "turmas": return "Minhas Turmas";
      default: return "Outra Tela";
    }
  }

  // =========================================================================
  // 5. Manipulação de Arquivo Excel (.xlsx)
  // =========================================================================
  function carregarArquivo(arquivo) {
    if (!arquivo) return;
    if (!arquivo.name.endsWith(".xlsx") && !arquivo.name.endsWith(".xls")) {
      mostrarMensagem("Por favor, selecione um arquivo Excel válido (.xlsx ou .xls).", "erro");
      Logger.aviso("Tentativa de carregar arquivo não Excel: " + arquivo.name);
      return;
    }

    Logger.info(`Carregando planilha Excel: ${arquivo.name} (${(arquivo.size / 1024).toFixed(1)} KB)...`);

    const reader = new FileReader();
    reader.onload = function (e) {
      try {
        const data = new Uint8Array(e.target.result);
        const { workbook, abas } = window.SgnExcel.carregarWorkbook(data, window.XLSX);

        workbookAtual = workbook;
        txtNomeArquivo.textContent = arquivo.name;
        diagExcelInfo.textContent = `${arquivo.name} (${abas.length} abas)`;

        Logger.excel(`Arquivo lido com sucesso. Abas encontradas: ${abas.join(", ")}`);

        // Popula abas no select
        selectAba.innerHTML = "";
        abas.forEach((aba) => {
          const opt = document.createElement("option");
          opt.value = aba;
          opt.textContent = aba;
          selectAba.appendChild(opt);
        });

        dropZone.style.display = "none";
        boxArquivoInfo.style.display = "flex";
        if (boxGerarModelo) boxGerarModelo.style.display = "none";

        atualizarConfiguracaoAba();
      } catch (err) {
        mostrarMensagem("Erro ao processar o arquivo Excel: " + err.message, "erro");
        Logger.erro(`Erro ao carregar workbook: ${err.message}`);
      }
    };
    reader.readAsArrayBuffer(arquivo);
  }

  function atualizarConfiguracaoAba() {
    if (!workbookAtual) return;
    const nomeAba = selectAba.value;
    const infoAba = window.SgnExcel.inspecionarAba(workbookAtual, nomeAba, window.XLSX);
    colunasPlanilhaAtual = infoAba.colunas || [];

    Logger.excel(`Inspecionando aba '${nomeAba}': ${infoAba.colunas.length} colunas identificadas.`);

    // Popula colunas para o nome do aluno
    selectColNome.innerHTML = "";
    infoAba.colunas.forEach((col) => {
      const opt = document.createElement("option");
      opt.value = col.letra;
      opt.textContent = `${col.letra} - ${col.titulo}`;
      if (col.letra === infoAba.colunaNomeSugerida) {
        opt.selected = true;
      }
      selectColNome.appendChild(opt);
    });

    // Sugere colunas de notas a partir da aba inspecionada
    if (infoAba.colunasNotasSugeridas && infoAba.colunasNotasSugeridas.length > 0) {
      inputColunasNotas.value = infoAba.colunasNotasSugeridas.join(", ");
    } else if (!inputColunasNotas.value.trim()) {
      const idxNome = window.SgnExcel.letraParaIndice(infoAba.colunaNomeSugerida);
      const sugestoes = [];
      const qtdEsperada = (estadoTelaSIGEduc && estadoTelaSIGEduc.qtdColunasInputs) ? estadoTelaSIGEduc.qtdColunasInputs : 3;
      for (let i = 1; i <= qtdEsperada; i++) {
        sugestoes.push(window.SgnExcel.indiceParaLetra(idxNome + i));
      }
      inputColunasNotas.value = sugestoes.join(", ");
    }

    atualizarPrevisualizacao();
  }

  // =========================================================================
  // 6. Pré-visualização, Mapeamento e Conferência de Nomes
  // =========================================================================
  function renderizarMapeamentoColunas(letrasNotas) {
    if (!boxMapeamentoColunas || !alertaDivergenciaColunas || !listaMapeamentoColunas) return;
    if (!letrasNotas || !letrasNotas.length) {
      boxMapeamentoColunas.style.display = "none";
      return;
    }

    const mapaTitulosExcel = new Map();
    if (colunasPlanilhaAtual && Array.isArray(colunasPlanilhaAtual)) {
      colunasPlanilhaAtual.forEach(c => mapaTitulosExcel.set(c.letra, c.titulo));
    }

    const ativsSIGEduc = (estadoTelaSIGEduc && estadoTelaSIGEduc.atividadesSIGEduc && estadoTelaSIGEduc.atividadesSIGEduc.length > 0)
      ? estadoTelaSIGEduc.atividadesSIGEduc
      : [];

    // Alerta de quantidade de atividades/colunas
    if (ativsSIGEduc.length > 0) {
      if (letrasNotas.length === ativsSIGEduc.length) {
        alertaDivergenciaColunas.className = "sgn-alerta-banner sucesso";
        alertaDivergenciaColunas.innerHTML = `✅ <strong>Perfeito:</strong> As ${letrasNotas.length} colunas da planilha correspondem exatamente às ${ativsSIGEduc.length} avaliações do SIGEduc.`;
      } else if (letrasNotas.length > ativsSIGEduc.length) {
        alertaDivergenciaColunas.className = "sgn-alerta-banner aviso";
        alertaDivergenciaColunas.innerHTML = `⚠️ <strong>Atenção:</strong> Planilha tem ${letrasNotas.length} colunas de notas selecionadas, mas o SIGEduc possui ${ativsSIGEduc.length} atividades. As ${ativsSIGEduc.length} primeiras notas serão lançadas.`;
      } else {
        alertaDivergenciaColunas.className = "sgn-alerta-banner info";
        alertaDivergenciaColunas.innerHTML = `ℹ️ <strong>Informativo:</strong> Planilha tem ${letrasNotas.length} notas para ${ativsSIGEduc.length} atividades no SIGEduc. A(s) atividade(s) restante(s) ficará(ão) em branco.`;
      }
    } else {
      alertaDivergenciaColunas.className = "sgn-alerta-banner info";
      alertaDivergenciaColunas.innerHTML = `📋 <strong>${letrasNotas.length} coluna(s) selecionada(s)</strong> no Excel para lançamento.`;
    }

    // Grid de correspondência
    listaMapeamentoColunas.innerHTML = "";
    const totalItens = Math.max(letrasNotas.length, ativsSIGEduc.length);
    for (let idx = 0; idx < totalItens; idx++) {
      const letra = letrasNotas[idx];
      const titExcel = letra ? (mapaTitulosExcel.get(letra) || `Coluna ${letra}`) : "(Sem coluna no Excel)";
      const titSIGEduc = (ativsSIGEduc.length > idx) ? ativsSIGEduc[idx] : (idx < letrasNotas.length ? `Atividade ${idx + 1}` : "(Sem atividade no SIGEduc)");

      const item = document.createElement("div");
      item.className = "sgn-map-item";
      item.innerHTML = `
        <span class="sgn-map-origem">${letra ? `Excel: <strong>${letra}</strong> (${titExcel})` : `<em style="color:#94a3b8;">${titExcel}</em>`}</span>
        <span class="sgn-map-seta">➔</span>
        <span class="sgn-map-destino">${titSIGEduc}</span>
      `;
      listaMapeamentoColunas.appendChild(item);
    }

    boxMapeamentoColunas.style.display = "block";
  }

  function obterFormatoNotaSelecionado() {
    for (const r of radiosFormato) {
      if (r.checked) return r.value;
    }
    return "ponto";
  }

  async function atualizarPrevisualizacao() {
    if (!workbookAtual) {
      cardPreview.style.display = "none";
      if (boxMapeamentoColunas) boxMapeamentoColunas.style.display = "none";
      if (boxAlunosDivergentes) boxAlunosDivergentes.style.display = "none";
      diagMatchInfo.textContent = "Nenhum arquivo";
      btnPreencher.disabled = true;
      return;
    }

    const nomeAba = selectAba.value;
    const colNome = selectColNome.value;
    const colsNotasStr = inputColunasNotas.value.trim();
    if (!colsNotasStr) {
      if (boxMapeamentoColunas) boxMapeamentoColunas.style.display = "none";
      btnPreencher.disabled = true;
      return;
    }

    const letrasNotas = colsNotasStr.split(/[,;\s]+/).map(s => s.trim().toUpperCase()).filter(Boolean);
    const formato = obterFormatoNotaSelecionado();

    renderizarMapeamentoColunas(letrasNotas);

    try {
      const extraidos = window.SgnExcel.extrairDadosNotas(
        workbookAtual,
        nomeAba,
        colNome,
        letrasNotas,
        formato,
        window.XLSX
      );

      dadosAlunosExtraidos = extraidos.alunos;
      cntTotalExcel.textContent = dadosAlunosExtraidos.length;
      diagExcelInfo.textContent = `${txtNomeArquivo.textContent} (${dadosAlunosExtraidos.length} alunos)`;

      // Se temos alunos na tela do SIGEduc, pede ao Content Script o casamento em tempo real
      if (estadoTelaSIGEduc && estadoTelaSIGEduc.qtdAlunosTela > 0 && tabIdAtiva) {
        const nomesExcel = dadosAlunosExtraidos.map(a => a.nome);

        const resPreview = await enviarMensagemSegura("PREVIEW_CASAMENTO", { nomesExcel });
        if (resPreview.sucesso && resPreview.dados) {
          const dados = resPreview.dados;
          renderizarTabelaPreview(
            dados.pares,
            dados.totalTela,
            dados.alunosTelaSemPar || [],
            dados.alunosExcelSemPar || []
          );
          cardPreview.style.display = "block";
          diagMatchInfo.textContent = `${dados.totalCasados} / ${dados.totalTela} casados`;
          btnPreencher.disabled = dados.totalCasados === 0;

          Logger.info(`Casamento de nomes: ${dados.totalCasados} casados de ${dados.totalTela} na tela (${(dados.alunosTelaSemPar || []).length} sem par no SIGEduc, ${(dados.alunosExcelSemPar || []).length} sem par no Excel).`);
        } else {
          // Fallback: exibe alunos do Excel diretamente
          renderizarPreviewApenasExcel(dadosAlunosExtraidos);
          cardPreview.style.display = "block";
          btnPreencher.disabled = false;
        }
      } else {
        // Sem conexão ativa na tela: exibe prévia diretamente a partir do Excel
        renderizarPreviewApenasExcel(dadosAlunosExtraidos);
        cardPreview.style.display = "block";
        diagMatchInfo.textContent = `${dadosAlunosExtraidos.length} na planilha`;
        btnPreencher.disabled = false;
      }
    } catch (err) {
      Logger.aviso(`Erro ao atualizar preview: ${err.message}`);
    }
  }

  function renderizarTabelaPreview(pares, totalTela, alunosTelaSemPar = [], alunosExcelSemPar = []) {
    cntCasados.textContent = pares.length;
    cntSemParTela.textContent = alunosTelaSemPar.length;
    if (cntSemParExcel) {
      cntSemParExcel.textContent = alunosExcelSemPar.length;
    }

    // Painel de estudantes com divergência
    if (boxAlunosDivergentes && listaAlunosDivergentes) {
      const totalDivergentes = alunosTelaSemPar.length + alunosExcelSemPar.length;
      if (totalDivergentes > 0) {
        if (txtQtdDivergentes) txtQtdDivergentes.textContent = totalDivergentes;
        let htmlDiverg = "";
        if (alunosTelaSemPar.length > 0) {
          htmlDiverg += `
            <div class="sgn-diverg-subsecao">
              <div class="sgn-diverg-titulo" style="color: #b45309;">⚠️ Presentes no SIGEduc, ausentes na Planilha (${alunosTelaSemPar.length}):</div>
              <ul class="sgn-diverg-lista">
                ${alunosTelaSemPar.map(nome => `<li><strong>${nome}</strong></li>`).join("")}
              </ul>
            </div>
          `;
        }
        if (alunosExcelSemPar.length > 0) {
          htmlDiverg += `
            <div class="sgn-diverg-subsecao">
              <div class="sgn-diverg-titulo" style="color: #1d4ed8;">ℹ️ Presentes na Planilha, ausentes no SIGEduc (${alunosExcelSemPar.length}):</div>
              <ul class="sgn-diverg-lista">
                ${alunosExcelSemPar.map(nome => `<li><strong>${nome}</strong></li>`).join("")}
              </ul>
            </div>
          `;
        }
        listaAlunosDivergentes.innerHTML = htmlDiverg;
        boxAlunosDivergentes.style.display = "block";
      } else {
        boxAlunosDivergentes.style.display = "none";
      }
    }

    previewTbody.innerHTML = "";

    pares.slice(0, 60).forEach((par) => {
      const tr = document.createElement("tr");
      tr.className = "tr-match";

      const alunoDados = (par.indicePlanilha !== undefined && dadosAlunosExtraidos[par.indicePlanilha])
        ? dadosAlunosExtraidos[par.indicePlanilha]
        : dadosAlunosExtraidos.find(a => window.SgnNomes ? window.SgnNomes.normalizar(a.nome) === window.SgnNomes.normalizar(par.nomeExcel) : a.nome === par.nomeExcel);
      const notasStr = alunoDados ? alunoDados.notas.map(n => n === "" ? "FV" : n).join(" | ") : "-";

      tr.innerHTML = `
        <td><strong>${par.nomeTela}</strong></td>
        <td>${par.nomeExcel}</td>
        <td><code>${notasStr}</code></td>
      `;
      previewTbody.appendChild(tr);
    });
  }

  function renderizarPreviewApenasExcel(alunosExcel) {
    cntCasados.textContent = alunosExcel.length;
    cntSemParTela.textContent = "-";
    if (cntSemParExcel) cntSemParExcel.textContent = "0";
    if (boxAlunosDivergentes) boxAlunosDivergentes.style.display = "none";

    previewTbody.innerHTML = "";
    alunosExcel.slice(0, 60).forEach((aluno) => {
      const tr = document.createElement("tr");
      tr.className = "tr-match";
      const notasStr = aluno.notas.map(n => n === "" ? "FV" : n).join(" | ");

      tr.innerHTML = `
        <td><em style="color:#64748b;">(Aguardando tela de notas)</em></td>
        <td><strong>${aluno.nome}</strong></td>
        <td><code>${notasStr}</code></td>
      `;
      previewTbody.appendChild(tr);
    });
  }

  // =========================================================================
  // 7. Execução do Preenchimento de Notas e Gravação
  // =========================================================================
  async function executarPreenchimento() {
    if (!dadosAlunosExtraidos.length) {
      mostrarMensagem("Nenhum estudante extraído da planilha para preencher.", "erro");
      Logger.aviso("Clique em preencher ignorado: nenhum aluno extraído.");
      return;
    }

    if (!tabIdAtiva) {
      mostrarMensagem("Aba do SIGEduc não conectada.", "erro");
      Logger.erro("Clique em preencher ignorado: nenhuma aba ativa.");
      return;
    }

    btnPreencher.disabled = true;
    mostrarMensagem("Preenchendo notas na página...", "sucesso");
    Logger.info(`Iniciando preenchimento na ${unidadeSelecionada}ª Unidade com ${dadosAlunosExtraidos.length} estudantes...`);

    // 1. Garante que a unidade correta está selecionada
    const resUnidade = await enviarMensagemSegura("GARANTIR_UNIDADE", { unidade: unidadeSelecionada });
    if (resUnidade.sucesso && resUnidade.dados && resUnidade.dados.clicou) {
      Logger.dom(`Aba da ${unidadeSelecionada}ª Unidade clicada. Aguardando recarregamento dos campos...`);
      await new Promise(r => setTimeout(r, 600));
    }

    // 2. Preenche as notas com a cadência selecionada e opção autoFV
    const parsedDelay = selectDelayCadencia ? parseInt(selectDelayCadencia.value, 10) : 150;
    const delayMs = (!isNaN(parsedDelay) && parsedDelay >= 0) ? parsedDelay : 150;
    const autoFV = chkAutoFV ? chkAutoFV.checked : true;

    const resNotas = await enviarMensagemSegura("PREENCHER_NOTAS", {
      dadosAlunosExcel: dadosAlunosExtraidos,
      opcoes: { delayMs, autoFV }
    });

    btnPreencher.disabled = false;

    if (!resNotas.sucesso || !resNotas.dados || !resNotas.dados.sucesso || resNotas.dados.totalPreenchidos === 0) {
      const msgErro = resNotas.dados ? (resNotas.dados.erro || "Nenhum estudante foi preenchido.") : (resNotas.erro || "Falha de comunicação.");
      mostrarMensagem("Erro ao preencher notas: " + msgErro, "erro");
      Logger.erro(`Falha no preenchimento de notas: ${msgErro}`);
      return;
    }

    const info = resNotas.dados;
    if (info.logs && Array.isArray(info.logs)) {
      info.logs.forEach(l => Logger.dom(l));
    }

    let msg = `✅ ${info.totalPreenchidos} estudantes receberam ${info.totalNotasPreenchidas} notas com sucesso!`;
    if (info.discrepanciasCorrigidas && info.discrepanciasCorrigidas > 0) {
      Logger.sucesso(`🛡️ Reconciliação do DOM: ${info.discrepanciasCorrigidas} nota(s) recuperada(s) e confirmada(s) na auditoria.`);
      msg += `\n🛡️ ${info.discrepanciasCorrigidas} nota(s) verificadas e restauradas no DOM.`;
    } else {
      Logger.sucesso("🛡️ Auditoria do DOM: 100% das notas verificadas e confirmadas.");
    }

    // 3. Se auto-gravação com senha estiver ativada
    if (chkAutoGravar.checked) {
      const senha = inputSenha.value.trim();
      if (!senha) {
        mostrarMensagem(msg + "\n⚠️ Senha não informada para gravação automática. Grave manualmente na tela.", "aviso");
        Logger.aviso("Auto-gravar ignorado: senha não digitada.");
        return;
      }

      mostrarMensagem("Submetendo gravação e confirmando senha no SIGEduc...", "sucesso");
      Logger.info("Submetendo gravação com senha no SIGEduc...");

      const resSenha = await enviarMensagemSegura("SUBMETER_SENHA", { senha });
      if (resSenha.sucesso && resSenha.dados && resSenha.dados.sucesso) {
        mostrarMensagem(msg + "\n🎉 Gravação submetida e confirmada com senha no portal!", "sucesso");
        Logger.sucesso("Gravação confirmada com senha no portal SIGEduc!");
      } else {
        const errSenha = resSenha.dados ? resSenha.dados.erro : (resSenha.erro || "Falha ao gravar com senha.");
        mostrarMensagem(msg + "\n⚠️ " + errSenha, "aviso");
        Logger.aviso(`Resultado da gravação: ${errSenha}`);
      }
    } else {
      mostrarMensagem(msg + "\n👉 Revise as notas no navegador e clique em 'Gravar' no SIGEduc.", "sucesso");
    }
  }

  async function executarPreenchimentoFV() {
    if (!tabIdAtiva || !dadosAlunosExtraidos.length) return;

    btnPreencherFV.disabled = true;
    Logger.info(`Iniciando preenchimento de Falta Vinculada (FV) na ${unidadeSelecionada}ª Unidade...`);

    // 1. Garante que a unidade correta está selecionada na tela de FV
    const resUnidade = await enviarMensagemSegura("GARANTIR_UNIDADE", { unidade: unidadeSelecionada });
    if (resUnidade.sucesso && resUnidade.dados && resUnidade.dados.clicou) {
      Logger.dom(`Aba da ${unidadeSelecionada}ª Unidade clicada. Aguardando recarregamento...`);
      await new Promise(r => setTimeout(r, 600));
    }

    const parsedDelay = selectDelayCadencia ? parseInt(selectDelayCadencia.value, 10) : 150;
    const delayMs = (!isNaN(parsedDelay) && parsedDelay >= 0) ? parsedDelay : 150;

    const resFV = await enviarMensagemSegura("PREENCHER_FV", {
      dadosAlunosExcel: dadosAlunosExtraidos,
      opcoes: { delayMs }
    });

    btnPreencherFV.disabled = false;

    if (resFV.sucesso && resFV.dados && resFV.dados.sucesso) {
      mostrarMensagem(`✅ ${resFV.dados.totalMarcados} caixas de Falta Vinculada marcadas com sucesso!`, "sucesso");
      Logger.sucesso(`Falta Vinculada aplicada: ${resFV.dados.totalMarcados} caixas marcadas.`);
    } else {
      const err = resFV.dados ? resFV.dados.erro : (resFV.erro || "Falha");
      mostrarMensagem("Erro ao aplicar Falta Vinculada: " + err, "erro");
      Logger.erro(`Falha ao preencher FV: ${err}`);
    }
  }

  async function executarDownloadModeloExcel() {
    if (!tabIdAtiva) {
      mostrarMensagem("Aba do SIGEduc não conectada.", "erro");
      Logger.erro("Download do modelo cancelado: aba do SIGEduc desconectada.");
      return;
    }

    try {
      btnBaixarModelo.disabled = true;
      btnBaixarModelo.innerHTML = "<span>⏳ Extraindo dados da tela...</span>";
      Logger.info("Solicitando dados da turma aberta no SIGEduc para gerar planilha modelo...");

      const res = await enviarMensagemSegura("OBTER_DADOS_MODELO_EXCEL");
      if (!res.sucesso || !res.dados || !res.dados.sucesso) {
        throw new Error(res.dados ? res.dados.erro : (res.erro || "Falha ao obter dados da turma da página."));
      }

      const dadosTurma = res.dados;
      Logger.excel(`Dados recebidos da página: ${dadosTurma.turma} (${dadosTurma.totalAlunos} estudantes, ${dadosTurma.atividades.length} atividades).`);

      const resultado = window.SgnExcel.gerarPlanilhaModelo(dadosTurma, {
        incluirFormulaTotal: true,
        preservarNotasExistentes: false,
        XLSX_LIB: window.XLSX
      });

      // Dispara download nativo via Blob e <a>
      const blob = new Blob([resultado.arrayBuffer], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = resultado.nomeArquivo;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 2000);

      Logger.sucesso(`Planilha modelo '${resultado.nomeArquivo}' baixada com sucesso (${resultado.totalAlunos} estudantes).`);
      mostrarMensagem(`📥 Planilha modelo '${resultado.nomeArquivo}' baixada com sucesso!\nPreencha as notas no Excel e depois selecione o arquivo aqui.`, "sucesso", 8000);
    } catch (err) {
      Logger.erro(`Falha ao gerar planilha modelo: ${err.message}`);
      mostrarMensagem(`Erro ao gerar planilha modelo: ${err.message}`, "erro");
    } finally {
      btnBaixarModelo.disabled = false;
      btnBaixarModelo.innerHTML = "<span>✨ Baixar Planilha Modelo (.xlsx)</span>";
    }
  }

  // =========================================================================
  // 8. Utilitários e Eventos de UI
  // =========================================================================
  function alternarView(viewId) {
    if (viewId === "view-logs") {
      viewLancamento.style.display = "none";
      viewLogs.style.display = "flex";
      tabNavLancamento.classList.remove("active");
      tabNavLogs.classList.add("active");
      // Ao abrir os logs, limpa o badge de erros
      Logger.errosCount = 0;
      Logger.atualizarBadge();
      logTerminal.scrollTop = logTerminal.scrollHeight;
    } else {
      viewLogs.style.display = "none";
      viewLancamento.style.display = "flex";
      tabNavLogs.classList.remove("active");
      tabNavLancamento.classList.add("active");
    }
  }

  function selecionarUnidadeUI(num) {
    unidadeSelecionada = parseInt(num, 10) || 1;
    const botoes = segmentedUnidade.querySelectorAll(".sgn-seg-btn");
    botoes.forEach((btn) => {
      const u = parseInt(btn.dataset.unidade, 10);
      btn.classList.toggle("active", u === unidadeSelecionada);
    });
  }

  function mostrarMensagem(texto, tipo = "sucesso") {
    msgStatus.textContent = texto;
    msgStatus.className = `sgn-msg-box ${tipo}`;
    msgStatus.style.display = "block";
  }

  function configurarEventosUI() {
    // Navegação entre Abas do Popup
    tabNavLancamento.addEventListener("click", () => alternarView("view-lancamento"));
    tabNavLogs.addEventListener("click", () => alternarView("view-logs"));

    btnRecarregarStatus.addEventListener("click", () => {
      Logger.info("Recarregamento de status solicitado pelo usuário.");
      verificarAbaAtiva();
    });

    // Ações de Diagnóstico
    btnRetestarConexao.addEventListener("click", async () => {
      btnRetestarConexao.disabled = true;
      btnRetestarConexao.textContent = "⏳ Testando...";
      Logger.info("Botão 'Testar Conexão / Reinjetar Script' acionado.");
      await verificarAbaAtiva();
      btnRetestarConexao.disabled = false;
      btnRetestarConexao.textContent = "🔄 Testar Conexão / Reinjetar Script";
    });

    btnRecarregarPaginaAba.addEventListener("click", async () => {
      if (!tabIdAtiva) return;
      Logger.info(`Recarregando aba ${tabIdAtiva}...`);
      try {
        await chrome.tabs.reload(tabIdAtiva);
        definirStatus("Página recarregada. Aguardando inicialização...", "aviso");
        setTimeout(verificarAbaAtiva, 1500);
      } catch (e) {
        Logger.erro("Falha ao recarregar aba: " + e.message);
      }
    });

    btnCopiarLogs.addEventListener("click", async () => {
      const texto = Logger.obterTextoFormatado();
      if (!texto) return;
      try {
        await navigator.clipboard.writeText(texto);
        const original = btnCopiarLogs.textContent;
        btnCopiarLogs.textContent = "✅ Copiado!";
        setTimeout(() => { btnCopiarLogs.textContent = original; }, 2000);
      } catch (err) {
        Logger.erro("Falha ao copiar para área de transferência: " + err.message);
      }
    });

    btnLimparLogs.addEventListener("click", () => Logger.limpar());

    // Filtros de Logs
    filterPills.forEach(pill => {
      pill.addEventListener("click", () => {
        filterPills.forEach(p => p.classList.remove("active"));
        pill.classList.add("active");
        Logger.aplicarFiltro(pill.dataset.filtro);
      });
    });

    // Drag and drop do arquivo
    dropZone.addEventListener("click", () => inputArquivo.click());
    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
      if (e.dataTransfer.files.length) carregarArquivo(e.dataTransfer.files[0]);
    });
    inputArquivo.addEventListener("change", (e) => {
      if (e.target.files.length) carregarArquivo(e.target.files[0]);
    });

    btnRemoverArquivo.addEventListener("click", () => {
      workbookAtual = null;
      dadosAlunosExtraidos = [];
      colunasPlanilhaAtual = [];
      dropZone.style.display = "block";
      boxArquivoInfo.style.display = "none";
      cardPreview.style.display = "none";
      if (boxMapeamentoColunas) boxMapeamentoColunas.style.display = "none";
      if (boxAlunosDivergentes) boxAlunosDivergentes.style.display = "none";
      diagExcelInfo.textContent = "Nenhuma carregada";
      diagMatchInfo.textContent = "0 casados";
      btnPreencher.disabled = true;
      inputArquivo.value = "";
      if (boxGerarModelo && estadoTelaSIGEduc && estadoTelaSIGEduc.tela === "notas") {
        boxGerarModelo.style.display = "flex";
      }
      Logger.info("Arquivo Excel descarregado.");
    });

    selectAba.addEventListener("change", atualizarConfiguracaoAba);
    selectColNome.addEventListener("change", atualizarPrevisualizacao);
    inputColunasNotas.addEventListener("input", atualizarPrevisualizacao);
    radiosFormato.forEach(r => r.addEventListener("change", atualizarPrevisualizacao));

    // Botões de unidade
    segmentedUnidade.addEventListener("click", async (e) => {
      const btn = e.target.closest(".sgn-seg-btn");
      if (!btn) return;
      selecionarUnidadeUI(btn.dataset.unidade);
      Logger.info(`Unidade ${unidadeSelecionada} selecionada pelo usuário.`);
      if (tabIdAtiva) {
        await enviarMensagemSegura("GARANTIR_UNIDADE", { unidade: unidadeSelecionada });
      }
    });

    // Checkbox de senha
    chkAutoGravar.addEventListener("change", () => {
      boxSenha.style.display = chkAutoGravar.checked ? "block" : "none";
    });

    btnPreencher.addEventListener("click", executarPreenchimento);
    btnPreencherFV.addEventListener("click", executarPreenchimentoFV);

    if (btnBaixarModelo) {
      btnBaixarModelo.addEventListener("click", executarDownloadModeloExcel);
    }
  }

  // Inicializa quando o DOM do popup estiver pronto
  document.addEventListener("DOMContentLoaded", inicializar);
})();
