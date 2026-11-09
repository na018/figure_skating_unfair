const programsContainer = document.querySelector("#programs");
const comparison = document.querySelector("#comparison");
const programs = [];
const formatPoints = (cents) => (cents / 100).toFixed(2);
const toCents = (value) => Math.round(value * 100);
const elementValues = typeof ISU_ELEMENT_VALUES === "undefined" ? null : ISU_ELEMENT_VALUES;
const codes = elementValues ? Object.keys(elementValues).filter((code) => !code.endsWith("b") && code !== "Eu") : [];
const codeByName = new Map(codes.map((code) => [code.toLowerCase(), code]));
const cleanJump = /^[1-4](?:T|S|Lo|F|Lz|A)$/;
const jumpNames = { T: "Toe loop", S: "Salchow", Lo: "Loop", F: "Flip", Lz: "Lutz", A: "Axel" };
const elementNames = {
  USp: "Upright spin", LSp: "Layback spin", CSp: "Camel spin", SSp: "Sit spin",
  FUSp: "Flying upright spin", FLSp: "Flying layback spin", FCSp: "Flying camel spin", FSSp: "Flying sit spin",
  CUSp: "Change foot upright spin", CLSp: "Change foot layback spin", CCSp: "Change foot camel spin", CSSp: "Change foot sit spin",
  FCUSp: "Flying change foot upright spin", FCLSp: "Flying change foot layback spin", FCCSp: "Flying change foot camel spin", FCSSp: "Flying change foot sit spin",
  CoSp: "Combination spin", FCoSp: "Flying combination spin", CCoSp: "Change foot combination spin", FCCoSp: "Flying change foot combination spin",
  StSq: "Step sequence", BiDs: "Backward inside death spiral", BoDs: "Backward outside death spiral",
  FiDs: "Forward inside death spiral", FoDs: "Forward outside death spiral",
  PSp: "Pair spin", PCoSp: "Pair spin combination", PiF: "Pivot figure",
  ChSq: "Choreographic sequence", ChSp: "Choreographic spin", ChPSp: "Choreographic pair spin", ChPLi: "Choreographic pair lift",
};
let elementId = 0;

function description(code) {
  const jump = code.match(/^([1-5])(T|S|Lo|F|Lz|A)(Th)?(.*)$/);
  if (jump) return `${["", "Single", "Double", "Triple", "Quadruple", "Quintuple"][Number(jump[1])]} ${jumpNames[jump[2]]}${jump[3] ? " throw" : ""}${jump[4] ? ` (${jump[4]})` : ""}`;
  const family = code.match(/^([A-Za-z]+)(B|[1-4])(V)?$/);
  if (family && elementNames[family[1]]) {
    return `${elementNames[family[1]]} ${family[2] === "B" ? "basic" : `level ${family[2]}`}${family[3] ? " (reduced value)" : ""}`;
  }
  const pair = code.match(/^([1-5][A-Z]?)(Li|Tw)(B|[1-4])(<<)?$/);
  if (pair) return `${pair[2] === "Li" ? "Pair lift" : "Twist lift"} ${pair[1]}, ${pair[3] === "B" ? "basic" : `level ${pair[3]}`}${pair[4] ? " (downgraded)" : ""}`;
  return code;
}

function resolveElement(value) {
  const parts = value.trim().split("+").map((part) => part.trim());
  if (parts.length === 1) {
    const code = codeByName.get(parts[0].toLowerCase());
    if (!code) return null;
    const [base, grades] = elementValues[code];
    return { base, grades };
  }
  const resolved = parts.map((part) => part.toLowerCase() === "eu" ? "Eu" : codeByName.get(part.toLowerCase()));
  const jumps = resolved.filter((code) => code !== "Eu");
  if (resolved.some((code) => !code || (code !== "Eu" && !cleanJump.test(code)))
    || jumps.length < 2 || jumps.length > 3
    || resolved.filter((code) => code === "Eu").length > 1
    || resolved[0] === "Eu" || resolved[resolved.length - 1] === "Eu") return null;
  const values = jumps.map((code) => elementValues[code]);
  const hardest = values.reduce((best, current) => current[0] > best[0] ? current : best);
  return { base: values.reduce((sum, current) => sum + current[0], 0), grades: hardest[1] };
}

function updateSuggestions(input, list) {
  const value = input.value.trim();
  const lastPlus = value.lastIndexOf("+");
  const prefix = lastPlus < 0 ? "" : value.slice(0, lastPlus + 1);
  const query = value.slice(lastPlus + 1).trim().toLowerCase();
  const candidates = lastPlus < 0 ? codes : [...codes.filter((code) => cleanJump.test(code)), "Eu"];
  const matches = candidates.filter((code) => code.toLowerCase().includes(query)
    || (!prefix && description(code).toLowerCase().includes(query))).slice(0, 60);
  list.replaceChildren(...matches.map((code) => {
    const option = document.createElement("option");
    option.value = prefix + code;
    option.label = description(code);
    return option;
  }));
}

function numberValue(input) {
  if (input.value.trim() === "" || !input.validity.valid) return null;
  const value = Number(input.value);
  return Number.isFinite(value) ? value : null;
}

function field(label, attributes, className) {
  return `<label class="calculator-field">${label}<input class="${className}" ${attributes}></label>`;
}

function addElement(program) {
  const element = document.createElement("tr");
  element.className = "element-row";
  const listId = `element-options-${++elementId}`;
  element.innerHTML = `
    <td>
      <label class="sr-only" for="${listId}-input">Element name</label>
      <input id="${listId}-input" class="element-name" type="text" list="${listId}" placeholder="e.g. 3Lz" autocomplete="off" />
      <datalist id="${listId}"></datalist>
      <span class="element-status"></span>
    </td>
    <td><span class="element-base">—</span></td>
    <td>
        <select class="element-grade" aria-label="GOE grade">
          ${Array.from({ length: 11 }, (_, i) => 5 - i).map((grade) => `<option value="${grade}"${grade === 0 ? " selected" : ""}>${grade > 0 ? "+" : ""}${grade}</option>`).join("")}
        </select>
    </td>
    <td><strong class="element-score">—</strong></td>
    <td><button class="remove-element" type="button">Remove</button></td>
  `;
  const input = element.querySelector(".element-name");
  const list = element.querySelector("datalist");
  input.addEventListener("input", () => updateSuggestions(input, list));
  input.addEventListener("focus", () => updateSuggestions(input, list));
  updateSuggestions(input, list);
  element.querySelector(".remove-element").addEventListener("click", () => {
    element.remove();
    updateProgram(program);
  });
  program.elements.append(element);
  updateProgram(program);
}

function elementValue(element) {
  const input = element.querySelector(".element-name");
  const data = resolveElement(input.value);
  const grade = Number(element.querySelector(".element-grade").value);
  const status = element.querySelector(".element-status");
  const score = element.querySelector(".element-score");
  const base = element.querySelector(".element-base");
  if (!data) {
    status.textContent = input.value.trim() ? "Select a listed element or enter a supported combination." : "";
    base.textContent = "—";
    score.textContent = "—";
    return null;
  }
  const goe = grade === 0 ? 0 : data.grades[grade < 0 ? grade + 5 : grade + 4];
  const value = data.base + goe;
  status.textContent = "";
  base.textContent = formatPoints(data.base);
  score.textContent = formatPoints(value);
  return value;
}

function updateProgram(program) {
  const elements = [...program.elements.querySelectorAll(".element-row")];
  const values = elements.map((element, index) => {
    element.querySelector(".remove-element").setAttribute("aria-label", `Remove element ${index + 1} from ${program.label}`);
    element.querySelector(".element-name").setAttribute("aria-label", `Element ${index + 1} name in ${program.label}`);
    element.querySelector(".element-grade").setAttribute("aria-label", `Element ${index + 1} GOE in ${program.label}`);
    return elementValue(element);
  });
  const enteredElements = elements.map((element, index) => ({
    entered: element.querySelector(".element-name").value.trim() !== "",
    value: values[index],
  })).filter((element) => element.entered);
  const tes = enteredElements.length && enteredElements.every((element) => element.value !== null)
    ? enteredElements.reduce((sum, element) => sum + element.value, 0)
    : null;
  const factorInput = program.card.querySelector(".pcs-factor");
  const markInputs = [...program.card.querySelectorAll(".pcs-mark")];
  const componentInputs = [...markInputs, factorInput];
  const invalidComponents = componentInputs.some((input) => !input.validity.valid);
  const factor = numberValue(factorInput);
  const marks = markInputs.map(numberValue);
  const pcs = factor !== null && marks.every((mark) => mark !== null)
    ? marks.reduce((sum, mark) => sum + Math.round(toCents(mark) * toCents(factor) / 100), 0)
    : null;
  const falls = numberValue(program.card.querySelector(".fall-count"));
  const deductionValue = numberValue(program.card.querySelector(".fall-deduction"));
  const deductions = falls === null || deductionValue === null ? null : falls * toCents(deductionValue);

  program.card.querySelector(".tes-output").textContent = tes === null ? "—" : formatPoints(tes);
  program.card.querySelector(".pcs-output").textContent = pcs === null ? "Not included" : formatPoints(pcs);
  program.card.querySelector(".deductions-output").textContent = deductions === null ? "—" : `−${formatPoints(deductions)}`;
  program.total = tes === null || invalidComponents || deductions === null
    ? null
    : tes + (pcs ?? 0) - deductions;
  program.pcsIncluded = pcs !== null;
  program.card.querySelector(".total-output").textContent = program.total === null ? "—" : formatPoints(program.total);
  let note;
  if (invalidComponents) {
    note = "Enter valid component marks and factor, or leave them blank.";
  } else if (deductions === null) {
    note = "Enter a valid whole number of falls and a non-negative deduction value.";
  } else if (tes === null) {
    note = "Select at least one valid element; correct any unrecognized element codes.";
  } else if (pcs === null) {
    note = "PCS is not included until all three marks and the factor are complete.";
  } else {
    note = "Estimate only; check all inputs and applicable rules.";
  }
  program.card.querySelector(".summary-note").textContent = note;
  updateComparison();
}

function updateComparison() {
  if (programs.length !== 2 || programs.some((program) => program.total === null)) {
    comparison.textContent = "Complete both programs to compare their totals.";
    return;
  }
  const [a, b] = programs;
  const nameA = a.card.querySelector(".program-name").value.trim() || a.label;
  const nameB = b.card.querySelector(".program-name").value.trim() || b.label;
  const difference = Math.abs(a.total - b.total);
  comparison.textContent = difference === 0
    ? `${nameA} and ${nameB} are tied at ${formatPoints(a.total)} points.`
    : `${a.total > b.total ? nameA : nameB} leads by ${formatPoints(difference)} points (${nameA}: ${formatPoints(a.total)} · ${nameB}: ${formatPoints(b.total)}).`;
  if (!a.pcsIncluded || !b.pcsIncluded) {
    comparison.textContent += " PCS is not included for every program.";
  }
}

function createProgram(label) {
  const card = document.createElement("section");
  card.className = "program-card";
  card.setAttribute("aria-label", label);
  card.innerHTML = `
    <p class="eyebrow">YOUR PROGRAM</p>
    <h2>${label}</h2>
    ${field("Program name", `type="text" value="${label}"`, "program-name")}
    <h3>Technical elements</h3>
    <div class="element-table-wrap">
      <table class="element-table">
        <thead><tr><th scope="col">Element name</th><th scope="col">Base value</th><th scope="col">GOE</th><th scope="col">Total</th><th scope="col"><span class="sr-only">Remove</span></th></tr></thead>
        <tbody class="element-list"></tbody>
      </table>
    </div>
    <button class="calculator-button add-element" type="button">+ Add element</button>
    <h3>Program components</h3>
    <p class="calculator-note">Optional: enter all three averaged marks and the factor to include PCS. ISU 2786 lists senior/junior singles and pairs factors.</p>
    <div class="component-fields">
      ${field("Composition", 'type="number" min="0" max="10" step="0.01" placeholder="0.00–10.00"', "pcs-mark")}
      ${field("Presentation", 'type="number" min="0" max="10" step="0.01" placeholder="0.00–10.00"', "pcs-mark")}
      ${field("Skating skills", 'type="number" min="0" max="10" step="0.01" placeholder="0.00–10.00"', "pcs-mark")}
      ${field("Factor for each component", 'type="number" min="0.01" step="0.01" placeholder="e.g. 1.33"', "pcs-factor")}
    </div>
    <h3>Falls</h3>
    <p class="calculator-note">A fixed deduction per fall is an estimate; actual ISU deductions can depend on the event and number of falls.</p>
    <div class="component-fields">
      ${field("Amount of falls", 'type="number" min="0" step="1" value="0"', "fall-count")}
      ${field("Deduction value per fall", 'type="number" min="0" step="0.01" value="1"', "fall-deduction")}
    </div>
    <div class="program-summary" aria-live="polite">
      <div><span>Technical element score</span><strong class="tes-output">—</strong></div>
      <div><span>Program component score</span><strong class="pcs-output">—</strong></div>
      <div><span>Fall deductions</span><strong class="deductions-output">—</strong></div>
      <div class="total"><span>Estimated total</span><strong class="total-output">—</strong></div>
      <span class="calculator-note summary-note"></span>
    </div>
  `;
  programsContainer.append(card);
  const program = { label, card, elements: card.querySelector(".element-list"), total: null };
  programs.push(program);
  card.addEventListener("input", () => updateProgram(program));
  card.addEventListener("change", () => updateProgram(program));
  card.querySelector(".add-element").addEventListener("click", () => addElement(program));
  addElement(program);
}

if (elementValues) {
  createProgram("Program A");
  createProgram("Program B");
} else {
  programsContainer.textContent = "The ISU element values could not be loaded. Please reload the page.";
  comparison.textContent = "Comparison is unavailable without the element values.";
}
