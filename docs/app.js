const state = {
  entries: [],
  entryById: new Map(),
  detailCache: new Map(),
  primary: null,
  comparison: null,
  selectedCompetitions: new Set(),
};

const $ = (selector) => document.querySelector(selector);
const primarySearch = $("#primary-search");
const compareSearch = $("#compare-search");
const primarySuggestions = $("#primary-suggestions");
const compareSuggestions = $("#compare-suggestions");
const results = $("#results");
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function avatar(entry, className = "avatar") {
  const label = escapeHtml(entry.name);
  const portraitUrl = safeImageUrl(entry.portrait_url);
  if (portraitUrl) {
    return `<span class="${className}"><img src="${portraitUrl}" alt="${label}" loading="lazy" data-initials="${escapeHtml(initials(entry.name))}"></span>`;
  }
  return `<span class="${className}" aria-label="${label}">${escapeHtml(initials(entry.name))}</span>`;
}

function portraitCredit(entry) {
  const credit = entry.portrait_credit;
  const sourceUrl = safeImageUrl(credit?.source_url);
  const licenseUrl = safeImageUrl(credit?.license_url);
  if (!credit || !sourceUrl || !licenseUrl) return "";
  return `<span class="portrait-credit"><a href="${sourceUrl}" target="_blank" rel="noopener noreferrer">Photo: “${escapeHtml(credit.title)}” by ${escapeHtml(credit.creator)}</a> · <a href="${licenseUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(credit.license)}</a></span>`;
}

function bindAvatarFallback(root) {
  root.querySelectorAll(".avatar img, .mini-avatar img").forEach((image) => {
    image.addEventListener("error", () => {
      image.parentElement.textContent = image.dataset.initials || "";
    }, { once: true });
  });
}

function safeImageUrl(value) {
  if (!value) return null;
  try {
    const url = new URL(value, window.location.href);
    return url.protocol === "https:" ? escapeHtml(url.href) : null;
  } catch {
    return null;
  }
}

function entryLabel(entry) {
  return `${entry.name} · ${entry.nationality}`;
}

function closeSuggestions(list) {
  list.hidden = true;
  list.replaceChildren();
}

function showSuggestions(input, list) {
  const query = input.value.trim().toLocaleLowerCase();
  if (query.length < 2) {
    closeSuggestions(list);
    return;
  }
  const matches = state.entries
    .filter((entry) => (
      entry.name.toLocaleLowerCase().includes(query)
      || entry.nationality.toLocaleLowerCase().includes(query)
    ))
    .slice(0, 12);
  list.innerHTML = matches.map((entry) => `
    <div class="suggestion-wrap">
      <button class="suggestion" type="button" role="option" data-entry-id="${escapeHtml(entry.entry_id)}">
        ${avatar(entry, "mini-avatar")}
        <span><strong>${escapeHtml(entry.name)}</strong><small>${escapeHtml(entry.nationality)} · ${entry.performance_count} performances</small></span>
      </button>
      ${portraitCredit(entry)}
    </div>
  `).join("") || '<p class="filter-hint">No matching entries.</p>';
  bindAvatarFallback(list);
  list.hidden = false;
  list.querySelectorAll("[data-entry-id]").forEach((button) => {
    button.addEventListener("click", () => selectEntry(button.dataset.entryId, input === compareSearch));
  });
}

async function loadEntry(entry) {
  if (state.detailCache.has(entry.entry_id)) return state.detailCache.get(entry.entry_id);
  const response = await fetch(`./data/${entry.file}`);
  if (!response.ok) throw new Error(`Could not load protocol data for ${entry.name}.`);
  const detail = await response.json();
  state.detailCache.set(entry.entry_id, detail);
  return detail;
}

async function selectEntry(entryId, isComparison = false) {
  const entry = state.entryById.get(entryId);
  if (!entry || (isComparison && state.primary?.entry_id === entryId)) return;
  const input = isComparison ? compareSearch : primarySearch;
  const suggestions = isComparison ? compareSuggestions : primarySuggestions;
  input.value = entryLabel(entry);
  closeSuggestions(suggestions);
  try {
    const detail = await loadEntry(entry);
    if (isComparison) {
      state.comparison = detail;
      const sharedCompetitions = new Set(
        detail.performances.map((performance) => performance.competition_id),
      );
      const selectedSharedCompetitions = [...state.selectedCompetitions]
        .filter((competitionId) => sharedCompetitions.has(competitionId));
      state.selectedCompetitions = new Set(
        selectedSharedCompetitions.length
          ? selectedSharedCompetitions
          : [...sharedCompetitions].filter((competitionId) => (
            state.primary?.performances.some(
              (performance) => performance.competition_id === competitionId,
            )
          )),
      );
      renderCompetitionOptions();
    } else {
      state.primary = detail;
      state.selectedCompetitions = new Set(
        detail.performances.map((performance) => performance.competition_id),
      );
      if (state.comparison?.entry_id === detail.entry_id) {
        state.comparison = null;
        compareSearch.value = "";
      }
      renderCompetitionOptions();
    }
    renderResults();
  } catch (error) {
    results.innerHTML = `<p class="error-message">${escapeHtml(error.message)}</p>`;
  }
}

function renderCompetitionOptions() {
  const container = $("#competition-options");
  if (!state.primary) {
    container.innerHTML = '<p class="filter-hint">Choose a skater first.</p>';
    $("#competition-label").textContent = "Choose competitions";
    return;
  }
  const competitionsByEntry = [state.primary, state.comparison]
    .filter(Boolean)
    .map((entry) => new Map(
      entry.performances.map((performance) => [
        performance.competition_id,
        performance.competition_name,
      ]),
    ));
  const competitions = new Map(competitionsByEntry[0]);
  if (state.comparison) {
    for (const competitionId of competitions.keys()) {
      if (!competitionsByEntry[1].has(competitionId)) {
        competitions.delete(competitionId);
      }
    }
  }
  state.selectedCompetitions = new Set(
    [...state.selectedCompetitions].filter((id) => competitions.has(id)),
  );
  container.innerHTML = [...competitions.entries()]
    .sort((left, right) => left[1].localeCompare(right[1]))
    .map(([id, name]) => `
      <label class="competition-option">
        <input type="checkbox" value="${escapeHtml(id)}" ${state.selectedCompetitions.has(id) ? "checked" : ""} />
        <span>${escapeHtml(name)}</span>
      </label>
    `).join("");
  container.querySelectorAll("input").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) state.selectedCompetitions.add(checkbox.value);
      else state.selectedCompetitions.delete(checkbox.value);
      updateCompetitionLabel(competitions.size);
      renderResults();
    });
  });
  updateCompetitionLabel(competitions.size);
}

function updateCompetitionLabel(total) {
  const selected = state.selectedCompetitions.size;
  $("#competition-label").textContent = selected === total
    ? `All competitions (${total})`
    : `${selected} of ${total} competitions`;
}

function filteredPerformances(entry) {
  return entry.performances.filter((performance) => (
    state.selectedCompetitions.has(performance.competition_id)
  ));
}

function displayScore(mark, panel) {
  const mean = Number.isFinite(mark.panel_mean) ? Number(mark.panel_mean).toFixed(2) : "—";
  const scores = (mark.judge_scores || []).map((score, index) => {
    if (score === null || score === undefined) return null;
    const judge = panel[index];
    return `<li>J${judge.number} ${escapeHtml(judge.nationality)}: ${Number(score).toFixed(2)}</li>`;
  }).filter(Boolean).join("");
  return `<span class="score-value">${mean}</span>
    <details class="judge-details"><summary>Judge marks</summary><ul class="judge-list">${scores || "<li>Unavailable</li>"}</ul></details>`;
}

function sumNumericField(marks, field) {
  const values = marks
    .map((mark) => mark[field])
    .filter((value) => Number.isFinite(value));
  return values.length ? values.reduce((total, value) => total + value, 0) : null;
}

function formatTotal(value) {
  return Number.isFinite(value) ? Number(value).toFixed(2) : "—";
}

function elementPanelScore(mark) {
  return Number.isFinite(mark?.base_value) && Number.isFinite(mark?.goe_total)
    ? (mark.base_value + mark.goe_total).toFixed(2)
    : "—";
}

function elementBaseValue(mark) {
  return Number.isFinite(mark?.base_value) ? mark.base_value.toFixed(2) : "—";
}

function protocolLink(performance) {
  const url = safeImageUrl(performance.source_url);
  return url
    ? `<a class="protocol-link" href="${url}" target="_blank" rel="noopener noreferrer">Official protocol ↗</a>`
    : "";
}

function formatDiscipline(value) {
  return ({
    men_singles: "Men",
    women_singles: "Women",
    pair_skating: "Pairs",
    ice_dance: "Ice dance",
  })[value] || value;
}

function formatSegment(value) {
  return ({
    short_program: "Short program",
    free_skating: "Free skating",
    rhythm_dance: "Rhythm dance",
    free_dance: "Free dance",
  })[value] || value;
}

function competitionTags(performances) {
  const labels = new Set();
  for (const performance of performances) {
    if (performance.event_type === "team_event") labels.add("Team event");
    if (performance.event_division !== "senior") {
      labels.add(performance.event_division.replace("_", " "));
    }
  }
  return [...labels]
    .map((label) => `<span class="tag">${escapeHtml(label)}</span>`)
    .join("");
}

function performanceTitle(performance) {
  return `${formatDiscipline(performance.event_category)} · ${formatSegment(performance.segment)}`;
}

function soloPerformanceCard(performance) {
  const elementRows = performance.elements.map((mark) => `
    <tr>
      <td>${escapeHtml(mark.element_type || "Element")}${mark.technical_call ? ` <small>${escapeHtml(mark.technical_call)}</small>` : ""}</td>
      <td>${elementBaseValue(mark)}</td>
      <td>${mark.goe_total === null || mark.goe_total === undefined ? "—" : Number(mark.goe_total).toFixed(2)}</td>
      <td>${elementPanelScore(mark)}</td>
      <td class="score-cell">${displayScore(mark, performance.judge_panel)}</td>
    </tr>
  `).join("");
  const elementTotalRow = `
    <tr class="total-row">
      <th scope="row">Total Element Score</th>
      <td>${sumNumericField(performance.elements, "base_value")?.toFixed(2) ?? "—"}</td>
      <td>${sumNumericField(performance.elements, "goe_total")?.toFixed(2) ?? "—"}</td>
      <td>${formatTotal(performance.total_element_score)}</td>
      <td>—</td>
    </tr>
  `;
  const componentRows = performance.components.map((mark) => `
    <tr>
      <td>${escapeHtml(mark.component || "Component")}</td>
      <td>${mark.component_factor ?? "—"}</td>
      <td class="score-cell">${displayScore(mark, performance.judge_panel)}</td>
    </tr>
  `).join("");
  const componentTotalRow = `
    <tr class="total-row">
      <th scope="row">Program Component Score (factored)</th>
      <td>—</td>
      <td class="score-cell">${formatTotal(performance.program_component_score)}</td>
    </tr>
    <tr class="total-row total-points-row">
      <th scope="row" colspan="2">Total Points</th>
      <td>${formatTotal(performance.total_segment_score)}</td>
    </tr>
  `;
  return `
    <article class="protocol-card">
      <div class="protocol-head">
        <div><strong>${escapeHtml(performanceTitle(performance))}</strong><br />
          <span>${performance.rank ? `Segment rank ${performance.rank}` : "Rank unavailable"} · ${performance.judge_panel.length} judges</span>
        </div>
        ${protocolLink(performance)}
      </div>
      <div class="table-scroll">
        <table class="marks-table">
          <thead><tr><th>Element</th><th>Base value</th><th>GOE</th><th>Element Total</th><th>Judge GOE mean / individual marks</th></tr></thead>
          <tbody>${elementRows || '<tr><td colspan="5">No element marks parsed.</td></tr>'}${elementTotalRow}</tbody>
        </table>
      </div>
      <p class="compare-label">Program components</p>
      <div class="table-scroll">
        <table class="marks-table">
          <thead><tr><th>Component</th><th>Factor</th><th>Panel mean / individual marks</th></tr></thead>
          <tbody>${componentRows || '<tr><td colspan="3">No component marks parsed.</td></tr>'}${componentTotalRow}</tbody>
        </table>
      </div>
    </article>
  `;
}

function elementOccurrences(marks) {
  const counts = new Map();
  return marks.map((mark) => {
    const type = mark.element_type || "Element";
    const occurrence = (counts.get(type) || 0) + 1;
    counts.set(type, occurrence);
    return { ...mark, match_key: `${type}#${occurrence}` };
  });
}

function comparisonTable(
  firstMarks,
  secondMarks,
  firstPanel,
  secondPanel,
  kind,
  firstName,
  secondName,
  firstPerformance,
  secondPerformance,
) {
  const scoreLabel = kind === "element"
    ? "judge GOE mean / marks"
    : "panel mean / judge marks";
  const first = kind === "element" ? elementOccurrences(firstMarks) : firstMarks;
  const second = kind === "element" ? elementOccurrences(secondMarks) : secondMarks;
  const keyOf = (mark) => kind === "element" ? mark.match_key : mark.component;
  const firstMap = new Map(first.map((mark) => [keyOf(mark), mark]));
  const secondMap = new Map(second.map((mark) => [keyOf(mark), mark]));
  const keys = [...new Set([...firstMap.keys(), ...secondMap.keys()])];
  if (!keys.length) return '<p class="filter-hint">No matching marks available.</p>';
  const rows = keys.map((key) => {
    const left = firstMap.get(key);
    const right = secondMap.get(key);
    const title = left?.element_type || right?.element_type || left?.component || right?.component || key;
    return `<tr>
      <td>${escapeHtml(title)}${left?.technical_call || right?.technical_call ? `<br /><small>${escapeHtml(left?.technical_call || right?.technical_call)}</small>` : ""}</td>
      ${kind === "element" ? `<td>${elementBaseValue(left)}</td>` : ""}
      ${kind === "element" ? `<td>${left?.goe_total === null || left?.goe_total === undefined ? "—" : Number(left.goe_total).toFixed(2)}</td>` : ""}
      ${kind === "element" ? `<td>${elementPanelScore(left)}</td>` : ""}
      <td class="score-cell">${left ? displayScore(left, firstPanel) : "—"}</td>
      ${kind === "element" ? `<td>${elementBaseValue(right)}</td>` : ""}
      ${kind === "element" ? `<td>${right?.goe_total === null || right?.goe_total === undefined ? "—" : Number(right.goe_total).toFixed(2)}</td>` : ""}
      ${kind === "element" ? `<td>${elementPanelScore(right)}</td>` : ""}
      <td class="score-cell">${right ? displayScore(right, secondPanel) : "—"}</td>
    </tr>`;
  }).join("");
  const summaryCells = (marks, performance) => {
    if (!marks.length) {
      return kind === "element"
        ? "<td>—</td><td>—</td><td>—</td><td>—</td>"
        : "<td>—</td>";
    }
    if (kind === "element") {
      const baseValue = sumNumericField(marks, "base_value");
      const goe = sumNumericField(marks, "goe_total");
      return `<td>${baseValue?.toFixed(2) ?? "—"}</td><td>${goe?.toFixed(2) ?? "—"}</td><td>${formatTotal(performance?.total_element_score)}</td><td>—</td>`;
    }
    return `<td class="score-cell">${formatTotal(performance?.program_component_score)}</td>`;
  };
  const totalsRow = `<tr class="total-row"><th scope="row">${kind === "element" ? "Total Element Score" : "Program Component Score (factored)"}</th>${summaryCells(firstMarks, firstPerformance)}${summaryCells(secondMarks, secondPerformance)}</tr>`;
  const totalPointsRow = kind === "component"
    ? `<tr class="total-row total-points-row"><th scope="row">Total Points</th><td>${formatTotal(firstPerformance?.total_segment_score)}</td><td>${formatTotal(secondPerformance?.total_segment_score)}</td></tr>`
    : "";
  return `<div class="table-scroll"><table class="marks-table comparison-table comparison-table--${kind}">
    <thead><tr>
      <th>${kind === "element" ? "Element" : "Component"}</th>
      ${kind === "element" ? "<th>Skater 1 base value</th>" : ""}
      ${kind === "element" ? "<th>Skater 1 GOE</th>" : ""}
      ${kind === "element" ? "<th>Skater 1 Element Total</th>" : ""}
      <th>Skater 1 · ${escapeHtml(firstName)} · ${scoreLabel}</th>
      ${kind === "element" ? "<th>Skater 2 base value</th>" : ""}
      ${kind === "element" ? "<th>Skater 2 GOE</th>" : ""}
      ${kind === "element" ? "<th>Skater 2 Element Total</th>" : ""}
      <th>Skater 2 · ${escapeHtml(secondName)} · ${scoreLabel}</th>
    </tr></thead>
    <tbody>${rows}${totalsRow}${totalPointsRow}</tbody>
  </table></div>`;
}

function comparePerformanceCard(first, second, firstEntry, secondEntry) {
  const performance = first || second;
  const firstName = firstEntry.name;
  const secondName = secondEntry.name;
  const missingEntryName = first ? secondName : firstName;
  return `
    <article class="protocol-card">
      <div class="protocol-head">
        <div><strong>${escapeHtml(performance.competition_name)}</strong><br />
          <span>${escapeHtml(performanceTitle(performance))} · ${performance.event_type === "team_event" ? "Team event" : "Individual event"}</span>
        </div>
        ${protocolLink(performance)}
      </div>
      <div class="comparison-names">
        <span>${escapeHtml(firstName)}</span><span class="versus">VS</span><span>${escapeHtml(secondName)}</span>
      </div>
      ${first && second ? "" : `<p class="comparison-missing">${escapeHtml(missingEntryName)} has no matching performance for this competition, discipline, and segment.</p>`}
      <p class="compare-label">Elements · identical element types aligned by appearance order</p>
      ${comparisonTable(first?.elements || [], second?.elements || [], first?.judge_panel || [], second?.judge_panel || [], "element", firstName, secondName, first, second)}
      <p class="compare-label">Program components</p>
      ${comparisonTable(first?.components || [], second?.components || [], first?.judge_panel || [], second?.judge_panel || [], "component", firstName, secondName, first, second)}
    </article>
  `;
}

function matchingKey(performance) {
  return [
    performance.competition_id,
    performance.event_type,
    performance.event_category,
    performance.event_division,
    performance.segment,
  ].join("|");
}

function renderResults() {
  if (!state.primary) {
    results.innerHTML = '<div class="empty-state"><span class="empty-icon" aria-hidden="true">↗</span><p>Pick a skater to explore their protocols.</p></div>';
    return;
  }
  const primaryPerformances = filteredPerformances(state.primary);
  const avatarHtml = avatar(state.primary);
  let html = `<div class="selected-skater">${avatarHtml}<div><h3>Search results for skater: ${escapeHtml(state.primary.name)}</h3><p>${escapeHtml(state.primary.nationality)} · ${primaryPerformances.length} performances selected</p>${portraitCredit(state.primary)}</div></div>`;

  if (state.comparison) {
    const comparisonPerformances = filteredPerformances(state.comparison);
    const secondByKey = new Map(comparisonPerformances.map((performance) => [matchingKey(performance), performance]));
    const comparisonRows = primaryPerformances.flatMap((performance) => {
      const key = matchingKey(performance);
      const match = secondByKey.get(key);
      if (!match) return [];
      return [[performance, match]];
    });
    html += `<div class="selected-skater">${avatar(state.comparison)}<div><h3>Compared with ${escapeHtml(state.comparison.name)}</h3><p>${escapeHtml(state.comparison.nationality)} · ${comparisonRows.length} shared performances</p>${portraitCredit(state.comparison)}</div></div>`;
    const allRows = comparisonRows;
    html += allRows.map(([first, second]) => (
      comparePerformanceCard(first, second, state.primary, state.comparison)
    )).join("");
    if (!allRows.length) {
      html += '<div class="empty-state"><p>No shared performances match the selected competitions.</p></div>';
    }
  } else {
    if (primaryPerformances.length) {
      const byCompetition = new Map();
      for (const performance of primaryPerformances) {
        if (!byCompetition.has(performance.competition_id)) {
          byCompetition.set(performance.competition_id, {
            name: performance.competition_name,
            season: performance.season,
            performances: [],
          });
        }
        byCompetition.get(performance.competition_id).performances.push(performance);
      }
      html += [...byCompetition.values()]
        .sort((a, b) => b.season.localeCompare(a.season) || a.name.localeCompare(b.name))
        .map((competition) => `
          <section class="result-group">
            <h3 class="result-title">${escapeHtml(competition.name)} ${competitionTags(competition.performances)}</h3>
            ${competition.performances.map(soloPerformanceCard).join("")}
          </section>
        `).join("");
    } else {
      html += '<div class="empty-state"><p>No performances match these competition filters.</p></div>';
    }
  }
  results.innerHTML = html;
  bindAvatarFallback(results);
}

function renderDirectory() {
  const query = $("#directory-search").value.trim().toLocaleLowerCase();
  const filteredEntries = state.entries.filter((entry) => (
    !query
    || entry.name.toLocaleLowerCase().includes(query)
    || entry.nationality.toLocaleLowerCase().includes(query)
  ));
  const categoryOrder = [
    ["women_singles", "Women Single Skating"],
    ["men_singles", "Men Single Skating"],
    ["ice_dance", "Ice Dance"],
    ["pair_skating", "Pair Skating"],
  ];
  $("#directory-count").textContent = `${filteredEntries.length.toLocaleString()} of ${state.entries.length.toLocaleString()} athletes and teams`;
  $("#directory-grid").innerHTML = categoryOrder.map(([category, label]) => {
    const categoryEntries = filteredEntries.filter((entry) => entry.event_categories.includes(category));
    if (!categoryEntries.length) return "";
    return `
      <section class="directory-category">
        <div class="directory-category-heading">
          <h3>${label}</h3>
          <span>${categoryEntries.length} ${categoryEntries.length === 1 ? "entry" : "entries"}</span>
        </div>
        <div class="directory-category-grid">
          ${categoryEntries.map((entry) => `
            <div class="directory-entry">
              <button class="directory-card" type="button" data-entry-id="${escapeHtml(entry.entry_id)}">
                ${avatar(entry)}
                <span class="directory-card-copy"><strong>${escapeHtml(entry.name)}</strong><small>${escapeHtml(entry.nationality)} · ${entry.performance_count} performances</small></span>
              </button>
              ${portraitCredit(entry)}
            </div>
          `).join("")}
        </div>
      </section>
    `;
  }).join("") || '<p class="filter-hint">No athletes or teams match this search.</p>';
  bindAvatarFallback($("#directory-grid"));
  $("#directory-grid").querySelectorAll("[data-entry-id]").forEach((button) => {
    button.addEventListener("click", () => {
      selectEntry(button.dataset.entryId);
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

function bindSearch(input, list) {
  input.addEventListener("input", () => showSuggestions(input, list));
  input.addEventListener("focus", () => showSuggestions(input, list));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSuggestions(list);
    if (event.key === "Enter") {
      const first = list.querySelector("[data-entry-id]");
      if (first) {
        event.preventDefault();
        selectEntry(first.dataset.entryId, input === compareSearch);
      }
    }
  });
  document.addEventListener("click", (event) => {
    if (!input.parentElement.contains(event.target)) closeSuggestions(list);
  });
}

async function start() {
  const initialDirectoryLink = window.location.hash === "#directory";
  let userInterrupted = false;
  const interrupt = () => { userInterrupted = true; };
  const interactionEvents = ["pointerdown", "touchstart", "wheel", "keydown"];
  interactionEvents.forEach((type) => window.addEventListener(type, interrupt, { passive: true }));
  try {
    const [indexResponse, siteResponse] = await Promise.all([
      fetch("./data/index.json"),
      fetch("./data/site.json"),
    ]);
    if (!indexResponse.ok || !siteResponse.ok) {
      throw new Error("Static data files are missing. Run the site data export command first.");
    }
    state.entries = await indexResponse.json();
    state.entries.sort((a, b) => a.name.localeCompare(b.name) || a.nationality.localeCompare(b.nationality));
    state.entryById = new Map(state.entries.map((entry) => [entry.entry_id, entry]));
    const site = await siteResponse.json();
    $("#dataset-note").textContent = `${site.entry_count.toLocaleString()} skater/team entries · ${site.competition_count} competitions · ${site.mark_count.toLocaleString()} judge marks`;
    bindSearch(primarySearch, primarySuggestions);
    bindSearch(compareSearch, compareSuggestions);
    $("#directory-search").addEventListener("input", renderDirectory);
    $("#select-all").addEventListener("click", () => {
      if (!state.primary) return;
      state.selectedCompetitions = new Set(
        [state.primary, state.comparison]
          .flatMap((entry) => entry?.performances || [])
          .map((performance) => performance.competition_id),
      );
      renderCompetitionOptions();
      renderResults();
    });
    $("#clear-all").addEventListener("click", () => {
      state.selectedCompetitions.clear();
      renderCompetitionOptions();
      renderResults();
    });
    const competitionFilter = $("#competition-filter");
    document.addEventListener("click", (event) => {
      if (!competitionFilter.contains(event.target)) competitionFilter.open = false;
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") competitionFilter.open = false;
    });
    renderDirectory();
    if (initialDirectoryLink && !userInterrupted && window.location.hash === "#directory") {
      $("#directory").scrollIntoView({ block: "start" });
    }
  } catch (error) {
    $("#dataset-note").textContent = "Dataset not built yet";
    results.innerHTML = `<p class="error-message">${escapeHtml(error.message)}</p>`;
    $("#directory-count").textContent = "To load skaters, run the site-data export command in the project README.";
  } finally {
    interactionEvents.forEach((type) => window.removeEventListener(type, interrupt));
  }
}

start();
