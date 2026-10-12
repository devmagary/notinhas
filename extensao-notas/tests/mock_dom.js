/**
 * Implementação leve e autocontida de DOM simulado para testes automatizados
 * no ambiente Node.js da extensão Chromium SIGEduc Auto.
 */

class ClassList {
  constructor() {
    this._classes = new Set();
  }
  add(...classes) {
    classes.forEach(c => c && this._classes.add(String(c).trim()));
  }
  remove(...classes) {
    classes.forEach(c => this._classes.delete(String(c).trim()));
  }
  contains(c) {
    return this._classes.has(String(c).trim());
  }
  toString() {
    return Array.from(this._classes).join(" ");
  }
}

class MockElement {
  constructor(tagName) {
    this.tagName = tagName.toUpperCase();
    this.id = "";
    this._className = "";
    this.classList = new ClassList();
    this.children = [];
    this.parentElement = null;
    this.attributes = {};
    this.style = {};
    this.value = "";
    this.checked = false;
    this.disabled = false;
    this.readOnly = false;
    this._innerText = "";
    this.listeners = {};
    this.offsetParent = this; // Simula visibilidade por padrão
  }

  get className() {
    return this.classList.toString();
  }

  set className(val) {
    this._className = val || "";
    this.classList = new ClassList();
    if (val) {
      val.split(/\s+/).forEach(c => c && this.classList.add(c));
    }
  }

  get cellIndex() {
    if (!this.parentElement || !this.parentElement.children) return 0;
    return this.parentElement.children.indexOf(this);
  }

  get firstChild() {
    return this.children[0] || null;
  }

  get innerText() {
    if (this._innerText) return this._innerText;
    return this.children.map(c => c.innerText).join(" ").trim();
  }

  set innerText(txt) {
    this._innerText = txt || "";
  }

  get textContent() {
    return this.innerText;
  }

  set textContent(txt) {
    this.innerText = txt;
  }

  setAttribute(k, v) {
    const val = String(v);
    this.attributes[k] = val;
    if (k === "id") this.id = val;
    if (k === "class") this.className = val;
    if (k === "type") this.type = val;
    if (k === "value") this.value = val;
    if (k === "name") this.name = val;
  }

  getAttribute(k) {
    if (k === "id") return this.id || null;
    if (k === "class") return this.className || null;
    if (k === "type") return this.type || null;
    if (k === "value") return this.value || null;
    if (k === "name") return this.name || null;
    return this.attributes[k] || null;
  }

  appendChild(child) {
    if (!child) return child;
    child.parentElement = this;
    this.children.push(child);
    return child;
  }

  insertBefore(newChild, refChild) {
    if (!newChild) return newChild;
    newChild.parentElement = this;
    if (!refChild) {
      this.children.push(newChild);
      return newChild;
    }
    const idx = this.children.indexOf(refChild);
    if (idx === -1) {
      this.children.push(newChild);
    } else {
      this.children.splice(idx, 0, newChild);
    }
    return newChild;
  }

  addEventListener(event, fn) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(fn);
  }

  dispatchEvent(event) {
    const evtType = event.type || event;
    if (this.listeners[evtType]) {
      this.listeners[evtType].forEach(fn => fn(event));
    }
    if (event.bubbles && this.parentElement) {
      this.parentElement.dispatchEvent(event);
    }
    return true;
  }

  focus() {}
  scrollIntoView() {}
  click() {
    if (this.attributes && this.attributes.type === "checkbox") {
      this.checked = !this.checked;
      this.dispatchEvent({ type: "click", bubbles: true });
      this.dispatchEvent({ type: "change", bubbles: true });
      return;
    }
    this.dispatchEvent({ type: "click", bubbles: true });
  }

  matches(selector) {
    const s = selector.trim();
    if (!s) return false;

    if (s.includes(",")) {
      return s.split(",").some(part => this.matches(part.trim()));
    }

    // Seletor de ID (ex: #formulario:result ou #formulario\\:result)
    if (s.startsWith("#")) {
      const targetId = s.slice(1).replace(/\\/g, "");
      return this.id === targetId;
    }

    // Seletor de classe (ex: .rich-table ou .avaliacao)
    if (s.startsWith(".")) {
      return this.classList.contains(s.slice(1));
    }

    // Seletor com atributo (ex: table[id='...'] ou input[id*=':av__'] ou input[type='text'])
    const attrMatch = s.match(/^([a-zA-Z0-9_-]*)\[([a-zA-Z0-9_-]+)([*^$]?=)(?:'|")?([^'"\]]*)(?:'|")?\]$/);
    if (attrMatch) {
      const tag = attrMatch[1];
      const attrName = attrMatch[2];
      const op = attrMatch[3];
      const val = attrMatch[4];

      if (tag && this.tagName !== tag.toUpperCase()) return false;
      const attrVal = this.getAttribute(attrName) || this[attrName] || "";
      if (op === "*=") return String(attrVal).includes(val);
      if (op === "^=") return String(attrVal).startsWith(val);
      if (op === "$=") return String(attrVal).endsWith(val);
      return String(attrVal) === val;
    }

    // Seletor com classe concatenada (ex: input.avaliacao)
    const tagClassMatch = s.match(/^([a-zA-Z0-9_-]+)\.([a-zA-Z0-9_-]+)$/);
    if (tagClassMatch) {
      const tag = tagClassMatch[1];
      const cls = tagClassMatch[2];
      return this.tagName === tag.toUpperCase() && this.classList.contains(cls);
    }

    // Seletor de tag simples
    return this.tagName === s.toUpperCase();
  }

  closest(selector) {
    let cur = this;
    while (cur) {
      if (cur.matches && cur.matches(selector)) return cur;
      cur = cur.parentElement;
    }
    return null;
  }

  querySelector(selector) {
    const list = this.querySelectorAll(selector);
    return list.length ? list[0] : null;
  }

  querySelectorAll(selector) {
    const parts = selector.split(",").map(p => p.trim()).filter(Boolean);
    const results = [];

    const walk = (node) => {
      for (const child of node.children) {
        let matched = false;
        for (const p of parts) {
          // Trata seletores com espaço descendente simples (ex: "tbody tr" ou "thead th")
          if (p.includes(" ")) {
            const sub = p.split(/\s+/);
            if (sub.length === 2 && child.matches(sub[1])) {
              let anc = child.parentElement;
              while (anc && anc !== node.parentElement) {
                if (anc.matches && anc.matches(sub[0])) {
                  matched = true;
                  break;
                }
                anc = anc.parentElement;
              }
            }
          } else if (child.matches(p)) {
            matched = true;
          }

          if (matched) break;
        }

        if (matched && !results.includes(child)) {
          results.push(child);
        }
        walk(child);
      }
    };

    walk(this);
    return results;
  }
}

class MockDocument {
  constructor() {
    this.body = new MockElement("BODY");
  }

  createElement(tag) {
    return new MockElement(tag);
  }

  getElementById(id) {
    const cleanId = String(id).replace(/\\/g, "");
    const find = (node) => {
      if (node.id === cleanId) return node;
      for (const c of node.children) {
        const r = find(c);
        if (r) return r;
      }
      return null;
    };
    return find(this.body);
  }

  querySelector(selector) {
    return this.body.querySelector(selector);
  }

  querySelectorAll(selector) {
    return this.body.querySelectorAll(selector);
  }
}

function criarAmbienteDOM() {
  const doc = new MockDocument();
  const win = {
    document: doc,
    location: { href: "https://sigeduc.educacao.ba.gov.br/lancarNotas" },
    getComputedStyle: () => ({ color: "rgb(0, 0, 0)" })
  };

  class Event {
    constructor(type, opt = {}) {
      this.type = type;
      this.bubbles = !!opt.bubbles;
    }
  }

  class KeyboardEvent extends Event {
    constructor(type, opt = {}) {
      super(type, opt);
      this.key = opt.key || "";
      this.keyCode = opt.keyCode || 0;
    }
  }

  return { document: doc, window: win, Event, KeyboardEvent };
}

/**
 * Cria a tabela HTML do RichFaces no DOM simulado exatamente como na tela do SIGEduc.
 */
function montarTabelaTurma(doc, nomesAlunos, qtdAvaliacoes = 3, titulosAtividades = null) {
  doc.body.children = []; // limpa

  const tabela = doc.createElement("table");
  tabela.id = "formulario:result";
  tabela.className = "rich-table listagem";

  // thead
  const thead = doc.createElement("thead");
  const trHead = doc.createElement("tr");

  const thNum = doc.createElement("th"); thNum.innerText = "Nº"; trHead.appendChild(thNum);
  const thMat = doc.createElement("th"); thMat.innerText = "Matrícula"; trHead.appendChild(thMat);
  const thNome = doc.createElement("th"); thNome.innerText = "Nome do Estudante"; trHead.appendChild(thNome);

  for (let c = 1; c <= qtdAvaliacoes; c++) {
    const thAv = doc.createElement("th");
    thAv.innerText = (titulosAtividades && titulosAtividades[c - 1]) ? titulosAtividades[c - 1] : `Atividade ${c}`;
    trHead.appendChild(thAv);
  }
  const thTotal = doc.createElement("th"); thTotal.innerText = "Total Unidade"; trHead.appendChild(thTotal);
  const thFv = doc.createElement("th"); thFv.innerText = "Falta Vinculada"; trHead.appendChild(thFv);

  thead.appendChild(trHead);
  tabela.appendChild(thead);

  // tbody
  const tbody = doc.createElement("tbody");

  nomesAlunos.forEach((nome, idx) => {
    const tr = doc.createElement("tr");
    tr.id = `formulario:result:${idx}`;

    const tdNum = doc.createElement("td"); tdNum.innerText = String(idx + 1); tr.appendChild(tdNum);
    const tdMat = doc.createElement("td"); tdMat.innerText = `2024${String(idx + 1).padStart(4, "0")}`; tr.appendChild(tdMat);

    // Nome como link <a> dentro de <td>
    const tdNome = doc.createElement("td");
    const aNome = doc.createElement("a");
    aNome.innerText = nome;
    aNome.setAttribute("href", "#");
    tdNome.appendChild(aNome);
    tr.appendChild(tdNome);

    // Inputs de avaliações
    for (let c = 1; c <= qtdAvaliacoes; c++) {
      const tdAv = doc.createElement("td");
      const inp = doc.createElement("input");
      inp.setAttribute("type", "text");
      inp.className = "avaliacao";
      inp.id = `formulario:result:${idx}:av__${c}`;
      tdAv.appendChild(inp);
      tr.appendChild(tdAv);
    }

    // Input de total da unidade (:nu__)
    const tdTotal = doc.createElement("td");
    const inpTotal = doc.createElement("input");
    inpTotal.setAttribute("type", "text");
    inpTotal.className = "notaUnidade";
    inpTotal.id = `formulario:result:${idx}:nu__1`;
    inpTotal.readOnly = true;
    tdTotal.appendChild(inpTotal);
    tr.appendChild(tdTotal);

    // Checkbox de Falta Vinculada
    const tdFv = doc.createElement("td");
    const chkFv = doc.createElement("input");
    chkFv.setAttribute("type", "checkbox");
    chkFv.id = `formulario:result:${idx}:fv__1`;
    tdFv.appendChild(chkFv);
    tr.appendChild(tdFv);

    tbody.appendChild(tr);
  });

  tabela.appendChild(tbody);
  doc.body.appendChild(tabela);

  return tabela;
}

/**
 * Cria a tabela de frequência (#tableAlunos) no DOM simulado.
 */
function montarTabelaFrequencia(doc, nomesAlunos, opcoes = {}) {
  doc.body.children = [];

  const tabela = doc.createElement("table");
  tabela.id = "tableAlunos";
  tabela.className = "rich-table listagem";

  const thead = doc.createElement("thead");
  const trHead = doc.createElement("tr");
  const thNum = doc.createElement("th"); thNum.innerText = "Nº"; trHead.appendChild(thNum);
  const thMat = doc.createElement("th"); thMat.innerText = "Matrícula"; trHead.appendChild(thMat);
  const thNome = doc.createElement("th"); thNome.innerText = "Nome do Aluno"; trHead.appendChild(thNome);

  const qtdPeriodos = opcoes.qtdPeriodos || 1;
  for (let p = 1; p <= qtdPeriodos; p++) {
    const thA = doc.createElement("th");
    thA.innerText = `Falta (Aula ${p})`;
    trHead.appendChild(thA);
  }
  thead.appendChild(trHead);
  tabela.appendChild(thead);

  const tbody = doc.createElement("tbody");
  const desabilitados = new Set(opcoes.alunosDesabilitados || []);

  nomesAlunos.forEach((nome, idx) => {
    const tr = doc.createElement("tr");
    tr.id = `tableAlunos:${idx}`;

    const tdNum = doc.createElement("td"); tdNum.innerText = String(idx + 1); tr.appendChild(tdNum);
    const tdMat = doc.createElement("td"); tdMat.innerText = `2024${String(idx + 1).padStart(4, "0")}`; tr.appendChild(tdMat);

    const tdNome = doc.createElement("td");
    const aNome = doc.createElement("a");
    aNome.innerText = nome;
    tdNome.appendChild(aNome);
    tr.appendChild(tdNome);

    for (let p = 1; p <= qtdPeriodos; p++) {
      const tdCb = doc.createElement("td");
      const cb = doc.createElement("input");
      cb.setAttribute("type", "checkbox");
      cb.id = `tableAlunos:${idx}:chk_${p}`;
      if (desabilitados.has(nome) || desabilitados.has(idx)) {
        cb.disabled = true;
        cb.setAttribute("disabled", "disabled");
      }
      tdCb.appendChild(cb);
      tr.appendChild(tdCb);
    }

    tbody.appendChild(tr);
  });

  tabela.appendChild(tbody);
  doc.body.appendChild(tabela);
  return tabela;
}

/**
 * Cria a tabela do calendário mensal no DOM simulado.
 */
function montarTabelaCalendario(doc, nomeMes = "Março", diasComAula = [4, 11, 18, 25]) {
  const tabela = doc.createElement("table");
  tabela.id = "calendarioFrequencia";

  const thead = doc.createElement("thead");
  const trMes = doc.createElement("tr");
  const thMes = doc.createElement("th");
  thMes.innerText = nomeMes.toUpperCase();
  trMes.appendChild(thMes);
  thead.appendChild(trMes);

  const trDias = doc.createElement("tr");
  ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SAB"].forEach(d => {
    const th = doc.createElement("th");
    th.innerText = d;
    trDias.appendChild(th);
  });
  thead.appendChild(trDias);
  tabela.appendChild(thead);

  const tbody = doc.createElement("tbody");
  const tr = doc.createElement("tr");
  diasComAula.forEach(dia => {
    const td = doc.createElement("td");
    const a = doc.createElement("a");
    a.innerText = String(dia);
    a.setAttribute("href", `#dia_${dia}`);
    td.appendChild(a);
    tr.appendChild(td);
  });
  tbody.appendChild(tr);
  tabela.appendChild(tbody);

  doc.body.appendChild(tabela);
  return tabela;
}

module.exports = {
  ClassList,
  MockElement,
  MockDocument,
  criarAmbienteDOM,
  montarTabelaTurma,
  montarTabelaFrequencia,
  montarTabelaCalendario
};
