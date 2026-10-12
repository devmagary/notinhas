/*
 * Processamento e extracao de dados de planilhas Excel (.xlsx) usando SheetJS.
 * Compativel com ambiente de extensao de navegador (globalThis.SgnExcel)
 * e ambiente Node.js (module.exports) para testes unitarios.
 */
(function (root) {
  "use strict";

  const VALORES_VAZIOS = new Set([
    "", "-", "--", "---", "n/a", "na", "null", "none",
    "sem nota", "s/n", "sn", "sem avaliacao", "sem avaliação",
    "pendente", "fv", "f.v.", "f.v", "falta", "faltou", "ausente", "disp", "dispensado", "dispensa",
    "não fez", "nao fez", "não compareceu", "nao compareceu", "nf", "n/f", "n.f.",
    "fj", "falta justificada", "justificada", "atestado",
    "#n/d", "#valor!", "#ref!", "#n/a"
  ]);

  /** Converte letra de coluna (A, B, Z, AA, AB) para indice base 0 */
  function letraParaIndice(letra) {
    if (typeof letra === "number") return Math.max(0, letra);
    letra = String(letra || "").trim().toUpperCase();
    let soma = 0;
    for (let i = 0; i < letra.length; i++) {
      const c = letra.charCodeAt(letra.length - 1 - i);
      if (c >= 65 && c <= 90) {
        soma += (c - 64) * Math.pow(26, i);
      }
    }
    return Math.max(0, soma - 1);
  }

  /** Converte indice base 0 para letra (0 -> A, 1 -> B, 26 -> AA) */
  function indiceParaLetra(indice) {
    let letra = "";
    let temp = indice;
    while (temp >= 0) {
      letra = String.fromCharCode((temp % 26) + 65) + letra;
      temp = Math.floor(temp / 26) - 1;
    }
    return letra;
  }

  /**
   * Verifica se o valor da celula representa Falta Vinculada / ausencia de nota
   */
  function ehFaltaVinculada(val) {
    if (val === null || val === undefined) return true;
    const txt = String(val).replace(/\u00A0/g, " ").trim().toLowerCase();
    if (VALORES_VAZIOS.has(txt) || txt === "") return true;
    if (txt.includes("não fez") || txt.includes("nao fez") || txt.includes("sem nota") || txt.includes("faltou") || txt.includes("ausente")) return true;
    const num = parseFloat(txt.replace(",", "."));
    return isNaN(num);
  }

  /**
   * Formata nota para insercao no SIGEduc.
   * formato: 'ponto' (ex: '7.5', padrao SIGEduc) ou 'virgula' (ex: '7,5')
   */
  function formatarNota(val, formato = "ponto") {
    if (val === null || val === undefined) return "";
    const txt = String(val).trim();
    if (VALORES_VAZIOS.has(txt.toLowerCase()) || ehFaltaVinculada(val)) return "";

    const num = parseFloat(txt.replace(",", "."));
    if (isNaN(num)) return "";

    // Formata com 1 casa decimal (ex: 7.0, 7.5, 10.0)
    const formatado = num.toFixed(1);
    if (formato === "virgula") {
      return formatado.replace(".", ",");
    }
    return formatado;
  }

  /**
   * Le e analisa a estrutura de um arquivo Excel (.xlsx) a partir de um ArrayBuffer ou binario.
   * Retorna metadados das abas disponiveis.
   */
  function carregarWorkbook(arrayBufferOuDados, XLSX_LIB) {
    const xlsx = XLSX_LIB || (typeof XLSX !== "undefined" ? XLSX : null);
    if (!xlsx) {
      throw new Error("Biblioteca SheetJS (XLSX) não encontrada.");
    }
    const workbook = xlsx.read(arrayBufferOuDados, { type: "array" });
    return {
      workbook,
      abas: workbook.SheetNames || []
    };
  }

  /**
   * Localiza dinamicamente a linha que contém os cabeçalhos das colunas (analisa até as primeiras 25 linhas).
   */
  function encontrarLinhaCabecalho(matriz) {
    if (!matriz || !matriz.length) return 0;
    const limite = Math.min(matriz.length, 25);
    let melhorLinha = 0;
    let melhorPontuacao = -1;

    for (let r = 0; r < limite; r++) {
      const linha = matriz[r] || [];
      const celulas = linha.map(c => String(c || "").trim());
      const preenchidas = celulas.filter(Boolean);
      if (preenchidas.length < 2) continue;

      let score = preenchidas.length;
      for (const cel of celulas) {
        const u = cel.toUpperCase();
        if (
          u === "NOME" || u.includes("NOME DO") || u.includes("ESTUDANTE") ||
          u.includes("ALUNO") || u === "DISCENTE" || u.includes("NOME COMPLETO") ||
          u.includes("NOMES")
        ) score += 20;
        if (
          u === "MATRÍCULA" || u === "MATRICULA" || u === "Nº" ||
          u === "NUMERO" || u === "N." || u === "ORDEM" || u === "MAT"
        ) score += 10;
        if (
          u.includes("PROVA") || u.includes("ATIVIDADE") || u.includes("AVALIA") ||
          u.includes("SIMULADO") || u.includes("UNIDADE") || u.includes("TRABALHO") ||
          u.includes("SEMINARIO") || u.includes("SEMINÁRIO") || u.includes("TESTE") ||
          /^(?:P|AV|N|ACT|AT|T)[1-9]$/i.test(u)
        ) score += 5;
      }

      if (score > melhorPontuacao) {
        melhorPontuacao = score;
        melhorLinha = r;
      }
    }

    return melhorLinha;
  }

  /**
   * Inspeciona uma aba especifica e retorna as colunas detectadas e pre-visualizacao das linhas.
   */
  function inspecionarAba(workbook, nomeAba, XLSX_LIB) {
    const xlsx = XLSX_LIB || (typeof XLSX !== "undefined" ? XLSX : null);
    const sheet = workbook.Sheets[nomeAba || workbook.SheetNames[0]];
    if (!sheet) {
      throw new Error(`Aba '${nomeAba}' não encontrada.`);
    }

    // Converte para matriz de linhas (valores brutos e strings)
    const matriz = xlsx.utils.sheet_to_json(sheet, { header: 1, defval: "" });
    if (!matriz || !matriz.length) {
      return { colunas: [], linhasAmostra: [], colunaNomeSugerida: "A" };
    }

    // Encontra dinamicamente a linha de cabecalho da tabela
    const idxCabecalho = encontrarLinhaCabecalho(matriz);

    const linhaCabecalho = matriz[idxCabecalho] || [];
    const maxCols = Math.max(...matriz.slice(idxCabecalho, idxCabecalho + 25).map(r => r.length), linhaCabecalho.length);

    // Mapeia metadados de cada coluna
    const colunas = [];
    for (let c = 0; c < maxCols; c++) {
      const letra = indiceParaLetra(c);
      const titulo = String(linhaCabecalho[c] || "").trim() || `Coluna ${letra}`;
      colunas.push({
        indice: c,
        letra: letra,
        titulo: titulo
      });
    }

    // Heuristica para detectar a coluna de nomes dos alunos:
    // 1. Prioriza colunas cujo cabeçalho explicita termos de nome do estudante (NOME, ESTUDANTE, ALUNO, DISCENTE)
    let idxNomeDetectado = -1;
    for (let c = 0; c < maxCols; c++) {
      const tit = String(linhaCabecalho[c] || "").trim().toUpperCase();
      if (tit === "NOME" || tit === "NOME DO ALUNO" || tit === "NOME DO ESTUDANTE" ||
          tit === "ESTUDANTE" || tit === "ALUNO" || tit === "DISCENTE" ||
          tit.includes("NOME DO") || tit.includes("NOME DE")) {
        idxNomeDetectado = c;
        break;
      }
    }

    const linhasAmostra = matriz.slice(idxCabecalho + 1, idxCabecalho + 20);

    // 2. Se o cabeçalho não tem coluna explícita, analisa a frequência de nomes (>= 2 palavras) nas primeiras colunas
    if (idxNomeDetectado === -1) {
      let melhorCol = 0;
      let maxNomes = -1;
      const limiteCols = Math.min(maxCols, 6);
      for (let c = 0; c < limiteCols; c++) {
        let cont = 0;
        for (const r of linhasAmostra) {
          const v = String(r[c] || "").trim();
          if (v.split(/\s+/).length >= 2 && /[A-Za-z]/.test(v)) cont++;
        }
        if (cont > maxNomes) {
          maxNomes = cont;
          melhorCol = c;
        }
      }
      idxNomeDetectado = melhorCol;
    }

    const colunaNomeSugerida = indiceParaLetra(idxNomeDetectado);

    // Sugestao automatica das colunas de avaliacao (ignora totais, medias e resultados finais)
    const idxNome = idxNomeDetectado;
    const termosIgnorarFim = ["TOTAL", "MEDIA", "MÉDIA", "GERAL", "FINAL", "RESULTADO"];
    const termosPular = ["SITUACAO", "SITUAÇÃO", "RECUPERACAO", "RECUPERAÇÃO", "REC", "FALTA", "FALTAS", "TURMA", "OBS", "OBSERVAÇÃO", "OBSERVACAO"];
    const colunasNotasSugeridas = [];
    const colunasNotasSugeridasDetalhes = [];

    for (let c = idxNome + 1; c < colunas.length; c++) {
      const col = colunas[c];
      const titUpper = col.titulo.toUpperCase();

      // Se atingiu uma coluna de total ou resumo final, encerra as atividades
      if (termosIgnorarFim.some(t => titUpper.includes(t))) break;

      // Se for coluna intermediária de faltas, recuperação ou situação, pula sem interromper as seguintes
      if (termosPular.some(t => titUpper.includes(t))) continue;

      const titOriginal = String(linhaCabecalho[c] || "").trim();
      const temDadoAmostra = linhasAmostra.some(r => {
        const val = String(r[c] || "").trim();
        return val !== "" && !VALORES_VAZIOS.has(val.toLowerCase());
      });

      // Se a coluna não possui título próprio e nenhuma linha de amostra possui valor, verifica se é fim real da planilha
      if (!titOriginal && !temDadoAmostra) {
        const temColunaPosterior = colunas.slice(c + 1).some((_, offset) => {
          const proxIdx = c + 1 + offset;
          const proxTit = String(linhaCabecalho[proxIdx] || "").trim();
          const proxTemDado = linhasAmostra.some(r => {
            const v = String(r[proxIdx] || "").trim();
            return v !== "" && !VALORES_VAZIOS.has(v.toLowerCase());
          });
          return Boolean(proxTit || proxTemDado);
        });
        if (!temColunaPosterior) {
          break; // Fim real da planilha
        }
        continue; // Apenas coluna intermediária vazia
      }

      colunasNotasSugeridas.push(col.letra);
      colunasNotasSugeridasDetalhes.push({
        letra: col.letra,
        titulo: col.titulo
      });
    }

    return {
      idxCabecalho,
      colunas,
      colunaNomeSugerida,
      colunasNotasSugeridas,
      colunasNotasSugeridasDetalhes,
      totalLinhas: matriz.length,
      linhasAmostra: linhasAmostra.slice(0, 5)
    };
  }

  /**
   * Extrai os dados dos alunos e notas a partir da aba e das colunas especificadas.
   *
   * @param {Object} workbook - objeto workbook do SheetJS
   * @param {string} nomeAba - nome da aba selecionada
   * @param {string} colunaNome - letra da coluna contendo os nomes (ex: 'A' ou 'B')
   * @param {Array<string>} letrasColunasNotas - lista de letras de colunas com notas (ex: ['C', 'D', 'E'])
   * @param {string} formato - 'ponto' ou 'virgula'
   * @param {Object} XLSX_LIB - referencia opcional a lib SheetJS
   */
  function extrairDadosNotas(workbook, nomeAba, colunaNome, letrasColunasNotas, formato = "ponto", XLSX_LIB) {
    const xlsx = XLSX_LIB || (typeof XLSX !== "undefined" ? XLSX : null);
    const sheet = workbook.Sheets[nomeAba || workbook.SheetNames[0]];
    if (!sheet) {
      throw new Error(`Aba '${nomeAba}' não encontrada.`);
    }

    const matriz = xlsx.utils.sheet_to_json(sheet, { header: 1, defval: "" });
    if (!matriz || !matriz.length) {
      return { alunos: [], titulosAtividades: [] };
    }

    // Detecta indice do cabecalho
    // Detecta dinamicamente o indice do cabecalho
    const idxCabecalho = encontrarLinhaCabecalho(matriz);

    const idxNome = letraParaIndice(colunaNome || "A");
    const indicesNotas = (letrasColunasNotas || []).map(letraParaIndice);

    const linhaCabecalho = matriz[idxCabecalho] || [];
    const titulosAtividades = indicesNotas.map((idx, pos) => {
      const tit = String(linhaCabecalho[idx] || "").trim();
      return tit || `Atividade ${pos + 1} (${indiceParaLetra(idx)})`;
    });

    const alunos = [];
    const linhasDados = matriz.slice(idxCabecalho + 1);

    for (let i = 0; i < linhasDados.length; i++) {
      const linha = linhasDados[i];
      if (!linha || linha.length === 0) continue;

      const nomeRaw = String(linha[idxNome] || "").replace(/^['"]+|['"]+$/g, "").trim();
      // Ignora linhas sem nome, cabecalhos repetidos ou notas de rodape
      if (!nomeRaw || nomeRaw.length < 3 || !/[A-Za-z]/.test(nomeRaw)) continue;

      const nomeUpper = nomeRaw.toUpperCase();
      if (nomeUpper.includes("TOTAL") || nomeUpper.includes("MÉDIA") || nomeUpper.includes("MEDIA") ||
          nomeUpper.includes("PROFESSOR") || nomeUpper.includes("DISCIPLINA") ||
          nomeUpper === "NOME" || nomeUpper.startsWith("NOME DO") || nomeUpper === "NOME DO ALUNO" ||
          nomeUpper === "NOME DO ESTUDANTE" || nomeUpper === "ESTUDANTE" || nomeUpper === "ALUNO" ||
          nomeUpper.startsWith("COORDENADOR") || nomeUpper.startsWith("DIRECAO") || nomeUpper.startsWith("DIREÇÃO")) {
        continue;
      }

      const notas = [];
      const fv = [];

      for (const idxNota of indicesNotas) {
        const valRaw = linha[idxNota];
        const ehFv = ehFaltaVinculada(valRaw);
        const notaFormatada = formatarNota(valRaw, formato);

        fv.push(ehFv);
        notas.push(notaFormatada);
      }

      alunos.push({
        linhaOriginal: idxCabecalho + 2 + i,
        nome: nomeRaw,
        notas: notas,
        fv: fv,
        temFv: fv.some(Boolean)
      });
    }

    return {
      alunos,
      titulosAtividades,
      totalAlunos: alunos.length
    };
  }

  /**
   * Sanitiza nome de aba para o padrão do Excel (máximo 31 caracteres, sem : \ / ? * [ ])
   */
  function sanitizarNomeAba(nome) {
    if (!nome) return "Turma";
    let limpo = String(nome).replace(/[:\\/?*\[\]]/g, "").trim();
    limpo = limpo.replace(/\s+/g, " ");
    return limpo.slice(0, 31) || "Turma";
  }

  /**
   * Sanitiza nome de arquivo para o sistema de arquivos (sem caracteres proibidos)
   */
  function sanitizarNomeArquivo(nome) {
    if (!nome) return "Planilha_Notas.xlsx";
    let limpo = String(nome).replace(/[\\/:*?"<>|]/g, "_").trim();
    limpo = limpo.replace(/\s+/g, "_");
    if (!limpo.toLowerCase().endsWith(".xlsx")) limpo += ".xlsx";
    return limpo;
  }

  /**
   * Gera uma planilha Excel modelo (.xlsx) pronta para preenchimento.
   *
   * @param {Object} dadosTurma
   * @param {string} dadosTurma.turma - Nome ou código da turma (ex: "SEGUMAT1SA")
   * @param {string} dadosTurma.componente - Nome do componente curricular
   * @param {number|string} dadosTurma.unidade - Número da unidade (ex: 1, 2)
   * @param {Array<string>} dadosTurma.atividades - Títulos das atividades (ex: ["Simulado (4.0)", "Gincana (2.0)"])
   * @param {Array<Object|string>} dadosTurma.alunos - Lista de alunos [{ nome, matricula, notas }] ou ["NOME"]
   * @param {Object} opcoes
   * @param {boolean} opcoes.incluirFormulaTotal - Se true, inclui coluna Total com =SOMA(B2:D2)
   * @param {boolean} opcoes.preservarNotasExistentes - Se true, inclui notas já digitadas na tela
   * @param {Object} opcoes.XLSX_LIB - Referência opcional à biblioteca SheetJS
   */
  function gerarPlanilhaModelo(dadosTurma, opcoes = {}) {
    const xlsx = opcoes.XLSX_LIB || (typeof XLSX !== "undefined" ? XLSX : null);
    if (!xlsx) {
      throw new Error("Biblioteca SheetJS (XLSX) não encontrada.");
    }

    const turmaNome = (dadosTurma && dadosTurma.turma) ? String(dadosTurma.turma).trim() : "Turma";
    const componente = (dadosTurma && dadosTurma.componente) ? String(dadosTurma.componente).trim() : "";
    const unidadeNum = (dadosTurma && dadosTurma.unidade) ? parseInt(dadosTurma.unidade, 10) || 1 : 1;
    const atividades = (dadosTurma && Array.isArray(dadosTurma.atividades) && dadosTurma.atividades.length)
      ? dadosTurma.atividades
      : ["Atividade 1", "Atividade 2", "Atividade 3"];
    const alunos = (dadosTurma && Array.isArray(dadosTurma.alunos)) ? dadosTurma.alunos : [];

    const incluirFormulaTotal = opcoes.incluirFormulaTotal !== false;
    const preservarNotas = !!opcoes.preservarNotasExistentes;

    const wb = xlsx.utils.book_new();

    // 1. Linha de Cabeçalho
    const cabecalhos = ["Nome do Estudante", ...atividades];
    if (incluirFormulaTotal) {
      cabecalhos.push("Total Unidade");
    }

    const linhas = [cabecalhos];
    let maxNomeLen = "Nome do Estudante".length;

    // 2. Linhas dos Estudantes
    alunos.forEach((aluno, idxAluno) => {
      const nome = typeof aluno === "string" ? aluno : (aluno && aluno.nome ? aluno.nome : `Estudante ${idxAluno + 1}`);
      if (nome.length > maxNomeLen) maxNomeLen = nome.length;

      const linha = [nome];
      const notasExistentes = (aluno && Array.isArray(aluno.notas)) ? aluno.notas : [];

      atividades.forEach((_, idxAtv) => {
        let val = "";
        if (preservarNotas && idxAtv < notasExistentes.length) {
          val = notasExistentes[idxAtv] || "";
        }
        linha.push(val);
      });

      if (incluirFormulaTotal && atividades.length > 0) {
        const colIni = "B";
        const colFim = indiceParaLetra(atividades.length); // ex: se 3 atividades, B até D
        const numLinha = idxAluno + 2; // linha 1 é cabeçalho, dados começam na linha 2
        // SheetJS suporta objetos de célula { f: formula } para gerar fórmulas nativas no Excel
        linha.push({ f: `SUM(${colIni}${numLinha}:${colFim}${numLinha})` });
      }

      linhas.push(linha);
    });

    const ws = xlsx.utils.aoa_to_sheet(linhas);

    // 3. Ajuste de Larguras das Colunas (!cols)
    const colWidths = [
      { wch: Math.min(Math.max(28, maxNomeLen + 2), 55) } // Coluna Nome
    ];
    atividades.forEach(tit => {
      colWidths.push({ wch: Math.max(14, String(tit).length + 2) });
    });
    if (incluirFormulaTotal) {
      colWidths.push({ wch: 15 });
    }
    ws["!cols"] = colWidths;

    // 4. Nome da Aba Sanitizado
    let sugestaoAba = `${turmaNome}_U${unidadeNum}`;
    let nomeAba = sanitizarNomeAba(sugestaoAba);
    xlsx.utils.book_append_sheet(wb, ws, nomeAba);

    // 5. Geração do Arquivo Binário
    const arrayBuffer = xlsx.write(wb, { bookType: "xlsx", type: "array" });

    // 6. Nome Sugerido do Arquivo
    const compSufixo = componente ? `_${componente.slice(0, 15)}` : "";
    const nomeArquivo = sanitizarNomeArquivo(`Notas_${turmaNome}${compSufixo}_U${unidadeNum}.xlsx`);

    return {
      workbook: wb,
      arrayBuffer: arrayBuffer,
      nomeArquivo: nomeArquivo,
      nomeAba: nomeAba,
      totalAlunos: alunos.length,
      totalAtividades: atividades.length
    };
  }

  const api = {
    letraParaIndice,
    indiceParaLetra,
    ehFaltaVinculada,
    formatarNota,
    carregarWorkbook,
    encontrarLinhaCabecalho,
    inspecionarAba,
    extrairDadosNotas,
    sanitizarNomeAba,
    sanitizarNomeArquivo,
    gerarPlanilhaModelo
  };

  root.SgnExcel = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
