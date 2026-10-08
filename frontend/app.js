const DOMAINS = [
  { key: "movies", label: "🎬 Movies", shortLabel: "Movies", genres: ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller", "Fantasy"] },
  { key: "series", label: "📺 Series", shortLabel: "Series", genres: ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller", "Fantasy"] },
  { key: "anime", label: "🌸 Anime", shortLabel: "Anime", genres: ["Action", "Comedy", "Drama", "Fantasy", "Romance", "Sci-Fi", "Slice of Life", "Supernatural"] },
  { key: "music", label: "🎵 Music", shortLabel: "Music", genres: [], favoritesLabel: "Favorite singers / artists" },
  { key: "games", label: "🎮 Games", shortLabel: "Games", genres: ["Action", "Adventure", "RPG", "Shooter", "Strategy", "Puzzle", "Sports"] },
  { key: "novels", label: "📚 Novels", shortLabel: "Novels", genres: ["Fiction", "Fantasy", "Mystery", "Romance", "Science Fiction", "Horror", "Biography"] },
  { key: "comics", label: "💥 Comics", shortLabel: "Comics", genres: ["Superhero", "Fantasy", "Horror", "Sci-Fi", "Crime"] },
];

const TMDB_GENRES = {
  28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
  99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
  27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
  10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western", 10759: "Action & Adventure",
  10762: "Kids", 10763: "News", 10764: "Reality", 10765: "Sci-Fi & Fantasy", 10766: "Soap",
  10767: "Talk", 10768: "War & Politics",
};

const initialPreferences = loadPreferences();
const hasSavedTaste = Object.values(initialPreferences).some(preference =>
  (Array.isArray(preference?.genres) && preference.genres.length > 0) ||
  (Array.isArray(preference?.favorites) && preference.favorites.length > 0)
);

const state = {
  preferences: initialPreferences,
  onboardingDone: localStorage.getItem("onboarding_done") === "true",
  view: hasSavedTaste ? "for-me" : "explore",
  activeDomain: "movies",
  items: [],
  visibleItems: [],
  filters: {},
  requestId: 0,
};

function loadPreferences() {
  try { return JSON.parse(localStorage.getItem("preferences") || "{}"); }
  catch { return {}; }
}
function savePreferences() {
  localStorage.setItem("preferences", JSON.stringify(state.preferences));
}
function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
function plainText(value) {
  const parsed = new DOMParser().parseFromString(String(value ?? ""), "text/html");
  return (parsed.body.textContent || "").replace(/\s+/g, " ").trim();
}
function safeURL(value) {
  try {
    const url = new URL(String(value));
    return ["https:", "http:"].includes(url.protocol) ? url.href : "";
  } catch { return ""; }
}
function normalize(value) { return String(value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(); }
function canonicalGenre(value) {
  const genre = normalize(value);
  if (["sci fi", "science fiction", "scifi"].includes(genre)) return "science fiction";
  if (["role playing", "role playing game", "rpg"].includes(genre)) return "rpg";
  return genre;
}
function sameGenre(a, b) { return canonicalGenre(a) === canonicalGenre(b); }
function matchesCatalogGenre(actual, selected) {
  const actualGenre = canonicalGenre(actual);
  const selectedGenre = canonicalGenre(selected);
  if (actualGenre === selectedGenre) return true;
  const aliases = { "hip hop rap": ["hip hop"], "hip hop": ["hip hop rap"] };
  return (aliases[selectedGenre] || []).includes(actualGenre);
}
function domainInfo(key = state.activeDomain) { return DOMAINS.find(domain => domain.key === key) || DOMAINS[0]; }
function selectedGenres() { return state.preferences[state.activeDomain]?.genres || []; }

function itemGenres(item) {
  const supplied = Array.isArray(item.genres) ? item.genres : [];
  const names = supplied.map(genre => typeof genre === "string" ? genre : genre?.name).filter(Boolean);
  const ids = Array.isArray(item.genre_ids) ? item.genre_ids.map(id => TMDB_GENRES[id]).filter(Boolean) : [];
  return [...new Set([...names, ...ids])];
}
function ratingScale() {
  const values = state.items.map(item => Number(item.rating)).filter(Number.isFinite);
  return values.length && Math.max(...values) <= 5 ? 5 : 10;
}
function ratingLabel(value) {
  if (value === undefined || value === null || value === "" || !Number.isFinite(Number(value)) || Number(value) <= 0) return "";
  return `${Number(value).toFixed(1)} / ${ratingScale()}`;
}
function recommendationReason(item) {
  if (state.activeDomain === "music" && state.view === "explore") {
    const genre = itemGenres(item)[0];
    if (genre) return `Catalog genre: ${genre}`;
  }
  const why = plainText(item.why);
  const generic = !why || /trending pick you might enjoy|popular right now|recommended for you/i.test(why);
  if (!generic) return why;
  if (state.view === "for-me") {
    const preferences = selectedGenres();
    const matched = itemGenres(item).filter(genre => preferences.some(pref => sameGenre(pref, genre)));
    if (matched.length) return `Because you like ${matched.slice(0, 2).join(" & ")}`;
    if (Number(item.match_score) > 0) return "A match for your saved preferences";
    if (preferences.length) return `Popular in ${domainInfo().shortLabel} · refining your picks`;
    if (state.activeDomain === "music" && state.preferences.music?.favorites?.length) return `Picked for fans of ${state.preferences.music.favorites.slice(0, 2).join(" & ")}`;
    return `Popular in ${domainInfo().shortLabel} · add genres to personalize`;
  }
  return `A popular ${domainInfo().shortLabel.toLowerCase()} pick`;
}

// ---------------------------------------------------------------------------
// OPTIONAL PREFERENCE SETUP
// ---------------------------------------------------------------------------
function renderOnboarding() {
  document.getElementById("edit-prefs-btn").hidden = true;
  document.getElementById("app").innerHTML = `
    <section class="onboarding" aria-labelledby="onboarding-title">
      <p class="eyebrow">YOUR TASTE, YOUR WAY</p>
      <h2 id="onboarding-title">What are you into?</h2>
      <p class="onboarding-lede">Choose a few favorites to tune your picks. You can skip this or change it any time.</p>
      <div class="preference-groups">${DOMAINS.map(renderPreferenceGroup).join("")}</div>
      <div class="onboarding-actions">
        <button class="button button-quiet" id="skip-btn" type="button">Skip for now <span aria-hidden="true">→</span></button>
        <button class="button button-primary" id="save-btn" type="button">Save my taste <span aria-hidden="true">✦</span></button>
      </div>
    </section>`;

  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const selected = chip.getAttribute("aria-pressed") !== "true";
      chip.setAttribute("aria-pressed", String(selected));
      chip.classList.toggle("selected", selected);
    });
  });
  document.getElementById("skip-btn").addEventListener("click", () => {
    state.onboardingDone = true;
    state.view = "explore";
    localStorage.setItem("onboarding_done", "true");
    render();
  });
  document.getElementById("save-btn").addEventListener("click", () => {
    collectOnboardingSelections();
    state.onboardingDone = true;
    state.view = "for-me";
    localStorage.setItem("onboarding_done", "true");
    render();
  });
}

function renderPreferenceGroup(domain) {
  const saved = state.preferences[domain.key] || {};
  if (domain.key === "music") {
    return `<section class="preference-group"><h3>${escapeHTML(domain.label)}</h3>
      <label class="sr-only" for="music-favorites-input">${escapeHTML(domain.favoritesLabel)} (separate names with commas)</label>
      <input class="text-input" type="text" id="music-favorites-input" value="${escapeHTML((saved.favorites || []).join(", "))}" placeholder="Favorite singers / artists (comma separated)" autocomplete="off" /></section>`;
  }
  return `<section class="preference-group"><h3>${escapeHTML(domain.label)}</h3><div class="chip-row" aria-label="${escapeHTML(domain.shortLabel)} genres">
    ${domain.genres.map(genre => {
      const isSelected = (saved.genres || []).includes(genre);
      return `<button class="chip${isSelected ? " selected" : ""}" type="button" data-domain="${escapeHTML(domain.key)}" data-genre="${escapeHTML(genre)}" aria-pressed="${isSelected}">${escapeHTML(genre)}</button>`;
    }).join("")}</div></section>`;
}

function collectOnboardingSelections() {
  DOMAINS.forEach(domain => {
    if (domain.key === "music") {
      const favorites = (document.getElementById("music-favorites-input")?.value || "").split(",").map(name => name.trim()).filter(Boolean);
      if (favorites.length) state.preferences.music = { favorites };
      else delete state.preferences.music;
    } else {
      const genres = [...document.querySelectorAll(`.chip.selected[data-domain="${domain.key}"]`)].map(chip => chip.dataset.genre);
      if (genres.length) state.preferences[domain.key] = { genres };
      else delete state.preferences[domain.key];
    }
  });
  savePreferences();
}

// ---------------------------------------------------------------------------
// APP SHELL, CATEGORY NAVIGATION, AND API DATA
// ---------------------------------------------------------------------------
function renderShell() {
  document.getElementById("edit-prefs-btn").hidden = false;
  document.getElementById("app").innerHTML = `
    <section class="hero" aria-labelledby="page-title">
      <p class="eyebrow">A BETTER NEXT PICK</p>
      <h2 id="page-title">Find your <span>next favorite</span></h2>
      <p id="page-subtitle">A little less scrolling. A lot more “that’s the one.”</p>
    </section>
    <div class="browse-bar">
      <nav id="top-nav" class="mode-switch" aria-label="Recommendation mode">
        <button type="button" data-view="for-me">For me</button>
        <button type="button" data-view="explore">Explore all</button>
      </nav>
      <p class="browse-hint">Pick a world to explore</p>
    </div>
    <nav class="domain-tabs" id="domain-tabs" aria-label="Entertainment categories" role="tablist"></nav>
    <section id="results" aria-live="polite" aria-busy="true"></section>`;

  document.querySelectorAll("#top-nav button").forEach(button => {
    const active = button.dataset.view === state.view;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
    button.addEventListener("click", () => {
      if (state.view === button.dataset.view) return;
      state.view = button.dataset.view;
      renderShell();
    });
  });

  const tabs = document.getElementById("domain-tabs");
  tabs.innerHTML = DOMAINS.map(domain => `<button type="button" role="tab" data-domain="${domain.key}" class="domain-tab${domain.key === state.activeDomain ? " active" : ""}" aria-selected="${domain.key === state.activeDomain}" aria-controls="results" tabindex="${domain.key === state.activeDomain ? "0" : "-1"}">${escapeHTML(domain.label)}</button>`).join("");
  tabs.querySelectorAll("button").forEach((button, index, buttons) => {
    button.addEventListener("click", () => {
      state.activeDomain = button.dataset.domain;
      renderShell();
      document.querySelector(`[data-domain="${state.activeDomain}"]`)?.focus();
    });
    button.addEventListener("keydown", event => {
      if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const target = event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + buttons.length) % buttons.length;
      buttons[target].focus();
      buttons[target].click();
    });
  });
  document.getElementById("edit-prefs-btn").onclick = renderOnboarding;
  loadResults();
}

async function loadResults() {
  const results = document.getElementById("results");
  if (!results) return;
  const requestId = ++state.requestId;
  const domain = state.activeDomain;
  const selectedMusicGenre = domain === "music" && state.view === "explore" ? (state.filters.music?.genre || "") : "";
  const genreSearch = Boolean(selectedMusicGenre);
  results.setAttribute("aria-busy", "true");
  const loadingText = genreSearch ? `Finding ${selectedMusicGenre} music…` : `Finding ${domainInfo(domain).shortLabel.toLowerCase()} picks…`;
  results.innerHTML = `<div class="loading-state"><span class="loader" aria-hidden="true"></span><p>${escapeHTML(loadingText)}</p></div>`;
  try {
    const options = state.view === "explore" || genreSearch
      ? {}
      : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state.preferences[domain] || {}) };
    const url = genreSearch
      ? `${API_BASE}/search/music?q=${encodeURIComponent(selectedMusicGenre)}&limit=50`
      : `${API_BASE}/${state.view === "explore" ? "explore" : "for-me"}/${encodeURIComponent(domain)}`;
    const response = await fetch(url, options);
    const payload = await response.json();
    if (requestId !== state.requestId) return;
    if (!response.ok) throw new Error(payload?.error || `The server returned ${response.status}.`);
    if (payload?.error) throw new Error(payload.error);
    if (!Array.isArray(payload)) throw new Error("The recommendations service returned an unexpected response.");
    state.items = genreSearch ? catalogGenreResults(payload, selectedMusicGenre) : payload;
    renderResults();
  } catch (error) {
    if (requestId !== state.requestId) return;
    results.setAttribute("aria-busy", "false");
    results.innerHTML = `<div class="message-state error-state"><span class="state-icon" aria-hidden="true">!</span><h3>We couldn't load this shelf</h3><p>${escapeHTML(error.message || "Please try again in a moment.")}</p><button class="button button-secondary" id="retry-btn" type="button">Try again</button></div>`;
    document.getElementById("retry-btn").addEventListener("click", loadResults);
  }
}

function catalogGenreResults(items, genre) {
  const hasGenreMetadata = items.some(item => itemGenres(item).length > 0);
  const matches = hasGenreMetadata
    ? items.filter(item => itemGenres(item).some(itemGenre => matchesCatalogGenre(itemGenre, genre)))
    : items;
  return matches.map(item => ({
    ...item,
    why: item.why || (hasGenreMetadata ? `Listed as ${genre} in the music catalog` : `Search result for ${genre}`),
  }));
}

async function loadMusicGenreResults(genre) {
  const results = document.getElementById("results");
  const grid = document.getElementById("result-grid");
  if (!results || !grid) return;
  const requestId = ++state.requestId;
  results.setAttribute("aria-busy", "true");
  grid.hidden = false;
  document.getElementById("filtered-empty").hidden = true;
  grid.className = "grid";
  grid.innerHTML = `<div class="genre-search-status" role="status">Searching the music catalog for <strong>${escapeHTML(genre)}</strong>…</div>`;
  try {
    const response = await fetch(`${API_BASE}/search/music?q=${encodeURIComponent(genre)}&limit=50`);
    const payload = await response.json();
    if (requestId !== state.requestId) return;
    if (!response.ok) throw new Error(payload?.error || `The server returned ${response.status}.`);
    if (payload?.error) throw new Error(payload.error);
    if (!Array.isArray(payload)) throw new Error("The music catalog returned an unexpected response.");
    state.items = catalogGenreResults(payload, genre);
    results.setAttribute("aria-busy", "false");
    renderFilteredItems();
  } catch (error) {
    if (requestId !== state.requestId) return;
    results.setAttribute("aria-busy", "false");
    grid.className = "grid";
    grid.innerHTML = `<div class="genre-search-status" role="alert">${escapeHTML(error.message || "Could not load this genre.")} <button class="button button-secondary" id="retry-genre-search" type="button">Try again</button></div>`;
    document.getElementById("retry-genre-search").addEventListener("click", () => loadMusicGenreResults(genre));
  }
}

function renderResults() {
  const results = document.getElementById("results");
  if (!results) return;
  results.setAttribute("aria-busy", "false");
  const domain = domainInfo();
  results.innerHTML = `
    <div class="shelf-heading"><div><p class="eyebrow">${state.view === "for-me" ? "CURATED FOR YOU" : domain.key === "music" ? "BROWSE BY GENRE" : "THE FULL COLLECTION"}</p><h2>${escapeHTML(domain.label)}</h2></div><span class="result-count" id="result-count"></span></div>
    ${domain.key === "music" ? `<p class="catalog-note">Genre labels follow the music catalog. Choose a genre to search that category beyond this starting mix.</p>` : ""}
    <section class="filter-panel" aria-label="Filter and sort recommendations">
      <label class="filter-search"><span class="sr-only">Search ${escapeHTML(domain.shortLabel)}</span><span class="search-icon" aria-hidden="true">⌕</span><input type="search" id="filter-search" placeholder="Search titles, stories, genres…" value="${escapeHTML(state.filters[domain.key]?.query || "")}" /></label>
      <label class="filter-control"><span>Genre</span><select id="filter-genre"><option value="">${domain.key === "music" ? "Popular mix" : "All genres"}</option>${availableGenres().map(genre => `<option value="${escapeHTML(genre)}">${escapeHTML(genre)}</option>`).join("")}</select></label>
      <label class="filter-control rating-filter"><span>Min rating <output id="rating-output">Any</output></span><input type="range" id="filter-rating" min="0" max="${ratingScale()}" step="0.5" value="${Number(state.filters[domain.key]?.minRating || 0)}" /></label>
      <label class="filter-control"><span>Sort by</span><select id="filter-sort"><option value="recommended">Recommended</option><option value="rating-desc">Top rated</option><option value="title-asc">Title A–Z</option></select></label>
      <button class="clear-filters" id="clear-filters" type="button">Reset</button>
    </section>
    <div class="grid" id="result-grid"></div>
    <div id="filtered-empty" class="message-state empty-state" hidden><h3>No picks match those filters</h3><p>Try a different search or reset the filters.</p><button class="button button-secondary" id="empty-reset" type="button">Reset filters</button></div>`;
  const current = state.filters[domain.key] || {};
  document.getElementById("filter-genre").value = current.genre || "";
  document.getElementById("filter-sort").value = current.sort || "recommended";
  const range = document.getElementById("filter-rating");
  const output = document.getElementById("rating-output");
  const update = () => {
    const previousGenre = state.filters[domain.key]?.genre || "";
    state.filters[domain.key] = {
      query: document.getElementById("filter-search").value,
      genre: document.getElementById("filter-genre").value,
      minRating: Number(range.value),
      sort: document.getElementById("filter-sort").value,
    };
    output.value = Number(range.value) ? `${Number(range.value).toFixed(1)}+` : "Any";
    output.textContent = output.value;
    if (domain.key === "music" && state.view === "explore" && previousGenre !== state.filters[domain.key].genre) {
      if (state.filters[domain.key].genre) loadMusicGenreResults(state.filters[domain.key].genre);
      else loadResults();
      return;
    }
    renderFilteredItems();
  };
  ["filter-search", "filter-genre", "filter-rating", "filter-sort"].forEach(id => document.getElementById(id).addEventListener(id === "filter-search" ? "input" : "change", update));
  range.addEventListener("input", update);
  const resetFilters = () => {
    state.filters[domain.key] = {};
    if (domain.key === "music" && state.view === "explore") loadResults();
    else renderResults();
  };
  document.getElementById("clear-filters").addEventListener("click", resetFilters);
  document.getElementById("empty-reset").addEventListener("click", resetFilters);
  output.value = Number(range.value) ? `${Number(range.value).toFixed(1)}+` : "Any";
  output.textContent = output.value;
  renderFilteredItems();
}

function availableGenres() {
  const genres = state.items.flatMap(itemGenres);
  if (state.activeDomain === "music") genres.push("Bollywood", "Dance", "Hip-Hop", "Hip-Hop/Rap", "Indian", "Indian Pop", "Pop", "Punjabi", "Punjabi Pop", "R&B/Soul", "Rock", "Soundtrack");
  return [...new Set(genres)].sort((a, b) => a.localeCompare(b));
}
function renderFilteredItems() {
  const domain = domainInfo();
  const filters = state.filters[domain.key] || {};
  const query = normalize(filters.query);
  let items = state.items.filter(item => {
    const searchable = normalize([item.title, plainText(item.overview), item.publisher, ...itemGenres(item), ...(item.platforms || [])].join(" "));
    const queryMatches = !query || searchable.includes(query);
    const genreMatches = !filters.genre || itemGenres(item).some(genre => normalize(genre) === normalize(filters.genre));
    const rating = Number(item.rating);
    const ratingMatches = !Number(filters.minRating) || (Number.isFinite(rating) && rating >= Number(filters.minRating));
    return queryMatches && genreMatches && ratingMatches;
  });
  if (filters.sort === "rating-desc") items = [...items].sort((a, b) => Number(b.rating || 0) - Number(a.rating || 0));
  if (filters.sort === "title-asc") items = [...items].sort((a, b) => String(a.title || "").localeCompare(String(b.title || "")));
  state.visibleItems = items;
  document.getElementById("result-count").textContent = `${items.length} ${items.length === 1 ? "pick" : "picks"}`;
  const grid = document.getElementById("result-grid");
  const empty = document.getElementById("filtered-empty");
  grid.hidden = items.length === 0;
  empty.hidden = items.length !== 0;
  if (domain.key === "music" && !filters.genre) {
    const groups = new Map();
    items.forEach((item, index) => {
      const genre = itemGenres(item)[0] || "Other";
      if (!groups.has(genre)) groups.set(genre, []);
      groups.get(genre).push({ item, index });
    });
    const orderedGroups = [...groups.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));
    grid.className = "result-collection";
    grid.innerHTML = orderedGroups.map(([genre, entries]) => `
      <section class="genre-shelf" aria-label="${escapeHTML(genre)} music">
        <div class="genre-shelf-heading"><h3>${escapeHTML(genre)}</h3><span>${entries.length} ${entries.length === 1 ? "track" : "tracks"}</span></div>
        <div class="grid genre-shelf-grid">${entries.map(({ item, index }) => renderCard(item, index)).join("")}</div>
      </section>`).join("");
  } else {
    grid.className = "grid";
    grid.innerHTML = items.map(renderCard).join("");
  }
  grid.querySelectorAll(".card-open").forEach(button => button.addEventListener("click", () => openDetails(Number(button.dataset.index))));
  grid.querySelectorAll(".card-image").forEach(image => image.addEventListener("error", () => {
    image.hidden = true;
    image.closest(".card-art")?.classList.add("image-missing");
  }, { once: true }));
}

function renderCard(item, index) {
  const title = plainText(item.title) || "Untitled";
  const image = safeURL(item.image);
  const genres = itemGenres(item).slice(0, 2);
  const rating = ratingLabel(item.rating);
  const domain = domainInfo();
  const musicCredits = Array.isArray(item.artists) ? item.artists.filter(Boolean).slice(0, 2) : [];
  const source = domain.key === "music"
    ? ([musicCredits.join(", "), item.album].filter(Boolean).join(" · ") || "Music pick")
    : item.free_legal_hint?.length ? `Availability varies · ${item.free_legal_hint.slice(0, 2).join(", ")}`
      : item.streaming?.length ? `Streaming: ${item.streaming.slice(0, 2).join(", ")}`
        : item.stores?.length ? `Stores: ${item.stores.slice(0, 2).join(", ")}`
          : item.platforms?.length ? item.platforms.slice(0, 2).join(" · ") : "Open for details";
  return `<article class="card" style="--card-index:${Math.min(index, 12)}">
    <button class="card-open" type="button" data-index="${index}" aria-label="View details for ${escapeHTML(title)}">
      <span class="card-art">${image ? `<img class="card-image" src="${escapeHTML(image)}" alt="" loading="lazy" />` : `<span class="image-fallback" aria-hidden="true">${escapeHTML(domain.label.split(" ").at(-1))}</span>`}<span class="art-overlay" aria-hidden="true">View details <span>↗</span></span>${rating ? `<span class="rating-pill">★ ${escapeHTML(rating)}</span>` : ""}</span>
      <span class="card-body"><span class="card-title">${escapeHTML(title)}</span><span class="card-why">✦ ${escapeHTML(recommendationReason(item))}</span>${genres.length ? `<span class="card-tags">${genres.map(genre => `<span class="mini-tag">${escapeHTML(genre)}</span>`).join("")}</span>` : ""}<span class="card-source">${escapeHTML(source)}</span></span>
    </button></article>`;
}

function detailsLinks(item) {
  const links = [];
  const provider = String(item.provider || "").toLowerCase();
  const listenLabel = provider.includes("apple") ? "Open in Apple Music" : provider.includes("spotify") ? "Open in Spotify" : "Listen";
  const candidates = [
    [listenLabel, item.listen_link], ["Read free", item.read_link], ["Get the book", item.buy_link],
    ["Official / reference page", item.site_url], ["Anime reference", item.url], ["Preview", item.preview_link],
  ];
  candidates.forEach(([label, rawURL]) => {
    const href = safeURL(rawURL);
    if (href && !links.some(link => link.href === href)) links.push({ label, href });
  });
  if (state.activeDomain === "music") {
    const artists = Array.isArray(item.artists) ? item.artists.join(" ") : "";
    const query = encodeURIComponent(`${plainText(item.title)} ${artists}`.trim());
    links.push({ label: "Search on Gaana", href: `https://gaana.com/search/${query}` });
  }
  if ((state.activeDomain === "movies" || state.activeDomain === "series") && item.id) {
    const kind = item.tmdb_media_type === "tv" || state.activeDomain === "series" ? "tv" : "movie";
    const href = `https://www.themoviedb.org/${kind}/${encodeURIComponent(item.id)}`;
    if (!links.some(link => link.href === href)) links.push({ label: "More details on TMDB", href });
  }
  if (state.activeDomain === "games" && Array.isArray(item.stores) && item.stores.length) {
    const search = encodeURIComponent(`${plainText(item.title)} ${item.stores.slice(0, 2).join(" ")}`);
    links.push({ label: "Find a listed store", href: `https://www.google.com/search?q=${search}` });
  }
  if (!links.length) {
    const search = encodeURIComponent(`${plainText(item.title)} ${domainInfo().shortLabel}`);
    links.push({ label: `Search ${domainInfo().shortLabel.toLowerCase()} details`, href: `https://www.google.com/search?q=${search}` });
  }
  return links;
}

function openDetails(index) {
  const item = state.visibleItems[index];
  if (!item) return;
  const dialog = document.getElementById("details-dialog");
  const title = plainText(item.title) || "Untitled";
  const synopsis = plainText(item.overview) || (state.activeDomain === "music" ? "" : "A full description is not available yet.");
  const genres = itemGenres(item);
  const rating = ratingLabel(item.rating);
  const image = safeURL(item.image);
  const preview = state.activeDomain === "music" ? safeURL(item.preview_url) : "";
  const facts = [];
  if (item.start_year) facts.push(["Started", item.start_year]);
  if (item.publisher) facts.push(["Publisher", item.publisher]);
  if (state.activeDomain === "music" && item.artists?.length) facts.push(["Artist", item.artists.join(", ")]);
  if (state.activeDomain === "music" && item.album) facts.push(["Album", item.album]);
  if (state.activeDomain === "music" && item.release_year) facts.push(["Released", item.release_year]);
  if (item.platforms?.length) facts.push(["Platforms", item.platforms.slice(0, 5).join(", ")]);
  if (item.stores?.length) facts.push(["Stores", item.stores.slice(0, 4).join(", ")]);
  const providers = [...new Set([...(item.free_legal_hint || []), ...(item.streaming || [])])];
  document.getElementById("detail-content").innerHTML = `
    ${image ? `<div class="detail-art"><img src="${escapeHTML(image)}" alt="" /></div>` : ""}
    <div class="detail-copy"><p class="eyebrow">${escapeHTML(domainInfo().label)} ${rating ? `· ★ ${escapeHTML(rating)}` : ""}</p>
      <h2 id="detail-title">${escapeHTML(title)}</h2>
      <p class="detail-reason">✦ ${escapeHTML(recommendationReason(item))}</p>
      ${synopsis ? `<p class="detail-overview">${escapeHTML(synopsis)}</p>` : ""}
      ${genres.length ? `<div class="detail-tags" aria-label="Genres">${genres.map(genre => `<span class="mini-tag">${escapeHTML(genre)}</span>`).join("")}</div>` : ""}
      ${facts.length ? `<dl class="detail-facts">${facts.map(([label, value]) => `<div><dt>${escapeHTML(label)}</dt><dd>${escapeHTML(value)}</dd></div>`).join("")}</dl>` : ""}
      ${preview ? `<section class="music-preview" aria-label="Music preview"><p class="music-preview-label">30-second preview</p><audio id="music-preview-player" controls preload="metadata" src="${escapeHTML(preview)}" aria-label="Preview ${escapeHTML(title)}"></audio><small>Short sample provided by the music catalog. Full playback opens on the linked service.</small></section>` : ""}
      ${providers.length ? `<p class="availability-note"><strong>Availability suggestions:</strong> ${escapeHTML(providers.join(", "))}. Check your region and provider for current availability.</p>` : ""}
      <div class="detail-actions">${detailsLinks(item).map(link => `<a class="button button-primary" href="${escapeHTML(link.href)}" target="_blank" rel="noopener noreferrer">${escapeHTML(link.label)} <span aria-hidden="true">↗</span></a>`).join("")}</div>
    </div>`;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  document.querySelector(".dialog-close").focus();
}

// ---------------------------------------------------------------------------
// THEME, MODAL, AND BOOT
// ---------------------------------------------------------------------------
function initTheme() {
  const saved = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeButton(saved);
  document.getElementById("theme-toggle-btn").addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    updateThemeButton(next);
  });
}
function updateThemeButton(theme) {
  const button = document.getElementById("theme-toggle-btn");
  button.textContent = theme === "dark" ? "☼ Light" : "☾ Dark";
  button.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} theme`);
}
function initModal() {
  const dialog = document.getElementById("details-dialog");
  document.querySelector(".dialog-close").addEventListener("click", () => dialog.close?.());
  dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close?.(); });
  dialog.addEventListener("close", () => {
    const preview = dialog.querySelector("#music-preview-player");
    if (preview) { preview.pause(); preview.currentTime = 0; }
    document.querySelector(".card-open")?.focus();
  });
}

function render() {
  if (state.onboardingDone) renderShell();
  else renderOnboarding();
}

initTheme();
initModal();
render();
