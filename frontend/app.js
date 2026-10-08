const DOMAINS = [
  { key: "movies", label: "🎬 Movies", genres: ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller", "Fantasy"] },
  { key: "series", label: "📺 Series", genres: ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller", "Fantasy"] },
  { key: "anime", label: "🌸 Anime", genres: ["Action", "Comedy", "Drama", "Fantasy", "Romance", "Sci-Fi", "Slice of Life", "Supernatural"] },
  { key: "music", label: "🎵 Music", genres: [], favoritesLabel: "Favorite singers / artists" },
  { key: "games", label: "🎮 Games", genres: ["Action", "Adventure", "RPG", "Shooter", "Strategy", "Puzzle", "Sports"] },
  { key: "novels", label: "📚 Novels", genres: ["Fiction", "Fantasy", "Mystery", "Romance", "Science Fiction", "Horror", "Biography"] },
  { key: "comics", label: "💥 Comics", genres: ["Superhero", "Fantasy", "Horror", "Sci-Fi", "Crime"] },
];

const state = {
  preferences: loadPreferences(), // { movies: {genres:[]}, music: {favorites:[]}, ... }
  onboardingDone: localStorage.getItem("onboarding_done") === "true",
  view: "for-me", // "for-me" | "explore"
  activeDomain: "movies",
};

function loadPreferences() {
  try {
    return JSON.parse(localStorage.getItem("preferences") || "{}");
  } catch {
    return {};
  }
}

function savePreferences() {
  localStorage.setItem("preferences", JSON.stringify(state.preferences));
}

// ---------------------------------------------------------------------------
// ONBOARDING
// ---------------------------------------------------------------------------
function renderOnboarding() {
  document.getElementById("top-nav").style.display = "none";
  document.getElementById("edit-prefs-wrap").style.display = "none";

  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="onboarding">
      <h2>What are you into?</h2>
      <p style="color:var(--muted); font-size:14px;">
        Pick your favorite genres per type — totally optional, skip any or all of it.
      </p>
      ${DOMAINS.map(d => renderOnboardingDomainBlock(d)).join("")}
      <div class="onboarding-actions">
        <button class="secondary" id="skip-btn">Skip → Explore</button>
        <button class="primary" id="save-btn">Save & continue</button>
      </div>
    </div>
  `;

  DOMAINS.forEach(d => {
    if (d.genres.length) {
      document.querySelectorAll(`.chip[data-domain="${d.key}"]`).forEach(chip => {
        chip.addEventListener("click", () => {
          chip.classList.toggle("selected");
        });
      });
    }
  });

  document.getElementById("skip-btn").addEventListener("click", () => {
    localStorage.setItem("onboarding_done", "true");
    state.onboardingDone = true;
    state.view = "explore";
    render();
  });

  document.getElementById("save-btn").addEventListener("click", () => {
    collectOnboardingSelections();
    localStorage.setItem("onboarding_done", "true");
    state.onboardingDone = true;
    state.view = "for-me";
    render();
  });
}

function renderOnboardingDomainBlock(d) {
  if (d.key === "music") {
    return `
      <div>
        <strong>${d.label}</strong>
        <div class="chip-row">
          <input type="text" id="music-favorites-input"
            placeholder="${d.favoritesLabel} (comma separated)"
            style="width:100%; padding:8px; border-radius:6px; border:1px solid var(--border); background:var(--bg); color:var(--text);" />
        </div>
      </div>
    `;
  }
  return `
    <div>
      <strong>${d.label}</strong>
      <div class="chip-row">
        ${d.genres.map(g => `<span class="chip" data-domain="${d.key}" data-genre="${g}">${g}</span>`).join("")}
      </div>
    </div>
  `;
}

function collectOnboardingSelections() {
  DOMAINS.forEach(d => {
    if (d.key === "music") {
      const val = document.getElementById("music-favorites-input")?.value || "";
      const favorites = val.split(",").map(s => s.trim()).filter(Boolean);
      if (favorites.length) state.preferences.music = { favorites };
    } else {
      const selected = Array.from(document.querySelectorAll(`.chip.selected[data-domain="${d.key}"]`))
        .map(el => el.dataset.genre);
      if (selected.length) state.preferences[d.key] = { genres: selected };
    }
  });
  savePreferences();
}

// ---------------------------------------------------------------------------
// MAIN APP SHELL (For Me / Explore + domain sub-tabs)
// ---------------------------------------------------------------------------
function renderShell() {
  document.getElementById("top-nav").style.display = "flex";
  document.getElementById("edit-prefs-wrap").style.display = "block";

  document.querySelectorAll("#top-nav button").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.view === state.view);
    btn.onclick = () => {
      state.view = btn.dataset.view;
      render();
    };
  });

  document.getElementById("edit-prefs-btn").onclick = () => {
    renderOnboarding();
  };

  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="domain-tabs" id="domain-tabs"></div>
    <div id="results"><div class="loading">Loading…</div></div>
  `;

  const tabsEl = document.getElementById("domain-tabs");
  tabsEl.innerHTML = DOMAINS.map(d =>
    `<button data-domain="${d.key}" class="${d.key === state.activeDomain ? 'active' : ''}">${d.label}</button>`
  ).join("");

  tabsEl.querySelectorAll("button").forEach(btn => {
    btn.onclick = () => {
      state.activeDomain = btn.dataset.domain;
      render();
    };
  });

  loadResults();
}

async function loadResults() {
  const resultsEl = document.getElementById("results");
  resultsEl.innerHTML = `<div class="loading">Loading ${state.activeDomain}…</div>`;

  let res;
  try {
    if (state.view === "explore") {
      res = await fetch(`${API_BASE}/explore/${state.activeDomain}`);
    } else {
      const prefs = state.preferences[state.activeDomain] || {};
      res = await fetch(`${API_BASE}/for-me/${state.activeDomain}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs),
      });
    }
  } catch (err) {
    // The request never reached the server at all (DNS/network/CORS failure,
    // or the backend is completely down / still waking up from sleep).
    resultsEl.innerHTML = `
      <div class="error-state">
        ⚠️ Couldn't reach the backend at ${API_BASE}.<br/>
        If it's hosted on a free plan, it may just be waking up — this can take 30–50 seconds.<br/>
        <button class="secondary" style="margin-top:12px" onclick="loadResults()">Retry</button>
      </div>`;
    return;
  }

  let items;
  const rawText = await res.text();
  try {
    items = JSON.parse(rawText);
  } catch {
    // The server responded, but not with JSON — usually a crash on that one
    // domain's data source. The backend itself is fine; this request wasn't.
    resultsEl.innerHTML = `
      <div class="error-state">
        ⚠️ This section (${state.activeDomain}) hit a snag fetching live data — the backend itself is running fine.<br/>
        <button class="secondary" style="margin-top:12px" onclick="loadResults()">Retry</button>
      </div>`;
    return;
  }

  if (items && items.error) {
    resultsEl.innerHTML = `
      <div class="error-state">
        ⚠️ ${items.error}<br/>
        <button class="secondary" style="margin-top:12px" onclick="loadResults()">Retry</button>
      </div>`;
    return;
  }
  if (!Array.isArray(items) || items.length === 0) {
    resultsEl.innerHTML = `<div class="empty-state">Nothing found yet — try adjusting genres or check back later.</div>`;
    return;
  }

  resultsEl.innerHTML = `<div class="grid">${items.map(renderCard).join("")}</div>`;
}

function renderCard(item) {
  const img = item.image || "https://placehold.co/300x220?text=No+Image";
  const why = item.why ? `<div class="card-why">✨ ${item.why}</div>` : "";
  const links = renderAvailability(item);
  const mainLink = item.listen_link || item.read_link || item.buy_link
    || item.site_url || item.url || item.preview_link || null;

  const cardInner = `
    <img src="${img}" alt="${item.title || ''}" loading="lazy" />
    <div class="card-body">
      <div class="card-title">${item.title || "Untitled"}</div>
      ${why}
      ${links}
    </div>
  `;

  if (mainLink) {
    return `<a class="card" href="${mainLink}" target="_blank" rel="noopener">${cardInner}</a>`;
  }
  return `<div class="card">${cardInner}</div>`;
}

function renderAvailability(item) {
  const parts = [];
  if (item.listen_link) parts.push(`<a href="${item.listen_link}" target="_blank">▶ Listen on Spotify</a>`);
  if (item.read_link) parts.push(`<a href="${item.read_link}" target="_blank">📖 Read free (Gutenberg)</a>`);
  if (item.buy_link) parts.push(`<a href="${item.buy_link}" target="_blank">🛒 Get book</a>`);
  if (item.site_url) parts.push(`<a href="${item.site_url}" target="_blank">ℹ️ More info</a>`);
  if (item.url) parts.push(`<a href="${item.url}" target="_blank">ℹ️ MyAnimeList page</a>`);
  if (item.stores && item.stores.length) parts.push(`<div>🛒 ${item.stores.slice(0, 2).join(", ")}</div>`);
  if (item.streaming && item.streaming.length) parts.push(`<div>📡 ${item.streaming.slice(0, 2).join(", ")}</div>`);
  if (item.free_legal_hint) parts.push(`<div>🆓 Try: ${item.free_legal_hint.join(", ")}</div>`);
  return parts.length ? `<div class="card-links">${parts.join("")}</div>` : "";
}

// ---------------------------------------------------------------------------
// ROOT RENDER
// ---------------------------------------------------------------------------
function render() {
  if (!state.onboardingDone) {
    renderOnboarding();
  } else {
    renderShell();
  }
}

// ---------------------------------------------------------------------------
// THEME TOGGLE
// ---------------------------------------------------------------------------
function initTheme() {
  const saved = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeButton(saved);

  document.getElementById("theme-toggle-btn").addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    updateThemeButton(next);
  });
}

function updateThemeButton(theme) {
  const btn = document.getElementById("theme-toggle-btn");
  btn.textContent = theme === "dark" ? "🌙 Dark" : "☀️ Light";
}

initTheme();
render();