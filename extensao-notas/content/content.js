/*
 * Content Script do SIGEduc Auto - Lançador de Notas
 * Executa diretamente no contexto do portal SIGEduc Bahia (https://sigeduc.educacao.ba.gov.br/*)
 */

(function (root) {
  "use strict";

  const VERSAO_CONTENT = "1.0.5";
  if (typeof console !== "undefined" && console.log) {
    console.log(`🎓 SIGEduc Auto: Content Script v${VERSAO_CONTENT} carregado.`);
  }

  // =========================================================================
  // 1. Toast / Notificações Flutuantes na Página
  // =========================================================================
  function exibirToast(titulo, mensagem, tipo = "sucesso", duracaoMs = 6000) {
    if (typeof document === "undefined" || !document.body) return;
    let toast = document.getElementById("sgn-floating-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "sgn-floating-toast";
      document.body.appendChild(toast);
    }

    const icones = {
      sucesso: "✅",
      aviso: "⚠️",
      erro: "❌",
      info: "ℹ️"
    };

    toast.className = `sgn-${tipo}`;
    toast.innerHTML = `
      <div class="sgn-toast-icon">${icones[tipo] || "ℹ️"}</div>
      <div class="sgn-toast-body">
        <div class="sgn-toast-title">${titulo}</div>
        <div class="sgn-toast-msg">${mensagem}</div>
      </div>
      <button class="sgn-toast-close" title="Fechar">&times;</button>
    `;

    const btnClose = toast.querySelector(".sgn-toast-close");
    if (btnClose) {
      btnClose.onclick = () => {
        toast.style.display = "none";
      };
    }

    toast.style.display = "flex";

    if (toast.__timeout) clearTimeout(toast.__timeout);
    if (duracaoMs > 0) {
      toast.__timeout = setTimeout(() => {
        toast.style.display = "none";
      }, duracaoMs);
    }
  }

  // =========================================================================
  // 2. Limpeza e Sanitização de Nomes
  // =========================================================================
  function limparNomeAluno(txt) {
    if (!txt) return "";
    let limpo = String(txt)
      // Remove aspas envolventes
      .replace(/^['"]+|['"]+$/g, "")
      // Remove emojis e simbolos unicode (ex: ♿ cadeirante, simbolos de acessibilidade)
      .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}]/gu, " ")
      // Remove números ordinais ou de chamada no início (ex: "1 ", "01 - ", "1. ")
      .replace(/^\s*\d+[\s\.\-]+/g, "");

    // Remove sucessivos sufixos entre parênteses, colchetes ou chaves no fim (ex: "(TRANSFERIDO)", "[CANCELADA]")
    let anterior = "";
    while (limpo !== anterior) {
      anterior = limpo;
      limpo = limpo.replace(/\s*[\(\[\{][^\)\]\}]*[\)\]\}]\s*$/g, "").trim();
    }

    return limpo
      // Remove sufixos de situação escolar com hífen, travessão, dois pontos ou barra (ex: "- TRANSFERIDO", ": CANCELADO", "- EVADIDO")
      .replace(/\s*[\-\–\—\:\/]\s*(?:TRANSFERID[OA]|CANCELAD[OA]|CANCELAMENTO|DESISTENTE|DESISTENCIA|REMANEJAD[OA]|REMANEJAMENTO|INATIV[OA]|ABANDONO|FALECID[OA]|EVADID[OA]|EVASAO|RECLASSIFICAD[OA]|RECLASSIFICACAO).*$/gi, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  // =========================================================================
  // 3. Detecção de Tela e Elementos no SIGEduc
  // =========================================================================
  function normalizarTextoSimples(str) {
    if (!str) return "";
    return String(str)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toUpperCase()
      .replace(/[\u00A0\s]+/g, " ")
      .trim();
  }

  function eTabelaCalendario(tabela) {
    if (!tabela) return false;
    try {
      const texto = normalizarTextoSimples(tabela.innerText || "");
      const meses = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"];
      const temMes = meses.some(m => texto.includes(m));

      // Verifica cabeçalhos de dias da semana (tanto DOM/SEG quanto D/S/T/Q)
      const temDiasSemanaAbrev = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SAB"].filter(d => texto.includes(d)).length >= 3;
      
      const celulasCabecalho = Array.from(tabela.querySelectorAll("th, tr:first-child td, tr:nth-child(2) td")).map(el => (el.innerText || "").trim().toUpperCase());
      const temDiasSemanaLetra = ["D", "S", "T", "Q"].filter(letra => celulasCabecalho.includes(letra)).length >= 3;

      const links = tabela.querySelectorAll("a");
      const numeros = Array.from(tabela.querySelectorAll("a, td, span")).filter(el => {
        const n = parseInt((el.innerText || "").trim(), 10);
        return !isNaN(n) && n >= 1 && n <= 31;
      });

      if ((temMes || temDiasSemanaAbrev || temDiasSemanaLetra) && (links.length >= 1 || numeros.length >= 4)) {
        return true;
      }
    } catch (e) {}
    return false;
  }

  function detectarTela() {
    const textoDoc = normalizarTextoSimples(document.body ? document.body.innerText : "");
    const url = (typeof window !== "undefined" && window.location ? window.location.href : "").toLowerCase();

    // 1. Tela de Falta Vinculada
    if (
      textoDoc.includes("VERIFICAR AVALIACOES NAO REALIZADAS") ||
      textoDoc.includes("VERIFICAR AVALIACOES") ||
      textoDoc.includes("FALTA VINCULADA")
    ) {
      return "fv";
    }

    // 2. Tela de Lançamento de Notas
    if (
      textoDoc.includes("LANCAR NOTAS PARA AVALIACOES") ||
      textoDoc.includes("LANCAR NOTAS") ||
      document.querySelector("input.avaliacao, input[id*=':av__'], input[id*=':av'], table[id*='formulario:result'], #formulario\\:result")
    ) {
      return "notas";
    }

    // 3. Tela de Frequência do Dia (Chamada / Tabela de Alunos)
    if (
      document.querySelector("#tableAlunos") ||
      (document.querySelector("table") && (textoDoc.includes("REGISTRO DE FREQUENCIA") || textoDoc.includes("LANCAR FREQUENCIA") || textoDoc.includes("FREQUENCIA DO DIA")) && document.querySelector("input[type='checkbox']"))
    ) {
      return "frequencia_dia";
    }

    // 4. Calendário Mensal de Frequência
    if (
      textoDoc.includes("CALENDARIO") ||
      textoDoc.includes("PRESENCAS LANCADAS") ||
      textoDoc.includes("AULAS DE REPOSICAO") ||
      textoDoc.includes("INTERRUPCAO ESCOLAR") ||
      textoDoc.includes("AULA CANCELADA") ||
      textoDoc.includes("FALTA PROFESSOR") ||
      (document.querySelectorAll("table").length > 0 && Array.from(document.querySelectorAll("table")).some(t => eTabelaCalendario(t)))
    ) {
      return "frequencia_calendario";
    }

    // 5. Painel do Professor / Lista de Turmas
    if (
      textoDoc.includes("MINHAS TURMAS") ||
      textoDoc.includes("TURMAS REGULARES") ||
      document.querySelector("img[src*='notas_lancar']")
    ) {
      return "turmas";
    }

    return "outra";
  }

  function elementoVisivel(el) {
    if (!el) return false;
    if (typeof window !== "undefined" && window.document && el.offsetParent !== undefined) {
      if (el.offsetParent !== null) return true;
      if (el.style && (el.style.display === "none" || el.style.visibility === "hidden")) return false;
      const isTestEnv = (typeof process !== "undefined" && process.versions && process.versions.node) ||
                        (typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent));
      if (isTestEnv) return true;
      return false;
    }
    return true;
  }

  function obterTabelaAtiva() {
    // 1. Seletores diretos conhecidos do JSF/RichFaces
    const seletores = [
      "table[id='formulario:result']",
      "table[id*=':result']:not([id*='resultj']):not([id*='resultadoFinal'])",
      "#formulario\\:result",
      "table[id='formulario:resultj_id_1']",
      "table[id='formulario:resultj_id_2']",
      "table[id='formulario:resultadoFinal']",
      "#tableAlunos",
      "table.rich-table",
      "table.listagem"
    ];

    for (const sel of seletores) {
      const el = document.querySelector(sel);
      if (el && elementoVisivel(el)) return el;
    }

    // 2. Procura tabela que contenha inputs de avaliação visíveis
    const inputs = document.querySelectorAll("input.avaliacao, input[id*=':av__'], input[id*=':av'], input[name*='avaliacao']");
    for (const inp of inputs) {
      const tabela = inp.closest("table");
      if (tabela && elementoVisivel(tabela)) return tabela;
    }

    // 3. Fallback: Procura qualquer tabela cujo cabeçalho contenha 'ESTUDANTE' ou 'ALUNO'
    const todasTabelas = Array.from(document.querySelectorAll("table"));
    for (const tab of todasTabelas) {
      if (!elementoVisivel(tab)) continue;
      const textoTh = (tab.querySelector("thead") || tab).innerText.toUpperCase();
      if ((textoTh.includes("ESTUDANTE") || textoTh.includes("ALUNO")) && tab.querySelectorAll("tr").length > 2) {
        return tab;
      }
    }

    return null;
  }

  function extrairCabecalhosTabela(tabela) {
    if (!tabela) return [];
    const thead = tabela.querySelector("thead");
    const trCabecalho = thead ? thead.querySelector("tr") : tabela.querySelector("tr");
    const ths = trCabecalho ? Array.from(trCabecalho.querySelectorAll("th, td")) : [];
    const headers = [];
    ths.forEach((th, idx) => {
      const txt = (th.innerText || th.textContent || "").trim().replace(/\s+/g, " ");
      if (txt) {
        headers.push({ indice: idx, texto: txt });
      }
    });
    return headers;
  }

  function extrairNomeDaLinha(linha) {
    if (!linha) return "";

    // 1. Links <a> dentro da linha (no SIGEduc, o nome do estudante normalmente é um link para a ficha)
    const links = linha.querySelectorAll("a");
    for (const a of links) {
      const txt = limparNomeAluno(a.innerText || "");
      const partes = txt.split(/\s+/);
      if (partes.length >= 2 && txt.length >= 5) {
        const up = txt.toUpperCase();
        const ignorar = ["VOLTAR", "EDITAR", "EXCLUIR", "SALVAR", "GRAVAR", "DETALHES", "IMPRIMIR", "HISTÓRICO", "HISTORICO"];
        if (!ignorar.some(term => up.includes(term))) {
          return txt;
        }
      }
    }

    // 2. Células <td> de texto puro
    const tds = linha.querySelectorAll("td");
    for (const td of tds) {
      if (td.querySelector("input, select, button, textarea")) continue;
      const txt = limparNomeAluno(td.innerText || "");
      const partes = txt.split(/\s+/);
      if (partes.length >= 2 && txt.length >= 5) {
        const up = txt.toUpperCase();
        if (!up.includes("MATRÍCULA") && !up.includes("MATRICULA") && !up.includes("SITUAÇÃO") && !up.includes("SITUACAO") && !up.includes("MÉDIA") && !up.includes("MEDIA")) {
          return txt;
        }
      }
    }

    return "";
  }

  function ehInputAvaliacao(inp) {
    if (!inp) return false;
    const id = (inp.id || "").toLowerCase();
    const name = (inp.name || "").toLowerCase();
    const cls = (inp.className || "").toLowerCase();

    // Exclui campos que são comprovadamente recuperação ou total/média final da unidade
    if (id.includes("nurec") || name.includes("nurec") || cls.includes("recuperacao") || cls.includes("nurec")) {
      return false;
    }
    if (id.includes("nu__") || id.includes(":nu_") || name.includes("nu__") || name.includes(":nu_") || cls.includes("total") || cls.includes("media") || cls.includes("notafinal") || cls.includes("notaunidade")) {
      return false;
    }
    if (id.includes("falta") || name.includes("falta") || cls.includes("falta")) {
      return false;
    }
    return true;
  }

  function ehInputVisivelNaLinha(inp) {
    if (!inp) return false;
    if (inp.type === "hidden" || inp.hidden) return false;
    if (inp.style && (inp.style.display === "none" || inp.style.visibility === "hidden")) return false;
    return true;
  }

  function extrairInputsAvaliacaoLinha(linha) {
    if (!linha) return [];
    // 1. Todos os inputs de texto na linha que não são campos especiais (recuperação, totais, faltas)
    const inputsTodos = Array.from(
      linha.querySelectorAll("input[type='text'], input:not([type='hidden']):not([type='checkbox']):not([type='radio']):not([type='password']):not([type='submit']):not([type='button']):not([type='image']):not([type='file']):not([type='reset'])")
    ).filter(i => ehInputVisivelNaLinha(i) && ehInputAvaliacao(i));

    // 2. Inputs com seletores explícitos de avaliação do SIGEduc (:av__, .avaliacao)
    const inputsAv = Array.from(
      linha.querySelectorAll("input.avaliacao, input[id*=':av__'], input[id*=':av'], input[name*='avaliacao'], input[name*=':av']")
    ).filter(i => ehInputVisivelNaLinha(i) && ehInputAvaliacao(i));

    // Seleciona o conjunto mais abrangente para garantir que nenhuma avaliação fique de fora
    let escolhidos = (inputsTodos.length >= inputsAv.length && inputsTodos.length > 0) ? inputsTodos : inputsAv;

    // Garante ordenação esquerda-para-direita estritamente de acordo com a posição no DOM
    escolhidos.sort((a, b) => {
      if (a === b) return 0;
      if (typeof a.compareDocumentPosition === "function") {
        const pos = a.compareDocumentPosition(b);
        if (pos & 4) return -1; // b segue a
        if (pos & 2) return 1;  // b precede a
      }
      return 0;
    });

    return escolhidos;
  }

  function extrairAlunosDaTela() {
    const tabela = obterTabelaAtiva();
    if (!tabela) return { alunos: [], cabecalhos: [], atividadesSIGEduc: [] };

    const cabecalhos = extrairCabecalhosTabela(tabela);

    // Mapeamento dos cabeçalhos por índice de coluna na linha de cabeçalho
    const thead = tabela.querySelector("thead");
    const trCabecalho = thead ? thead.querySelector("tr") : tabela.querySelector("tr");
    const thsLinha = trCabecalho ? Array.from(trCabecalho.querySelectorAll("th, td")) : [];

    let linhas = Array.from(tabela.querySelectorAll("tbody tr"));
    if (!linhas.length) {
      linhas = Array.from(tabela.querySelectorAll("tr")).slice(1);
    }

    const resultado = [];
    let atividadesSIGEduc = [];

    linhas.forEach((linha, idx) => {
      if (!elementoVisivel(linha)) return; // ignora invisíveis
      const nome = extrairNomeDaLinha(linha);
      if (!nome) return;

      // Inputs de notas dessa linha
      const inputsFinais = extrairInputsAvaliacaoLinha(linha);

      // Se ainda não descobriu os títulos das atividades e temos inputs nesta linha
      if (atividadesSIGEduc.length === 0 && inputsFinais.length > 0) {
        atividadesSIGEduc = inputsFinais.map((inp, iPos) => {
          const td = inp.closest("td") || inp.closest("th");
          const cellIndex = td ? td.cellIndex : -1;
          if (cellIndex >= 0 && thsLinha[cellIndex]) {
            const txt = (thsLinha[cellIndex].innerText || thsLinha[cellIndex].textContent || "").trim().replace(/\s+/g, " ");
            if (txt) return txt;
          }
          return `Atividade ${iPos + 1}`;
        });
      }

      // Checkboxes de falta dessa linha (caso tela de FV)
      const checkboxes = Array.from(linha.querySelectorAll("input[type='checkbox']")).filter(c => elementoVisivel(c));

      // Linhas informativas sem nenhum campo editável são descartadas
      if (inputsFinais.length === 0 && checkboxes.length === 0) return;

      resultado.push({
        indiceLinha: idx,
        nome: nome,
        linhaEl: linha,
        qtdInputs: inputsFinais.length,
        inputs: inputsFinais,
        qtdCheckboxes: checkboxes.length,
        checkboxes: checkboxes
      });
    });

    return { alunos: resultado, cabecalhos, atividadesSIGEduc };
  }

  function detectarUnidadeAtiva() {
    const tabs = Array.from(document.querySelectorAll("a, td, div, span, button, li"));
    for (let u = 1; u <= 4; u++) {
      const reg = new RegExp(`\\b${u}[ªºa]?\\s*unidade\\b`, "i");
      for (const el of tabs) {
        if (el.children.length > 2) continue;
        const txt = (el.innerText || "").trim();
        if (reg.test(txt)) {
          // Verifica se está visualmente ativa
          let cur = el;
          let ativa = false;
          for (let i = 0; i < 4 && cur; i++) {
            const cls = (cur.className || "").toLowerCase();
            if (
              cls.includes("rich-tab-active") ||
              cls.includes("dr-tbpnl-tb-act") ||
              cls.includes("tab-active") ||
              cls.includes("active") ||
              cur.getAttribute("aria-selected") === "true"
            ) {
              ativa = true;
              break;
            }
            try {
              const st = window.getComputedStyle(cur);
              if (st.color === "rgb(255, 255, 255)" || st.color === "#ffffff") {
                ativa = true;
                break;
              }
            } catch (e) {}
            cur = cur.parentElement;
          }
          if (ativa) return u;
        }
      }
    }
    return 1; // Padrão
  }

  function extrairMetadadosTela() {
    const textoDoc = (document.body ? document.body.innerText : "");
    let escola = "";
    let turma = "";
    let componente = "";

    // 1. Regex de busca nos textos da página
    const matchEscola = textoDoc.match(/Escola:\s*([^\n\r]+)/i);
    if (matchEscola) escola = matchEscola[1].trim();

    const matchTurma = textoDoc.match(/Turma:\s*([^\n\r]+)/i);
    if (matchTurma) turma = matchTurma[1].trim();

    const matchComp = textoDoc.match(/Componente(?:\s*Curricular)?:\s*([^\n\r]+)/i);
    if (matchComp) componente = matchComp[1].trim();

    // 2. Seletor por células específicas se ainda estiverem vazios
    if (!turma || !componente || !escola) {
      const elementos = Array.from(document.querySelectorAll("td, th, span, div, p"));
      for (const el of elementos) {
        if (el.children.length > 2) continue;
        const txt = (el.innerText || "").trim();
        if (!escola && /^Escola:\s*(.+)$/im.test(txt)) {
          escola = txt.match(/^Escola:\s*(.+)$/im)[1].trim();
        }
        if (!turma && /^Turma:\s*(.+)$/im.test(txt)) {
          turma = txt.match(/^Turma:\s*(.+)$/im)[1].trim();
        }
        if (!componente && /^Componente(?:\s*Curricular)?:\s*(.+)$/im.test(txt)) {
          componente = txt.match(/^Componente(?:\s*Curricular)?:\s*(.+)$/im)[1].trim();
        }
      }
    }

    // Se a turma contiver o código abreviado (ex: "... - SEGUMAT1SA / MATUTINO"), extrai o código
    let codigoTurma = turma;
    const matchCod = turma.match(/-\s*([A-Z0-9]+)\s*\//i) || turma.match(/-\s*([A-Z0-9]+)$/i);
    if (matchCod) {
      codigoTurma = matchCod[1].trim();
    } else if (turma.length > 28) {
      codigoTurma = turma.slice(0, 28).trim();
    }

    return {
      escola,
      turmaCompleta: turma,
      turma: codigoTurma || turma || "Turma",
      componente,
      unidade: detectarUnidadeAtiva()
    };
  }

  // =========================================================================
  // 4. Comutação de Unidade (RichFaces Tabs)
  // =========================================================================
  function garantirUnidadeAtiva(numUnidade) {
    if (!numUnidade) return { sucesso: true, jaAtiva: true };
    const alvoNum = parseInt(numUnidade, 10);
    const atual = detectarUnidadeAtiva();
    if (atual === alvoNum) {
      return { sucesso: true, jaAtiva: true };
    }

    const candidatos = Array.from(document.querySelectorAll("a, td, div, span, button, li"));
    const regexUnidade = new RegExp(`^\\s*${alvoNum}[ªºa]?\\s*unidade\\b`, "i");
    const regexGeral = new RegExp(`\\b${alvoNum}[ªºa]?\\s*unidade\\b`, "i");

    let tabElement = null;
    for (const el of candidatos) {
      if (el.children.length > 2) continue;
      const txt = (el.innerText || el.textContent || "").trim();
      if (regexUnidade.test(txt) || regexGeral.test(txt)) {
        tabElement = el;
        break;
      }
    }

    if (!tabElement) {
      const idMap = { 1: "tab1", 2: "tab1j_id_1", 3: "tab1j_id_2", 4: "resultadoFinal" };
      const alvoId = idMap[alvoNum];
      if (alvoId) {
        tabElement = document.querySelector(`a[href*='${alvoId}'], [id*='${alvoId}']`);
      }
    }

    if (tabElement) {
      const clicavel = tabElement.tagName === "A" || tabElement.tagName === "BUTTON"
        ? tabElement
        : (tabElement.querySelector("a, button") || tabElement);

      clicavel.scrollIntoView({ block: "center", inline: "center" });
      clicavel.click();
      return { sucesso: true, jaAtiva: false, clicou: true };
    }

    return { sucesso: false, erro: `Aba da ${alvoNum}ª Unidade não encontrada no DOM.` };
  }

  // =========================================================================
  // 5. Preenchimento de Notas com Eventos DOM Reais
  // =========================================================================
  function dispararEventosInput(input) {
    if (!input) return;
    try {
      input.dispatchEvent(new Event("focus", { bubbles: true }));
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      input.dispatchEvent(new Event("blur", { bubbles: true }));
    } catch (e) {}
  }

  function aplicarValorNoInput(inp, val) {
    if (!inp) return false;
    try {
      if (inp.disabled || inp.readOnly || (inp.classList && inp.classList.contains("noEdit"))) {
        return false;
      }

      const valorFormatado = (val !== "" && val !== null && val !== undefined) ? String(val).trim() : "";

      // Atualiza tanto a propriedade viva quanto o atributo HTML para serialização correta
      inp.value = valorFormatado;
      try {
        inp.setAttribute("value", valorFormatado);
      } catch (e) {}

      dispararEventosInput(inp);

      if (valorFormatado !== "") {
        if (inp.classList) {
          inp.classList.remove("sgn-aviso");
          inp.classList.add("sgn-preenchido");
        }
      } else {
        if (inp.classList) {
          inp.classList.remove("sgn-preenchido", "sgn-aviso");
        }
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  function encontrarLinhaAlunoLive(tabela, nomeAluno, sgnNomes) {
    if (!tabela || !nomeAluno) return null;
    const linhas = Array.from(tabela.querySelectorAll("tbody tr, tr"));
    for (const tr of linhas) {
      const nomeNaLinha = extrairNomeDaLinha(tr);
      if (nomeNaLinha) {
        if (sgnNomes && typeof sgnNomes.nomesSaoIguais === "function") {
          if (sgnNomes.nomesSaoIguais(nomeNaLinha, nomeAluno)) return tr;
        } else if (nomeNaLinha.toUpperCase() === nomeAluno.toUpperCase()) {
          return tr;
        }
      }
    }
    return null;
  }

  function dispararRecalculoLinha(linhaEl, notasAplicadas) {
    if (!linhaEl) return;

    const soma = notasAplicadas.reduce((acc, curr) => {
      const num = parseFloat(String(curr.val).replace(",", "."));
      return acc + (isNaN(num) ? 0 : num);
    }, 0);
    const usouVirgula = notasAplicadas.some(n => String(n.val).includes(","));
    const totalFormatado = usouVirgula ? soma.toFixed(1).replace(".", ",") : soma.toFixed(1);

    // Procura input de total da unidade (:nu__, notaUnidade, etc.)
    const inputTotal = linhaEl.querySelector(
      "input[id*=':nu__'], input[id*='nu__'], input.notaUnidade, input[name*=':nu__'], input[name*='nu__'], input.total, input[id*='total'], input[id*='media']"
    );

    if (inputTotal) {
      inputTotal.value = totalFormatado;
      try { inputTotal.setAttribute("value", totalFormatado); } catch (e) {}
      inputTotal.dispatchEvent(new Event("input", { bubbles: true }));
      inputTotal.dispatchEvent(new Event("change", { bubbles: true }));
      if (inputTotal.classList) {
        inputTotal.classList.add("sgn-recalculado");
      }
    }

    // Dispara eventos na linha para manipuladores do RichFaces
    try {
      linhaEl.dispatchEvent(new Event("change", { bubbles: true }));
      linhaEl.dispatchEvent(new Event("recalcular", { bubbles: true }));
    } catch (e) {}

    if (typeof window !== "undefined") {
      if (typeof window.calculaNota === "function") {
        try { window.calculaNota(linhaEl); } catch (e) {}
      }
      if (typeof window.recalcularTotal === "function") {
        try { window.recalcularTotal(linhaEl); } catch (e) {}
      }
    }
  }

  async function preencherNotasNaTela(dadosAlunosExcel, opcoes = {}) {
    if (!dadosAlunosExcel || !Array.isArray(dadosAlunosExcel) || !dadosAlunosExcel.length) {
      return { sucesso: false, erro: "Dados dos estudantes da planilha não foram fornecidos ou estão vazios." };
    }

    let delayMs = 150;
    if (opcoes && opcoes.delayMs !== undefined && opcoes.delayMs !== null) {
      const parsed = parseInt(opcoes.delayMs, 10);
      if (!isNaN(parsed) && parsed >= 0) {
        delayMs = parsed;
      }
    }
    const autoFV = (opcoes && opcoes.autoFV !== undefined) ? !!opcoes.autoFV : false;

    const tabela = obterTabelaAtiva();
    if (!tabela) {
      return { sucesso: false, erro: "Tabela de notas do SIGEduc não foi localizada na página ativa." };
    }

    const { alunos: alunosTela } = extrairAlunosDaTela();
    if (!alunosTela.length) {
      return { sucesso: false, erro: "Nenhuma linha de estudante identificada na tabela ativa." };
    }

    const sgnNomes = (typeof window !== "undefined" && window.SgnNomes) ||
      (typeof SgnNomes !== "undefined" ? SgnNomes : null) ||
      (typeof require !== "undefined" ? require("../lib/nomes.js") : null);

    if (!sgnNomes) {
      return { sucesso: false, erro: "Biblioteca de correspondência de nomes (nomes.js) não está carregada." };
    }

    const nomesTela = alunosTela.map(a => a.nome);
    const nomesPlanilha = dadosAlunosExcel.map(a => a.nome);

    // Utiliza a biblioteca nomes.js para casar sem falsos positivos
    const { pares, conflitos } = sgnNomes.casarListas(nomesTela, nomesPlanilha);

    if (!pares || pares.size === 0) {
      exibirToast(
        "Nenhum Estudante Casado",
        "Nenhum estudante da planilha correspondeu aos nomes na tela do SIGEduc. Verifique a turma e a aba.",
        "aviso",
        7000
      );
      return {
        sucesso: false,
        erro: "Nenhum estudante da planilha correspondeu aos estudantes exibidos na página do SIGEduc. Verifique se a turma e a aba da planilha selecionadas coincidem com a turma aberta.",
        totalPreenchidos: 0,
        totalNotasPreenchidas: 0,
        totalAlunosTela: alunosTela.length,
        totalAlunosExcel: dadosAlunosExcel.length,
        conflitos,
        detalhes: [],
        logs: [`Nenhum dos ${dadosAlunosExcel.length} estudantes da planilha casou com os ${alunosTela.length} estudantes na tela.`]
      };
    }

    let totalPreenchidos = 0;
    let totalNotasPreenchidas = 0;
    const detalhesPreenchimento = [];
    const logsExecucao = [];

    logsExecucao.push(`[PASSO 1] Preenchendo notas com cadência assíncrona (${delayMs}ms): ${pares.size} estudantes casados.`);

    // =========================================================================
    // PASSO 1: Preenchimento Sequencial Determinístico
    // =========================================================================
    for (let iTela = 0; iTela < alunosTela.length; iTela++) {
      const itemTela = alunosTela[iTela];
      const match = pares.get(iTela);
      if (!match) {
        if (itemTela.linhaEl && itemTela.linhaEl.classList) {
          itemTela.linhaEl.classList.remove("sgn-linha-casada");
          itemTela.linhaEl.classList.add("sgn-linha-sem-par");
        }
        detalhesPreenchimento.push({
          nomeTela: itemTela.nome,
          nomeExcel: null,
          status: "sem_par",
          notas: []
        });
        continue;
      }

      const itemExcel = dadosAlunosExcel[match.indicePlanilha];
      
      // Obtém linha viva no DOM caso tenha ocorrido re-render
      let linhaAtiva = (itemTela.linhaEl && itemTela.linhaEl.isConnected)
        ? itemTela.linhaEl
        : (encontrarLinhaAlunoLive(tabela, itemTela.nome, sgnNomes) || itemTela.linhaEl);

      if (linhaAtiva && linhaAtiva.classList) {
        linhaAtiva.classList.remove("sgn-linha-sem-par");
        linhaAtiva.classList.add("sgn-linha-casada");
      }

      const notasParaPreencher = itemExcel.notas || [];
      let inputsLinha = extrairInputsAvaliacaoLinha(linhaAtiva);
      if (!inputsLinha.length && itemTela.inputs) {
        inputsLinha = itemTela.inputs;
      }

      const qtdCols = Math.min(inputsLinha.length, notasParaPreencher.length);
      const notasAplicadas = [];

      for (let c = 0; c < qtdCols; c++) {
        const inp = inputsLinha[c];
        const val = notasParaPreencher[c];

        if (inp.disabled || inp.readOnly || (inp.classList && inp.classList.contains("noEdit"))) {
          if (inp.classList) inp.classList.add("sgn-aviso");
          const valExistente = (inp.value || "").trim();
          notasAplicadas.push({ col: c + 1, val: valExistente, status: "bloqueado", temValor: valExistente !== "" });
          continue;
        }

        try {
          aplicarValorNoInput(inp, val);
          if (val !== "" && val !== null && val !== undefined) {
            notasAplicadas.push({ col: c + 1, val: val, status: "preenchido", temValor: true });
            totalNotasPreenchidas++;
          } else {
            notasAplicadas.push({ col: c + 1, val: "", status: "em_branco", temValor: false });
          }

          if (delayMs > 0) {
            await new Promise(r => setTimeout(r, delayMs));
          }
        } catch (eInput) {
          logsExecucao.push(`Erro no input col ${c + 1} do aluno ${itemTela.nome}: ${eInput.message}`);
        }
      }

      // Checkboxes de falta (se tela de FV ou autoFV ativo)
      if (autoFV && linhaAtiva) {
        const checkboxes = Array.from(linhaAtiva.querySelectorAll("input[type='checkbox']")).filter(c => !c.disabled);
        const flagsFv = itemExcel.fv || [];
        for (let idx = 0; idx < checkboxes.length; idx++) {
          const chk = checkboxes[idx];
          let idxAtividade = -1;
          const idOuName = (chk.id || chk.name || "");
          const matchNum = idOuName.match(/(?:fv|av)[_:]+(\d+)/i);
          if (matchNum) {
            idxAtividade = parseInt(matchNum[1], 10) - 1;
          } else {
            idxAtividade = idx;
          }

          const deveMarcar = idxAtividade < flagsFv.length ? flagsFv[idxAtividade] : false;
          if (deveMarcar && !chk.checked) {
            try { chk.focus(); chk.click(); } catch (e) {}
            if (!chk.checked) {
              chk.checked = true;
              try {
                chk.dispatchEvent(new Event("input", { bubbles: true }));
                chk.dispatchEvent(new Event("change", { bubbles: true }));
              } catch (e) {}
            }
          } else if (!deveMarcar && chk.checked) {
            try { chk.focus(); chk.click(); } catch (e) {}
            if (chk.checked) {
              chk.checked = false;
              try {
                chk.dispatchEvent(new Event("input", { bubbles: true }));
                chk.dispatchEvent(new Event("change", { bubbles: true }));
              } catch (e) {}
            }
          }
        }
      }

      // Inspeciona inputs extras existentes na linha
      for (let c = qtdCols; c < inputsLinha.length; c++) {
        const inpExtra = inputsLinha[c];
        const valExistente = (inpExtra.value || "").trim();
        if (valExistente !== "") {
          notasAplicadas.push({ col: c + 1, val: valExistente, status: "existente", temValor: true });
        } else {
          notasAplicadas.push({ col: c + 1, val: "", status: "em_branco", temValor: false });
        }
      }

      // Recálculo da linha se todas as avaliações estiverem completas
      const todasPreenchidas = notasAplicadas.length > 0 &&
        notasAplicadas.length === inputsLinha.length &&
        notasAplicadas.every(n => (n.status === "preenchido" || n.status === "bloqueado" || n.status === "existente") && n.val !== "" && n.val !== null && n.val !== undefined);

      if (todasPreenchidas) {
        dispararRecalculoLinha(linhaAtiva, notasAplicadas);
      } else if (linhaAtiva) {
        const inputTotal = linhaAtiva.querySelector(
          "input[id*=':nu__'], input[id*='nu__'], input.notaUnidade, input[name*=':nu__'], input[name*='nu__'], input.total, input[id*='total'], input[id*='media']"
        );
        if (inputTotal) {
          inputTotal.value = "";
          try { inputTotal.setAttribute("value", ""); } catch (e) {}
          inputTotal.dispatchEvent(new Event("input", { bubbles: true }));
          inputTotal.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }

      totalPreenchidos++;
      detalhesPreenchimento.push({
        nomeTela: itemTela.nome,
        nomeExcel: itemExcel.nome,
        nivel: match.nivel,
        status: "ok",
        notas: notasAplicadas
      });

      // Micro-pausa entre alunos para estabilidade do navegador e servidor
      const pausaInterAluno = Math.min(30, Math.floor(delayMs / 3));
      if (pausaInterAluno > 0) {
        await new Promise(r => setTimeout(r, pausaInterAluno));
      }
    }

    // =========================================================================
    // PASSO 2: Verificação e Reconciliação Automática no DOM Vivo
    // Impede que RichFaces AJAX ou colisões assíncronas apaguem qualquer nota
    // =========================================================================
    const pausaSettle = Math.max(250, delayMs * 2);
    logsExecucao.push(`[PASSO 2] Auditoria do DOM em tempo real após estabilização (${pausaSettle}ms)...`);
    await new Promise(r => setTimeout(r, pausaSettle));

    let discrepanciasCorrigidas = 0;
    const tabelaLive = obterTabelaAtiva() || tabela;

    for (let iTela = 0; iTela < alunosTela.length; iTela++) {
      const match = pares.get(iTela);
      if (!match) continue;

      const itemTela = alunosTela[iTela];
      const itemExcel = dadosAlunosExcel[match.indicePlanilha];
      const notasEsperadas = itemExcel.notas || [];

      const linhaLive = encontrarLinhaAlunoLive(tabelaLive, itemTela.nome, sgnNomes) || itemTela.linhaEl;
      if (!linhaLive) continue;

      const inputsLive = extrairInputsAvaliacaoLinha(linhaLive);
      if (!inputsLive || !inputsLive.length) continue;

      let precisaRecalcular = false;
      const qtdComparar = Math.min(inputsLive.length, notasEsperadas.length);

      for (let c = 0; c < qtdComparar; c++) {
        const inp = inputsLive[c];
        if (inp.disabled || inp.readOnly || (inp.classList && inp.classList.contains("noEdit"))) {
          continue;
        }
        const valEsperado = (notasEsperadas[c] !== "" && notasEsperadas[c] !== null && notasEsperadas[c] !== undefined)
          ? String(notasEsperadas[c]).trim()
          : "";
        const valAtual = (inp.value || "").trim();

        if (valEsperado !== "" && valAtual !== valEsperado) {
          logsExecucao.push(`[RECONCILIAÇÃO] ${itemTela.nome} (Col ${c + 1}): valor era '${valAtual}', restaurado para '${valEsperado}'.`);
          aplicarValorNoInput(inp, valEsperado);
          discrepanciasCorrigidas++;
          precisaRecalcular = true;
        } else if (valEsperado === "" && valAtual !== "") {
          logsExecucao.push(`[RECONCILIAÇÃO] ${itemTela.nome} (Col ${c + 1}): campo sem nota limpo para Falta Vinculada.`);
          aplicarValorNoInput(inp, "");
          discrepanciasCorrigidas++;
          precisaRecalcular = true;
        }
      }

      if (precisaRecalcular) {
        const notasLinha = inputsLive.map((inp, idx) => ({
          col: idx + 1,
          val: (inp.value || "").trim(),
          status: "reconciliado"
        }));
        const todasPreenchidas = notasLinha.every(n => n.val !== "");
        if (todasPreenchidas) {
          dispararRecalculoLinha(linhaLive, notasLinha);
        }
      }
    }

    if (discrepanciasCorrigidas > 0) {
      logsExecucao.push(`[RECONCILIAÇÃO CONCLUÍDA] ${discrepanciasCorrigidas} nota(s) restaurada(s) e confirmada(s) no DOM.`);
    } else {
      logsExecucao.push(`[VERIFICAÇÃO CONFIRMADA] 100% das notas verificadas e intactas no DOM.`);
    }

    if (totalPreenchidos === 0) {
      exibirToast(
        "Nenhum Aluno Preenchido",
        "Nenhuma nota pôde ser preenchida na tabela do SIGEduc.",
        "aviso",
        7000
      );
      return {
        sucesso: false,
        erro: "Nenhuma nota pôde ser preenchida na tabela do SIGEduc.",
        totalPreenchidos: 0,
        totalNotasPreenchidas: 0,
        totalAlunosTela: alunosTela.length,
        totalAlunosExcel: dadosAlunosExcel.length,
        conflitos,
        detalhes: detalhesPreenchimento,
        logs: logsExecucao
      };
    }

    exibirToast(
      "Notas Preenchidas!",
      `${totalPreenchidos} estudantes receberam ${totalNotasPreenchidas} notas na tela. Revise antes de gravar.`,
      "sucesso",
      7000
    );

    return {
      sucesso: true,
      totalPreenchidos,
      totalNotasPreenchidas,
      discrepanciasCorrigidas,
      totalAlunosTela: alunosTela.length,
      totalAlunosExcel: dadosAlunosExcel.length,
      conflitos,
      detalhes: detalhesPreenchimento,
      logs: logsExecucao
    };
  }

  // =========================================================================
  // 6. Preenchimento de Falta Vinculada (FV)
  // =========================================================================
  async function preencherFVNaTela(dadosAlunosExcel, opcoes = {}) {
    if (!dadosAlunosExcel || !Array.isArray(dadosAlunosExcel) || !dadosAlunosExcel.length) {
      return { sucesso: false, erro: "Dados dos alunos da planilha não fornecidos ou vazios." };
    }

    const { alunos: alunosTela, cabecalhos } = extrairAlunosDaTela();
    if (!alunosTela.length) {
      return { sucesso: false, erro: "Nenhuma linha identificada na tabela de Falta Vinculada." };
    }

    const tabela = obterTabelaAtiva();
    const thead = tabela ? tabela.querySelector("thead") : null;
    const trCabecalho = thead ? thead.querySelector("tr") : (tabela ? tabela.querySelector("tr") : null);
    const thsLinha = trCabecalho ? Array.from(trCabecalho.querySelectorAll("th, td")) : [];

    // Mapeia colunas que são avaliações/atividades no cabeçalho
    const colunasAtividades = [];
    thsLinha.forEach((th, cIdx) => {
      const txt = (th.innerText || th.textContent || "").trim().toUpperCase();
      const ehMetadado = (
        txt === "Nº" || txt === "NUMERO" || txt === "N." || txt === "ORDEM" ||
        txt === "MATRÍCULA" || txt === "MATRICULA" || txt === "MAT" ||
        txt === "ESTUDANTE" || txt === "ALUNO" || txt.includes("NOME") ||
        txt === "TOTAL" || txt.includes("TOTAL") || txt === "SITUAÇÃO" || txt === "SITUACAO" ||
        txt === "RESULTADO" || txt === "FALTA VINCULADA" || txt === "FALTAS"
      );
      if (!ehMetadado && txt !== "") {
        colunasAtividades.push({ cIdx, titulo: (th.innerText || th.textContent || "").trim() });
      }
    });

    const sgnNomes = (typeof window !== "undefined" && window.SgnNomes) ||
      (typeof SgnNomes !== "undefined" ? SgnNomes : null) ||
      (typeof require !== "undefined" ? require("../lib/nomes.js") : null);
    if (!sgnNomes) {
      return { sucesso: false, erro: "Biblioteca de correspondência de nomes não disponível." };
    }

    const nomesTela = alunosTela.map(a => a.nome);
    const nomesPlanilha = dadosAlunosExcel.map(a => a.nome);
    const { pares } = sgnNomes.casarListas(nomesTela, nomesPlanilha);

    if (!pares || pares.size === 0) {
      exibirToast(
        "Nenhum Estudante Casado",
        "Nenhum estudante da planilha correspondeu aos nomes na tela de Falta Vinculada.",
        "aviso",
        7000
      );
      return {
        sucesso: false,
        erro: "Nenhum estudante da planilha correspondeu aos estudantes na tabela de Falta Vinculada.",
        totalMarcados: 0
      };
    }

    let totalMarcados = 0;
    let delayMs = 15;
    if (opcoes && opcoes.delayMs !== undefined && opcoes.delayMs !== null) {
      const parsed = parseInt(opcoes.delayMs, 10);
      if (!isNaN(parsed) && parsed >= 0) delayMs = parsed;
    }

    for (let iTela = 0; iTela < alunosTela.length; iTela++) {
      const itemTela = alunosTela[iTela];
      const match = pares.get(iTela);
      if (!match) continue;

      const itemExcel = dadosAlunosExcel[match.indicePlanilha];
      const flagsFv = itemExcel.fv || [];

      // Reobtém checkboxes visíveis da linha ativa
      const linhaLive = (itemTela.linhaEl && itemTela.linhaEl.isConnected)
        ? itemTela.linhaEl
        : (encontrarLinhaAlunoLive(tabela, itemTela.nome, sgnNomes) || itemTela.linhaEl);

      const checkboxesLinha = linhaLive
        ? Array.from(linhaLive.querySelectorAll("input[type='checkbox']")).filter(c => elementoVisivel(c) && !c.disabled)
        : (itemTela.checkboxes || []).filter(c => !c.disabled);

      for (let idx = 0; idx < checkboxesLinha.length; idx++) {
        const chk = checkboxesLinha[idx];
        const td = chk.closest("td");
        const cellIdx = td ? td.cellIndex : -1;

        let idxAtividade = -1;

        // 1ª Estratégia: Mapeamento determinístico por cellIndex do cabeçalho
        if (cellIdx >= 0 && colunasAtividades.length > 0) {
          const encontrada = colunasAtividades.findIndex(c => c.cIdx === cellIdx);
          if (encontrada !== -1) {
            idxAtividade = encontrada;
          }
        }

        // 2ª Estratégia: Extração do índice da atividade pelo ID/Name (ex: :fv__1, fv__2)
        if (idxAtividade === -1) {
          const idOuName = (chk.id || chk.name || "");
          const matchNum = idOuName.match(/(?:fv|av)[_:]+(\d+)/i);
          if (matchNum) {
            idxAtividade = parseInt(matchNum[1], 10) - 1;
          }
        }

        // 3ª Estratégia: Fallback sequencial
        if (idxAtividade === -1) {
          idxAtividade = idx;
        }

        let deveMarcar = false;
        if (checkboxesLinha.length === 1) {
          // Apenas um checkbox na linha (tabela com coluna geral de FV): reflete temFv do aluno
          deveMarcar = !!itemExcel.temFv;
        } else {
          // Múltiplos checkboxes na linha: cada um corresponde à sua avaliação específica
          deveMarcar = (idxAtividade >= 0 && idxAtividade < flagsFv.length)
            ? flagsFv[idxAtividade]
            : (idx < flagsFv.length ? flagsFv[idx] : false);
        }

        if (deveMarcar && !chk.checked) {
          try {
            chk.focus();
            chk.click();
          } catch (e) {}
          if (!chk.checked) {
            chk.checked = true;
            try {
              chk.dispatchEvent(new Event("input", { bubbles: true }));
              chk.dispatchEvent(new Event("change", { bubbles: true }));
            } catch (e) {}
          }
          totalMarcados++;
          if (delayMs > 0) {
            await new Promise(r => setTimeout(r, delayMs));
          }
        } else if (!deveMarcar && chk.checked) {
          try {
            chk.focus();
            chk.click();
          } catch (e) {}
          if (chk.checked) {
            chk.checked = false;
            try {
              chk.dispatchEvent(new Event("input", { bubbles: true }));
              chk.dispatchEvent(new Event("change", { bubbles: true }));
            } catch (e) {}
          }
          if (delayMs > 0) {
            await new Promise(r => setTimeout(r, delayMs));
          }
        }
      }
    }

    exibirToast(
      "Faltas Vinculadas Aplicadas",
      `${totalMarcados} caixas de Falta Vinculada foram marcadas para os alunos sem nota da planilha.`,
      "sucesso",
      7000
    );

    return { sucesso: true, totalMarcados };
  }

  // =========================================================================
  // 7. Submissão e Gravação com Senha (Opcional)
  // =========================================================================
  async function submeterComSenha(senha) {
    if (!senha) return { sucesso: false, erro: "Senha não fornecida." };

    // 1. Procura campo de senha já presente na tela principal
    let campoSenha = document.querySelector("input[type='password']");
    if (campoSenha && elementoVisivel(campoSenha)) {
      campoSenha.value = senha;
      dispararEventosInput(campoSenha);

      const btnGravar = Array.from(document.querySelectorAll("input[type='submit'], input[type='button'], button"))
        .find(el => elementoVisivel(el) && !el.disabled && /gravar|salvar|cadastrar/i.test(el.value || el.innerText || ""));

      if (btnGravar) {
        btnGravar.click();
        return { sucesso: true, mensagem: "Gravação enviada com sucesso!" };
      }
    }

    // 2. Fluxo com popup modal: Clica em Gravar para abrir o popup de senha
    const btnGravar = Array.from(document.querySelectorAll("input[type='submit'], input[type='button'], button"))
      .find(el => elementoVisivel(el) && !el.disabled && /gravar|salvar|cadastrar/i.test(el.value || el.innerText || ""));

    if (!btnGravar) {
      return { sucesso: false, erro: "Botão 'Gravar' não encontrado na tela." };
    }

    btnGravar.click();

    // Aguarda modal abrir por até 6 segundos
    let campoModal = null;
    const inicio = Date.now();
    while (Date.now() - inicio < 6000) {
      const inputs = Array.from(document.querySelectorAll("input[type='password']"));
      campoModal = inputs.find(i => elementoVisivel(i));
      if (campoModal) break;
      await new Promise(r => setTimeout(r, 400));
    }

    if (campoModal) {
      campoModal.value = senha;
      dispararEventosInput(campoModal);

      await new Promise(r => setTimeout(r, 300));
      const btnConfirmar = Array.from(document.querySelectorAll("input[type='submit'], input[type='button'], button"))
        .find(el => elementoVisivel(el) && !el.disabled && /confirmar|ok/i.test(el.value || el.innerText || ""));

      if (btnConfirmar) {
        btnConfirmar.click();
        return { sucesso: true, mensagem: "Senha confirmada no modal com sucesso!" };
      } else {
        campoModal.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", keyCode: 13, bubbles: true }));
        return { sucesso: true, mensagem: "Senha enviada via tecla Enter!" };
      }
    }

    return { sucesso: true, mensagem: "Gravação submetida." };
  }

  // =========================================================================
  // 7.1 Módulo de Lançamento de Presenças e Faltas (Frequência & Calendário)
  // =========================================================================
  const MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
  ];

  function alterarCheckbox(chk, marcar) {
    if (!chk || chk.disabled || chk.getAttribute("disabled")) return false;
    const estadoAtual = Boolean(chk.checked);
    if (estadoAtual === Boolean(marcar)) return false;

    try { chk.focus(); } catch (e) {}
    try { chk.click(); } catch (e) {}

    if (chk.checked !== marcar) {
      chk.checked = marcar;
    }

    try {
      chk.dispatchEvent(new Event("change", { bubbles: true }));
      chk.dispatchEvent(new Event("input", { bubbles: true }));
    } catch (e) {}

    return true;
  }

  function extrairAlunosFrequenciaDaTela() {
    let tabela = document.querySelector("#tableAlunos");
    if (!tabela) {
      const tabelas = Array.from(document.querySelectorAll("table"));
      tabela = tabelas.find(t => t.querySelector("tbody tr") && t.querySelector("input[type='checkbox']"));
    }
    if (!tabela) return { alunos: [], total: 0 };

    const linhas = Array.from(tabela.querySelectorAll("tbody tr"));
    const alunos = [];

    linhas.forEach((linha, idx) => {
      const td3 = linha.querySelector("td:nth-child(3)");
      let nome = td3 ? limparNomeAluno(td3.innerText || "") : "";
      if (!nome || nome.length < 3) {
        nome = extrairNomeDaLinha(linha);
      }
      if (!nome) return;

      const cbs = Array.from(linha.querySelectorAll("input[type='checkbox']"));
      const habilitados = cbs.filter(c => !c.disabled && !c.getAttribute("disabled"));
      const desabilitados = cbs.filter(c => c.disabled || c.getAttribute("disabled"));

      alunos.push({
        indice: idx,
        nome: nome,
        linha: linha,
        checkboxes: habilitados,
        totalCheckboxes: cbs.length,
        temDesabilitado: desabilitados.length > 0
      });
    });

    return { alunos, total: alunos.length };
  }

  function marcarPresencaTodos() {
    const { alunos } = extrairAlunosFrequenciaDaTela();
    let modificados = 0;

    alunos.forEach(aluno => {
      aluno.checkboxes.forEach(chk => {
        // Checkbox desmarcado = PRESENÇA
        if (alterarCheckbox(chk, false)) {
          modificados++;
        }
      });
    });

    return {
      sucesso: true,
      totalAlunos: alunos.length,
      modificados: modificados,
      mensagem: `Presença atribuída a ${alunos.length} estudantes (${modificados} marcações atualizadas).`
    };
  }

  function marcarFaltososPorLista(nomesFaltosos = []) {
    const { alunos } = extrairAlunosFrequenciaDaTela();
    const sgnNomes = (typeof window !== "undefined" && window.SgnNomes) ||
                     (typeof SgnNomes !== "undefined" ? SgnNomes : null) ||
                     (typeof require !== "undefined" ? require("../lib/nomes.js") : null);

    let faltososCount = 0;
    let presentesCount = 0;
    const faltososEncontrados = [];
    const nomesNormalizadosFaltosos = (nomesFaltosos || []).map(n => String(n).trim()).filter(Boolean);

    alunos.forEach(aluno => {
      let ehFaltoso = false;
      if (sgnNomes && nomesNormalizadosFaltosos.length > 0) {
        ehFaltoso = nomesNormalizadosFaltosos.some(nomeF => sgnNomes.nomesSaoIguais(aluno.nome, nomeF));
      }

      if (ehFaltoso) {
        faltososCount++;
        faltososEncontrados.push(aluno.nome);
        aluno.checkboxes.forEach(chk => alterarCheckbox(chk, true));
      } else {
        presentesCount++;
        aluno.checkboxes.forEach(chk => alterarCheckbox(chk, false));
      }
    });

    const naoEncontrados = nomesNormalizadosFaltosos.filter(nomeF => {
      return !faltososEncontrados.some(nomeE => sgnNomes && sgnNomes.nomesSaoIguais(nomeE, nomeF));
    });

    return {
      sucesso: true,
      totalAlunos: alunos.length,
      faltososCount,
      presentesCount,
      faltososEncontrados,
      naoEncontrados,
      mensagem: `${faltososCount} faltosos marcados, ${presentesCount} presentes confirmados.`
    };
  }

  function marcarFaltososPorMapaData(mapaAlunosData = {}) {
    const { alunos } = extrairAlunosFrequenciaDaTela();
    const sgnNomes = (typeof window !== "undefined" && window.SgnNomes) ||
                     (typeof SgnNomes !== "undefined" ? SgnNomes : null) ||
                     (typeof require !== "undefined" ? require("../lib/nomes.js") : null);

    const nomesTela = alunos.map(a => a.nome);
    const nomesPlanilha = Object.keys(mapaAlunosData || {});

    let resultadoCasamento = null;
    if (sgnNomes) {
      resultadoCasamento = sgnNomes.casarListas(nomesTela, nomesPlanilha);
    }

    let faltososCount = 0;
    let presentesCount = 0;

    alunos.forEach((aluno, iTela) => {
      let status = "P";
      if (resultadoCasamento && resultadoCasamento.pares.has(iTela)) {
        const par = resultadoCasamento.pares.get(iTela);
        const nomePlanilha = nomesPlanilha[par.indicePlanilha];
        status = mapaAlunosData[nomePlanilha] || "P";
      } else if (mapaAlunosData && mapaAlunosData[aluno.nome]) {
        status = mapaAlunosData[aluno.nome];
      }

      const ehFalta = (status === "F" || status === "X" || status === "1");
      if (ehFalta) {
        faltososCount++;
        aluno.checkboxes.forEach(chk => alterarCheckbox(chk, true));
      } else {
        presentesCount++;
        aluno.checkboxes.forEach(chk => alterarCheckbox(chk, false));
      }
    });

    return {
      sucesso: true,
      totalAlunos: alunos.length,
      faltososCount,
      presentesCount,
      mensagem: `Frequência aplicada: ${faltososCount} faltosos e ${presentesCount} presentes.`
    };
  }

  function encontrarTabelaDoMes(mes) {
    if (!mes || mes < 1 || mes > 12) return null;
    const nomeMesNorm = normalizarTextoSimples(MESES[mes - 1]);
    const outrosMeses = MESES.filter((_, idx) => idx !== (mes - 1)).map(m => normalizarTextoSimples(m));

    const todasTabelas = Array.from(document.querySelectorAll("table"));
    const tabelasFolha = todasTabelas.filter(t => t.querySelectorAll("table").length === 0);

    // 1. Tabela folha cujo texto contém o mês desejado e nenhum outro mês
    for (const tab of tabelasFolha) {
      const txt = normalizarTextoSimples(tab.innerText || "");
      if (txt.includes(nomeMesNorm) && !outrosMeses.some(om => txt.includes(om))) {
        return tab;
      }
    }

    // 2. Tabela folha cujo container pai contém o mês desejado e nenhum outro
    for (const tab of tabelasFolha) {
      const pai = tab.closest("div, td, section, fieldset, form, .calendario, .month") || tab.parentElement;
      if (pai) {
        const txtPai = normalizarTextoSimples(pai.innerText || "");
        if (txtPai.includes(nomeMesNorm) && !outrosMeses.some(om => txtPai.includes(om))) {
          return tab;
        }
      }
    }

    // 3. Qualquer tabela cujo texto contenha o mês
    for (const tab of todasTabelas) {
      const txt = normalizarTextoSimples(tab.innerText || "");
      if (txt.includes(nomeMesNorm)) {
        return tab;
      }
    }

    // 4. Elementos de cabeçalho ou título com o nome do mês
    const cabecalhos = Array.from(document.querySelectorAll("caption, th, h1, h2, h3, h4, h5, div, span, b, strong")).filter(el => {
      const txt = normalizarTextoSimples(el.innerText || "");
      return txt === nomeMesNorm || txt.startsWith(nomeMesNorm);
    });
    for (const el of cabecalhos) {
      const container = el.closest("div, table, section, fieldset, td") || el.parentElement;
      if (container) {
        const tab = container.querySelector("table");
        if (tab) return tab;
        return container;
      }
    }

    return null;
  }

  function acionarCliqueElemento(el) {
    if (!el) return false;
    try {
      if (typeof el.scrollIntoView === "function") {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      el.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, cancelable: true, view: window }));
      el.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, view: window }));
      el.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true, view: window }));
      el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
      if (typeof el.click === "function") {
        el.click();
      }
      return true;
    } catch (e) {
      try {
        if (typeof el.click === "function") {
          el.click();
          return true;
        }
      } catch (err) {
        console.error("Erro ao clicar no elemento do calendário:", err);
      }
    }
    return false;
  }

  function encontrarEClicarDiaNoCalendario(dia, mes) {
    const diaNum = parseInt(dia, 10);
    if (isNaN(diaNum)) return false;

    const diaStr = String(diaNum);
    const diaZero = diaStr.padStart(2, "0");
    const mesNum = mes ? parseInt(mes, 10) : null;
    const dataFormatada = mesNum ? `${diaZero}/${String(mesNum).padStart(2, "0")}` : diaStr;

    const raizBusca = mesNum ? (encontrarTabelaDoMes(mesNum) || document.body) : document.body;

    // 1. Procura em links <a>
    const links = Array.from(raizBusca.querySelectorAll("a"));
    for (const link of links) {
      const txt = (link.innerText || link.textContent || "").replace(/\s+/g, "").trim();
      const title = (link.getAttribute("title") || "").trim();
      const href = (link.getAttribute("href") || "").trim();
      const onclick = (link.getAttribute("onclick") || "").trim();

      if (
        txt === diaStr ||
        txt === diaZero ||
        (title && (title.includes(dataFormatada) || title.includes(` ${diaNum} `))) ||
        (onclick && (onclick.includes(`'${diaNum}'`) || onclick.includes(`"${diaNum}"`)))
      ) {
        return acionarCliqueElemento(link);
      }
    }

    // 2. Procura em elementos clicáveis ([onclick], buttons)
    const clicaveis = Array.from(raizBusca.querySelectorAll("button, td[onclick], span[onclick], div[onclick], [onclick]"));
    for (const el of clicaveis) {
      const txt = (el.innerText || el.textContent || "").replace(/\s+/g, "").trim();
      if (txt === diaStr || txt === diaZero) {
        return acionarCliqueElemento(el);
      }
    }

    // 3. Procura em células <td>
    const tds = Array.from(raizBusca.querySelectorAll("td"));
    for (const td of tds) {
      const txt = (td.innerText || td.textContent || "").replace(/\s+/g, "").trim();
      if (txt === diaStr || txt === diaZero) {
        const filho = td.querySelector("a, button, [onclick]");
        if (filho) return acionarCliqueElemento(filho);
        return acionarCliqueElemento(td);
      }
    }

    // 4. Fallback: Se não achou na raiz específica do mês e mesNum foi fornecido, tenta na página inteira
    if (raizBusca !== document.body) {
      const todosLinks = Array.from(document.querySelectorAll("a"));
      for (const link of todosLinks) {
        const title = (link.getAttribute("title") || "").trim();
        const onclick = (link.getAttribute("onclick") || "").trim();
        const href = (link.getAttribute("href") || "").trim();
        if (
          (title && title.includes(dataFormatada)) ||
          (onclick && onclick.includes(dataFormatada)) ||
          (href && href.includes(dataFormatada))
        ) {
          return acionarCliqueElemento(link);
        }
      }
    }

    return false;
  }

  function voltarParaCalendario() {
    const botoes = Array.from(document.querySelectorAll("input[type='button'], input[type='submit'], button, a"));
    const btnVoltar = botoes.find(el => {
      const val = normalizarTextoSimples(el.value || el.innerText || "");
      return (
        val.includes("VOLTAR") ||
        val.includes("RETORNAR") ||
        val.includes("CALENDARIO") ||
        val.includes("DIARIO DE CLASSE")
      );
    });
    if (btnVoltar) {
      acionarCliqueElemento(btnVoltar);
      return true;
    }
    if (typeof window !== "undefined" && window.history && window.history.back) {
      window.history.back();
      return true;
    }
    return false;
  }

  function exibirBarraProgressoLote(atual, total, dataAtual) {
    if (typeof document === "undefined" || !document.body) return;
    let widget = document.getElementById("sgn-progresso-lote");
    if (!widget) {
      widget = document.createElement("div");
      widget.id = "sgn-progresso-lote";
      document.body.appendChild(widget);
    }

    widget.innerHTML = `
      <span class="sgn-barra-icon">⏳</span>
      <div class="sgn-prog-text">
        Lote em andamento: <strong>${atual} de ${total}</strong> (${dataAtual})
      </div>
      <button type="button" class="sgn-btn-cancelar-lote" id="sgn-btn-cancelar-lote" title="Interromper lote de frequência">
        ⏹️ Parar
      </button>
    `;

    const btnParar = widget.querySelector("#sgn-btn-cancelar-lote");
    if (btnParar) {
      btnParar.onclick = () => {
        sessionStorage.removeItem("sgn_lote_frequencia");
        widget.style.display = "none";
        exibirToast("Lote Interrompido", "A automação de datas foi cancelada.", "aviso", 4000);
      };
    }

    widget.style.display = "flex";
  }

  async function verificarEExecutarFilaLote() {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    const raw = sessionStorage.getItem("sgn_lote_frequencia");
    if (!raw) return;

    let config = null;
    try {
      config = JSON.parse(raw);
    } catch (e) {
      sessionStorage.removeItem("sgn_lote_frequencia");
      return;
    }

    if (!config || !config.ativo || !Array.isArray(config.filaDatas)) {
      sessionStorage.removeItem("sgn_lote_frequencia");
      return;
    }

    let tela = detectarTela();
    const indiceAtual = config.indiceAtual || 0;
    const total = config.filaDatas.length;

    if (indiceAtual >= total) {
      sessionStorage.removeItem("sgn_lote_frequencia");
      const widget = document.getElementById("sgn-progresso-lote");
      if (widget) widget.style.display = "none";
      exibirToast("Lote Concluído! 🎉", `Todas as ${total} datas foram lançadas com sucesso!`, "sucesso", 8000);
      return;
    }

    const dataAtual = config.filaDatas[indiceAtual];
    exibirBarraProgressoLote(indiceAtual + 1, total, dataAtual);

    if (tela === "frequencia_dia") {
      // 1. Estamos na tela de frequência do dia
      const mapaData = (config.dadosFrequenciaPorData && config.dadosFrequenciaPorData[dataAtual]) || null;
      if (mapaData) {
        marcarFaltososPorMapaData(mapaData);
      } else {
        marcarPresencaTodos();
      }

      await new Promise(r => setTimeout(r, 450));

      if (config.autoGravar && config.senha) {
        exibirToast("Gravando Chamada...", `Confirmando presença do dia ${dataAtual} com senha...`, "info", 3000);
        const resGravar = await submeterComSenha(config.senha);
        if (!resGravar.sucesso) {
          exibirToast("Atenção na Gravação", resGravar.erro || "Verifique a senha no site.", "aviso", 6000);
          return;
        }
      }

      config.indiceAtual = indiceAtual + 1;
      sessionStorage.setItem("sgn_lote_frequencia", JSON.stringify(config));

      await new Promise(r => setTimeout(r, 600));
      voltarParaCalendario();

    } else {
      // 2. Estamos no Calendário Mensal (ou transição de página)
      const pedacos = dataAtual.split(/[\/\-\.]/);
      const dia = parseInt(pedacos[0], 10);
      const mes = pedacos.length > 1 ? parseInt(pedacos[1], 10) : null;

      // Aguarda 600ms para estabilização do DOM
      await new Promise(r => setTimeout(r, 600));

      let clicou = encontrarEClicarDiaNoCalendario(dia, mes);
      if (!clicou) {
        // Tenta mais uma vez após 800ms (para requisições AJAX do RichFaces)
        await new Promise(r => setTimeout(r, 800));
        clicou = encontrarEClicarDiaNoCalendario(dia, mes);
      }

      if (clicou) {
        exibirToast("Data Selecionada!", `Abrindo chamada do dia ${dataAtual}...`, "info", 3000);
      } else {
        exibirToast("Data Não Encontrada", `Não foi possível localizar o dia ${dataAtual} no calendário ativo. Clique na data manualmente no site para continuar o lote.`, "aviso", 9000);
      }
    }
  }

  function baixarModeloFrequenciaDireto() {
    const metadados = extrairMetadadosTela();
    const { alunos } = extrairAlunosFrequenciaDaTela();
    const sgnExcel = (typeof window !== "undefined" && window.SgnExcel) ||
                     (typeof SgnExcel !== "undefined" ? SgnExcel : null) ||
                     (typeof require !== "undefined" ? require("../lib/excel.js") : null);

    if (!sgnExcel) {
      exibirToast("Baixar Modelo", "Abra a extensão SIGEduc Auto para baixar a planilha modelo.", "info", 4000);
      return;
    }

    try {
      const res = sgnExcel.gerarPlanilhaModeloFrequencia({
        turma: metadados.turma,
        componente: metadados.componente,
        alunos: alunos.map(a => a.nome)
      });

      const blob = new Blob([res.arrayBuffer], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = res.nomeArquivo;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      exibirToast("Modelo Gerado", `Planilha '${res.nomeArquivo}' baixada com sucesso!`, "sucesso", 4000);
    } catch (e) {
      exibirToast("Erro ao Gerar Modelo", e.message, "erro", 5000);
    }
  }

  function injetarBarraFrequenciaNaTela() {
    if (typeof document === "undefined" || !document.body) return;
    if (document.getElementById("sgn-barra-frequencia")) return;

    let tabela = document.querySelector("#tableAlunos");
    if (!tabela) {
      const tabelas = Array.from(document.querySelectorAll("table"));
      tabela = tabelas.find(t => t.querySelector("tbody tr") && t.querySelector("input[type='checkbox']"));
    }
    if (!tabela) return;

    const barra = document.createElement("div");
    barra.id = "sgn-barra-frequencia";
    barra.className = "sgn-barra-frequencia";
    barra.innerHTML = `
      <div class="sgn-barra-brand">
        <span class="sgn-barra-icon">📅</span>
        <strong class="sgn-barra-title">SIGEduc Auto</strong>
      </div>
      <div class="sgn-barra-actions">
        <button type="button" id="sgn-btn-todos-presentes" class="sgn-btn-barra-verde" title="Desmarca todas as faltas (100% de presença)">
          🟢 100% Presentes
        </button>
        <div class="sgn-barra-input-group">
          <input type="text" id="sgn-input-faltosos-rapido" placeholder="Faltosos (ex: Sabrina, Thiago)..." class="sgn-barra-input" />
          <button type="button" id="sgn-btn-marcar-faltosos" class="sgn-btn-barra-laranja" title="Marca falta apenas para os digitados">
            ⚡ Marcar Faltas
          </button>
        </div>
        <button type="button" id="sgn-btn-baixar-modelo-freq" class="sgn-btn-barra-cinza" title="Baixa modelo Excel desta turma com markboxes">
          📥 Baixar Modelo Excel
        </button>
      </div>
    `;

    tabela.parentNode.insertBefore(barra, tabela);

    const btnTodos = barra.querySelector("#sgn-btn-todos-presentes");
    if (btnTodos) {
      btnTodos.onclick = () => {
        const res = marcarPresencaTodos();
        exibirToast("Chamada Atualizada", res.mensagem, "sucesso", 4000);
      };
    }

    const btnFaltosos = barra.querySelector("#sgn-btn-marcar-faltosos");
    const inputFaltosos = barra.querySelector("#sgn-input-faltosos-rapido");
    if (btnFaltosos && inputFaltosos) {
      const acaoMarcar = () => {
        const val = inputFaltosos.value.trim();
        if (!val) {
          exibirToast("Atenção", "Digite ao menos um nome de aluno faltoso.", "aviso", 3000);
          return;
        }
        const nomes = val.split(/[,;\n\r]+/).map(n => n.trim()).filter(Boolean);
        const res = marcarFaltososPorLista(nomes);
        exibirToast("Faltas Registradas", res.mensagem, "sucesso", 4000);
      };
      btnFaltosos.onclick = acaoMarcar;
      inputFaltosos.onkeydown = (e) => {
        if (e.key === "Enter") acaoMarcar();
      };
    }

    const btnModelo = barra.querySelector("#sgn-btn-baixar-modelo-freq");
    if (btnModelo) {
      btnModelo.onclick = () => {
        baixarModeloFrequenciaDireto();
      };
    }
  }

  // =========================================================================
  // 8. Listener de Mensagens da Extensão com Suporte a Reinjeção Dinâmica
  // =========================================================================
  if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
    if (typeof window !== "undefined" && window.__sgnMensagemListener && chrome.runtime.onMessage.hasListener(window.__sgnMensagemListener)) {
      try {
        chrome.runtime.onMessage.removeListener(window.__sgnMensagemListener);
      } catch (e) {}
    }

    const listener = function (request, sender, sendResponse) {
      try {
        switch (request.tipo) {
          case "PING": {
            const tela = detectarTela();
            const { alunos, cabecalhos, atividadesSIGEduc } = extrairAlunosDaTela();
            const unidadeAtiva = detectarUnidadeAtiva();
            sendResponse({
              sucesso: true,
              pong: true,
              versao: VERSAO_CONTENT,
              url: typeof window !== "undefined" ? window.location.href : "",
              tela: tela,
              unidadeAtiva: unidadeAtiva,
              qtdAlunosTela: alunos.length,
              cabecalhos: cabecalhos.map(c => c.texto),
              atividadesSIGEduc: atividadesSIGEduc || [],
              nomesAmostra: alunos.slice(0, 3).map(a => a.nome)
            });
            break;
          }

          case "OBTER_ESTADO_TELA": {
            const tela = detectarTela();
            const unidadeAtiva = detectarUnidadeAtiva();
            const { alunos, cabecalhos, atividadesSIGEduc } = extrairAlunosDaTela();
            const metadados = extrairMetadadosTela();

            sendResponse({
              sucesso: true,
              tela: tela,
              unidadeAtiva: unidadeAtiva,
              turma: metadados.turma,
              turmaCompleta: metadados.turmaCompleta,
              componente: metadados.componente,
              escola: metadados.escola,
              qtdAlunosTela: alunos.length,
              nomesAlunosTela: alunos.map(a => a.nome),
              cabecalhos: cabecalhos.map(c => c.texto),
              atividadesSIGEduc: atividadesSIGEduc || [],
              qtdColunasInputs: alunos.length ? alunos[0].qtdInputs : 0,
              qtdCheckboxesFV: alunos.length ? alunos[0].qtdCheckboxes : 0,
              url: typeof window !== "undefined" ? window.location.href : ""
            });
            break;
          }

          case "OBTER_DADOS_MODELO_EXCEL": {
            const metadados = extrairMetadadosTela();
            const { alunos, atividadesSIGEduc } = extrairAlunosDaTela();
            const alunosFormatados = alunos.map(a => ({
              nome: a.nome,
              notas: (a.inputs || []).map(inp => (inp.value || "").trim())
            }));

            sendResponse({
              sucesso: true,
              turma: metadados.turma,
              turmaCompleta: metadados.turmaCompleta,
              componente: metadados.componente,
              escola: metadados.escola,
              unidade: metadados.unidade,
              atividades: atividadesSIGEduc.length ? atividadesSIGEduc : ["Atividade 1", "Atividade 2", "Atividade 3"],
              totalAlunos: alunosFormatados.length,
              alunos: alunosFormatados
            });
            break;
          }

          case "PREVIEW_CASAMENTO": {
            const { alunos: alunosTela } = extrairAlunosDaTela();
            const nomesTela = alunosTela.map(a => a.nome);
            const nomesExcel = request.nomesExcel || [];

            const sgnNomes = (typeof window !== "undefined" && window.SgnNomes) ||
              (typeof SgnNomes !== "undefined" ? SgnNomes : null) ||
              (typeof require !== "undefined" ? require("../lib/nomes.js") : null);

            if (!sgnNomes) {
              sendResponse({ sucesso: false, erro: "Biblioteca de nomes indisponível." });
              break;
            }

            const resultado = sgnNomes.casarListas(nomesTela, nomesExcel);
            const paresDetalhes = [];
            const indicesExcelCasados = new Set();
            const indicesTelaCasados = new Set();

            resultado.pares.forEach((val, iTela) => {
              indicesTelaCasados.add(iTela);
              indicesExcelCasados.add(val.indicePlanilha);
              paresDetalhes.push({
                nomeTela: nomesTela[iTela],
                nomeExcel: nomesExcel[val.indicePlanilha],
                indicePlanilha: val.indicePlanilha,
                nivel: val.nivel
              });
            });

            const alunosTelaSemPar = nomesTela.filter((_, idx) => !indicesTelaCasados.has(idx));
            const alunosExcelSemPar = nomesExcel.filter((_, idx) => !indicesExcelCasados.has(idx));

            sendResponse({
              sucesso: true,
              totalTela: nomesTela.length,
              totalExcel: nomesExcel.length,
              totalCasados: resultado.pares.size,
              pares: paresDetalhes,
              conflitos: resultado.conflitos,
              alunosTelaSemPar,
              alunosExcelSemPar
            });
            break;
          }

          case "GARANTIR_UNIDADE": {
            const res = garantirUnidadeAtiva(request.unidade);
            sendResponse(res);
            break;
          }

          case "PREENCHER_NOTAS": {
            preencherNotasNaTela(request.dadosAlunosExcel, request.opcoes)
              .then(sendResponse)
              .catch(err => {
                sendResponse({ sucesso: false, erro: err.message, stack: err.stack });
              });
            return true; // mantem canal assincrono aberto
          }

          case "PREENCHER_FV": {
            preencherFVNaTela(request.dadosAlunosExcel, request.opcoes)
              .then(sendResponse)
              .catch(err => {
                sendResponse({ sucesso: false, erro: err.message, stack: err.stack });
              });
            return true; // mantem canal assincrono aberto
          }

          case "SUBMETER_SENHA": {
            submeterComSenha(request.senha).then(sendResponse);
            return true; // mantem canal assincrono aberto
          }

          case "OBTER_ESTADO_FREQUENCIA": {
            const tela = detectarTela();
            const metadados = extrairMetadadosTela();
            let alunosFreq = [];
            if (tela === "frequencia_dia") {
              const res = extrairAlunosFrequenciaDaTela();
              alunosFreq = res.alunos.map(a => ({
                indice: a.indice,
                nome: a.nome,
                qtdCheckboxes: a.checkboxes.length,
                temDesabilitado: a.temDesabilitado
              }));
            }
            let diasCalendario = [];
            if (tela === "frequencia_calendario") {
              const tabs = Array.from(document.querySelectorAll("table")).filter(t => eTabelaCalendario(t));
              tabs.forEach(t => {
                const links = Array.from(t.querySelectorAll("a"));
                links.forEach(l => {
                  const num = parseInt((l.innerText || "").trim(), 10);
                  if (!isNaN(num) && num >= 1 && num <= 31) {
                    diasCalendario.push(num);
                  }
                });
              });
            }

            let loteAtivo = false;
            let statusLote = null;
            if (typeof window !== "undefined" && window.sessionStorage) {
              const raw = sessionStorage.getItem("sgn_lote_frequencia");
              if (raw) {
                try {
                  statusLote = JSON.parse(raw);
                  loteAtivo = Boolean(statusLote && statusLote.ativo);
                } catch (e) {}
              }
            }

            sendResponse({
              sucesso: true,
              tela,
              turma: metadados.turma,
              turmaCompleta: metadados.turmaCompleta,
              componente: metadados.componente,
              escola: metadados.escola,
              totalAlunos: alunosFreq.length,
              alunos: alunosFreq,
              diasCalendario: Array.from(new Set(diasCalendario)).sort((a, b) => a - b),
              loteAtivo,
              statusLote
            });
            break;
          }

          case "MARCAR_FREQUENCIA_TODOS": {
            const res = marcarPresencaTodos();
            sendResponse(res);
            break;
          }

          case "MARCAR_FREQUENCIA_FALTOSOS": {
            const res = marcarFaltososPorLista(request.nomesFaltosos || []);
            sendResponse(res);
            break;
          }

          case "MARCAR_FREQUENCIA_EXCEL": {
            const res = marcarFaltososPorMapaData(request.mapaAlunosData || {});
            sendResponse(res);
            break;
          }

          case "INICIAR_LOTE_CALENDARIO": {
            if (typeof window !== "undefined" && window.sessionStorage) {
              const config = {
                ativo: true,
                filaDatas: request.filaDatas || [],
                indiceAtual: 0,
                dadosFrequenciaPorData: request.dadosFrequenciaPorData || {},
                autoGravar: Boolean(request.autoGravar),
                senha: request.senha || ""
              };
              sessionStorage.setItem("sgn_lote_frequencia", JSON.stringify(config));
              verificarEExecutarFilaLote();
              sendResponse({ sucesso: true, mensagem: `Lote iniciado com ${config.filaDatas.length} datas.` });
            } else {
              sendResponse({ sucesso: false, erro: "sessionStorage indisponível." });
            }
            break;
          }

          case "CANCELAR_LOTE_CALENDARIO": {
            if (typeof window !== "undefined" && window.sessionStorage) {
              sessionStorage.removeItem("sgn_lote_frequencia");
              const widget = document.getElementById("sgn-progresso-lote");
              if (widget) widget.style.display = "none";
              sendResponse({ sucesso: true, mensagem: "Lote cancelado." });
            } else {
              sendResponse({ sucesso: true });
            }
            break;
          }

          case "OBTER_DADOS_MODELO_FREQUENCIA": {
            const metadados = extrairMetadadosTela();
            const { alunos } = extrairAlunosFrequenciaDaTela();
            sendResponse({
              sucesso: true,
              turma: metadados.turma,
              turmaCompleta: metadados.turmaCompleta,
              componente: metadados.componente,
              escola: metadados.escola,
              totalAlunos: alunos.length,
              alunos: alunos.map(a => a.nome)
            });
            break;
          }

          default:
            sendResponse({ sucesso: false, erro: `Ação '${request.tipo}' não reconhecida.` });
        }
      } catch (err) {
        console.error("Erro no SIGEduc Auto Content Script:", err);
        sendResponse({ sucesso: false, erro: err.message, stack: err.stack });
      }

      return true;
    };

    if (typeof window !== "undefined") {
      window.__sgnMensagemListener = listener;
    }
    chrome.runtime.onMessage.addListener(listener);
  }

  // Inicialização automática de recursos na página do SIGEduc
  if (typeof document !== "undefined" && typeof window !== "undefined") {
    const autoInit = () => {
      const tela = detectarTela();
      if (tela === "frequencia_dia") {
        injetarBarraFrequenciaNaTela();
      }
      verificarEExecutarFilaLote();
    };

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", autoInit);
    } else {
      setTimeout(autoInit, 300);
    }
  }

  const api = {
    VERSAO_CONTENT,
    limparNomeAluno,
    detectarTela,
    eTabelaCalendario,
    obterTabelaAtiva,
    extrairCabecalhosTabela,
    extrairNomeDaLinha,
    extrairAlunosDaTela,
    extrairInputsAvaliacaoLinha,
    ehInputAvaliacao,
    elementoVisivel,
    detectarUnidadeAtiva,
    garantirUnidadeAtiva,
    dispararEventosInput,
    dispararRecalculoLinha,
    preencherNotasNaTela,
    preencherFVNaTela,
    submeterComSenha,
    extrairAlunosFrequenciaDaTela,
    marcarPresencaTodos,
    marcarFaltososPorLista,
    marcarFaltososPorMapaData,
    encontrarEClicarDiaNoCalendario,
    encontrarTabelaDoMes,
    normalizarTextoSimples,
    voltarParaCalendario,
    verificarEExecutarFilaLote,
    injetarBarraFrequenciaNaTela
  };

  if (typeof root !== "undefined") {
    root.SgnContent = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
