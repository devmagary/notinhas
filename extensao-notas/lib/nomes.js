/*
 * Comparacao robusta de nomes de estudantes.
 * Porta direta da logica de sigeduc_core.py (normalizar_nome, canonicalizar_palavra,
 * nomes_sao_iguais, encontrar_melhor_aluno).
 *
 * Garante:
 *  - Acentos e cedilha ignorados (REBOUCAS == REBOUÇAS).
 *  - Variacoes ortograficas comuns (LUIS/LUIZ, SOUZA/SOUSA, MATHEUS/MATEUS, HELOYSA/ELOISA).
 *  - Nunca cruza alunos com prenomes iguais e sobrenomes diferentes
 *    (MARIA VITORIA SANTOS LISBOA != MARIA VITORIA TOSTA DO AMARAL).
 *
 * Funciona no navegador (globalThis.SgnNomes) e no Node (module.exports) para testes.
 */
(function (root) {
  "use strict";

  const PREPOSICOES = new Set(["DE", "DA", "DO", "DAS", "DOS", "E"]);
  const SUFIXOS = new Set(["JUNIOR", "JR", "FILHO", "NETO", "SOBRINHO", "SEGUNDO", "TERCEIRO"]);
  const STATUS_ALUNOS = new Set([
    "TRANSFERIDO", "TRANSFERIDA", "TRANSF",
    "CANCELADO", "CANCELADA", "CANCELAMENTO",
    "DESISTENTE", "DESISTENCIA",
    "REMANEJADO", "REMANEJADA", "REMANEJAMENTO",
    "INATIVO", "INATIVA",
    "ABANDONO", "FALECIDO", "FALECIDA",
    "EVADIDO", "EVADIDA", "EVASAO",
    "RECLASSIFICADO", "RECLASSIFICADA", "RECLASSIFICACAO"
  ]);

  function normalizar(nome) {
    if (nome === null || nome === undefined) return "";
    return String(nome)
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^A-Za-z\s]/g, " ")
      .toUpperCase()
      .split(/\s+/)
      .filter(Boolean)
      .join(" ");
  }

  function canonicalizar(p) {
    p = p.toUpperCase();
    if (p.length > 1 && p[0] === "H" && "AEIOU".includes(p[1])) p = p.slice(1);
    p = p.replace(/TH/g, "T").replace(/PH/g, "F").replace(/CH/g, "X");
    p = p.replace(/CT/g, "T").replace(/PT/g, "T").replace(/SC/g, "S");
    p = p.replace(/Y/g, "I").replace(/W/g, "V");
    p = p.replace(/Z/g, "S");
    p = p.replace(/K/g, "C");
    p = p.replace(/([B-DF-HJ-NP-TV-Z])\1+/g, "$1");
    return p;
  }

  function palavrasRelevantes(nome, canon = true) {
    const palavras = normalizar(nome).split(" ").filter((p) => p && !PREPOSICOES.has(p) && !STATUS_ALUNOS.has(p));
    return canon ? palavras.map(canonicalizar) : palavras;
  }

  function escaparRegex(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function contemPalavras(texto, trecho) {
    if (!texto || !trecho) return false;
    return new RegExp("\\b" + escaparRegex(trecho) + "\\b").test(texto);
  }

  /** True somente quando os dois nomes representam com seguranca a mesma pessoa. */
  function nomesSaoIguais(nomeA, nomeB) {
    const aNorm = normalizar(nomeA);
    const bNorm = normalizar(nomeB);
    if (!aNorm || !bNorm) return false;
    if (aNorm === bNorm) return true;

    let pA = palavrasRelevantes(nomeA, true);
    let pB = palavrasRelevantes(nomeB, true);
    if (!pA.length || !pB.length) return false;
    if (pA.join(" ") === pB.join(" ")) return true;

    // Primeiro nome deve ser identico
    if (pA[0] !== pB[0]) return false;

    // Sufixos de parentesco (Junior, Filho, Neto...)
    let ultA = pA[pA.length - 1];
    let ultB = pB[pB.length - 1];
    if (SUFIXOS.has(ultA) && !SUFIXOS.has(ultB)) {
      pA = pA.slice(0, -1);
      if (!pA.length) return false;
      ultA = pA[pA.length - 1];
    } else if (SUFIXOS.has(ultB) && !SUFIXOS.has(ultA)) {
      pB = pB.slice(0, -1);
      if (!pB.length) return false;
      ultB = pB[pB.length - 1];
    }

    // Ultimo sobrenome deve ser compativel (aceita abreviacao de 1 letra)
    if (pA.length >= 2 && pB.length >= 2 && ultA !== ultB) {
      const abrev = (ultA.length === 1 && ultB.startsWith(ultA)) || (ultB.length === 1 && ultA.startsWith(ultB));
      if (!abrev) return false;
    }

    // Conflito de palavras intermediarias completas (ex: ARAUJO vs OLIVEIRA)
    const setA = new Set(pA);
    const setB = new Set(pB);
    const soA = [...setA].filter((x) => !setB.has(x));
    const soB = [...setB].filter((x) => !setA.has(x));
    const conflitosA = soA.filter((pa) => !(pa.length === 1 && soB.some((pb) => pb.startsWith(pa))));
    const conflitosB = soB.filter((pb) => !(pb.length === 1 && soA.some((pa) => pa.startsWith(pb))));
    if (conflitosA.length && conflitosB.length) return false;

    const menor = pA.length <= pB.length ? pA : pB;
    const maior = pA.length <= pB.length ? pB : pA;
    if (menor.length < 2) return false;

    const setMaior = new Set(maior);
    const comuns = new Set(menor.filter((x) => setMaior.has(x)));
    return comuns.size / maior.length >= 0.65;
  }

  /**
   * Localiza o melhor candidato para o nome exibido na tela.
   * Retorna { candidato, nivel } onde nivel e "exato" | "contido" | "aproximado", ou null.
   */
  function encontrarMelhor(textoTela, candidatos) {
    if (!textoTela || !candidatos || !candidatos.length) return null;
    const texto = normalizar(textoTela);
    if (!texto) return null;

    for (const c of candidatos) {
      if (normalizar(c) === texto) return { candidato: c, nivel: "exato" };
    }

    const contidos = [];
    for (const c of candidatos) {
      const cn = normalizar(c);
      if (cn.split(" ").length >= 2 && (contemPalavras(texto, cn) || contemPalavras(cn, texto))) {
        contidos.push({ c, tam: cn.length });
      }
    }
    if (contidos.length === 1) return { candidato: contidos[0].c, nivel: "contido" };
    if (contidos.length > 1) {
      contidos.sort((a, b) => b.tam - a.tam);
      // Empate de tamanho = ambiguo; nao arrisca
      if (contidos[0].tam !== contidos[1].tam) return { candidato: contidos[0].c, nivel: "contido" };
    }

    const canon = candidatos.filter((c) => nomesSaoIguais(c, textoTela));
    if (canon.length === 1) return { candidato: canon[0], nivel: "aproximado" };
    if (canon.length > 1) {
      const pTela = new Set(palavrasRelevantes(textoTela, true));
      let melhor = null;
      let melhorScore = -1;
      let empate = false;
      for (const c of canon) {
        const score = palavrasRelevantes(c, true).filter((p) => pTela.has(p)).length;
        if (score > melhorScore) {
          melhorScore = score;
          melhor = c;
          empate = false;
        } else if (score === melhorScore) {
          empate = true;
        }
      }
      if (!empate) return { candidato: melhor, nivel: "aproximado" };
    }
    return null;
  }

  /**
   * Casa uma lista de nomes da tela com uma lista de nomes da planilha garantindo
   * que um aluno da planilha nunca seja usado em duas linhas da tela.
   * Retorna Map<indiceTela, { indicePlanilha, nivel }>.
   */
  function casarListas(nomesTela, nomesPlanilha) {
    const prioridade = { exato: 3, contido: 2, aproximado: 1 };
    const propostas = [];
    nomesTela.forEach((nomeTela, iTela) => {
      const r = encontrarMelhor(nomeTela, nomesPlanilha);
      if (r) {
        propostas.push({ iTela, iPlan: nomesPlanilha.indexOf(r.candidato), nivel: r.nivel });
      }
    });

    // Se dois nomes da tela disputam o mesmo aluno, fica o de maior certeza; empate = nenhum.
    const porPlanilha = new Map();
    for (const p of propostas) {
      if (!porPlanilha.has(p.iPlan)) porPlanilha.set(p.iPlan, []);
      porPlanilha.get(p.iPlan).push(p);
    }
    const resultado = new Map();
    const conflitos = [];
    for (const [iPlan, lista] of porPlanilha) {
      lista.sort((a, b) => prioridade[b.nivel] - prioridade[a.nivel]);
      if (lista.length === 1 || prioridade[lista[0].nivel] > prioridade[lista[1].nivel]) {
        resultado.set(lista[0].iTela, { indicePlanilha: iPlan, nivel: lista[0].nivel });
        lista.slice(1).forEach((p) => conflitos.push({ iTela: p.iTela, iPlan }));
      } else {
        lista.forEach((p) => conflitos.push({ iTela: p.iTela, iPlan }));
      }
    }
    return { pares: resultado, conflitos };
  }

  const api = { normalizar, canonicalizar, palavrasRelevantes, nomesSaoIguais, encontrarMelhor, casarListas };
  root.SgnNomes = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
