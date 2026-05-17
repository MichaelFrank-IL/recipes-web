(function () {
  const recipes = window.familyRecipes || [];
  const state = {
    search: "",
    category: "all",
    sort: "family",
    favoritesOnly: false,
    selectedId: recipes[0] ? recipes[0].id : null
  };

  const favoriteKey = "familyRecipeFavorites";
  const favorites = new Set(readFavorites());

  const grid = document.querySelector("#recipeGrid");
  const detail = document.querySelector("#recipeDetail");
  const count = document.querySelector("#recipeCount");
  const searchInput = document.querySelector("#searchInput");
  const sortSelect = document.querySelector("#sortSelect");
  const filterGroup = document.querySelector(".filter-group");
  const favoriteFilter = document.querySelector("#favoriteFilter");

  function readFavorites() {
    try {
      return JSON.parse(localStorage.getItem(favoriteKey)) || [];
    } catch (error) {
      return [];
    }
  }

  function saveFavorites() {
    try {
      localStorage.setItem(favoriteKey, JSON.stringify(Array.from(favorites)));
    } catch (error) {
      return;
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function listItems(items, tagName) {
    return items.map((item) => `<${tagName}>${escapeHtml(item)}</${tagName}>`).join("");
  }

  function sourceMarkup(recipe) {
    const source = escapeHtml(recipe.source);
    if (!recipe.sourceUrl) {
      return source;
    }

    return `<a href="${escapeHtml(recipe.sourceUrl)}" target="_blank" rel="noreferrer">${source}</a>`;
  }

  function recipeTags(recipe) {
    return recipe.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
  }

  function uniqueCategories() {
    return Array.from(new Set(recipes.map((recipe) => recipe.category)));
  }

  function renderCategoryButtons() {
    const buttons = uniqueCategories().map((category) => {
      const button = document.createElement("button");
      button.className = "filter-button";
      button.type = "button";
      button.dataset.category = category;
      button.textContent = category;
      return button;
    });

    buttons.forEach((button) => filterGroup.appendChild(button));
  }

  function searchableText(recipe) {
    return [
      recipe.title,
      recipe.category,
      recipe.source,
      recipe.intro,
      recipe.tags.join(" "),
      recipe.ingredients.join(" ")
    ].join(" ").toLowerCase();
  }

  function filteredRecipes() {
    const query = state.search.trim().toLowerCase();
    return recipes
      .filter((recipe) => state.category === "all" || recipe.category === state.category)
      .filter((recipe) => !state.favoritesOnly || favorites.has(recipe.id))
      .filter((recipe) => !query || searchableText(recipe).includes(query))
      .sort((a, b) => {
        if (state.sort === "title") {
          return a.title.localeCompare(b.title);
        }

        if (state.sort === "time") {
          return a.timeMinutes - b.timeMinutes;
        }

        return recipes.indexOf(a) - recipes.indexOf(b);
      });
  }

  function recipeTime(recipe) {
    if (!recipe.timeMinutes) {
      return "Time not listed";
    }

    return recipe.timeMinutes < 60
      ? `${recipe.timeMinutes} min`
      : `${Math.floor(recipe.timeMinutes / 60)} hr ${recipe.timeMinutes % 60 || ""} min`.replace("  min", "");
  }

  function recipeMeta(recipe) {
    const time = recipeTime(recipe);
    if (!recipe.servings || recipe.servings === "Not listed") {
      return time;
    }

    return `${time} | Serves ${escapeHtml(recipe.servings)}`;
  }

  function renderCards() {
    const visibleRecipes = filteredRecipes();
    grid.innerHTML = "";

    count.textContent = `${visibleRecipes.length} ${visibleRecipes.length === 1 ? "recipe" : "recipes"}`;

    if (!visibleRecipes.length) {
      grid.innerHTML = '<p class="empty-state">No recipes match that search.</p>';
      detail.hidden = true;
      return;
    }

    if (!visibleRecipes.some((recipe) => recipe.id === state.selectedId)) {
      state.selectedId = visibleRecipes[0].id;
    }

    visibleRecipes.forEach((recipe) => {
      const card = document.createElement("article");
      card.className = `recipe-card accent-${recipe.accent}`;
      card.dataset.id = recipe.id;

      const isFavorite = favorites.has(recipe.id);
      const isSelected = recipe.id === state.selectedId;

      card.innerHTML = `
        <button class="save-button" type="button" aria-pressed="${isFavorite}" aria-label="${isFavorite ? "Unsave" : "Save"} ${escapeHtml(recipe.title)}">
          ${isFavorite ? "Saved" : "Save"}
        </button>
        <button class="card-button" type="button" aria-pressed="${isSelected}">
          <span class="card-category">${escapeHtml(recipe.category)}</span>
          <h2>${escapeHtml(recipe.title)}</h2>
          <p>${escapeHtml(recipe.intro)}</p>
          <span class="card-meta">${recipeMeta(recipe)}</span>
          <span class="tag-list">${recipeTags(recipe)}</span>
        </button>
      `;

      card.querySelector(".save-button").addEventListener("click", (event) => {
        event.stopPropagation();
        toggleFavorite(recipe.id);
      });

      card.querySelector(".card-button").addEventListener("click", () => {
        state.selectedId = recipe.id;
        render();
        detail.scrollIntoView({ behavior: "smooth", block: "start" });
      });

      grid.appendChild(card);
    });

    renderDetail();
  }

  function toggleFavorite(id) {
    if (favorites.has(id)) {
      favorites.delete(id);
    } else {
      favorites.add(id);
    }

    saveFavorites();
    render();
  }

  function renderDetail() {
    const recipe = recipes.find((item) => item.id === state.selectedId);

    if (!recipe) {
      detail.hidden = true;
      return;
    }

    detail.hidden = false;
    detail.className = `recipe-detail accent-${recipe.accent}`;
    detail.innerHTML = `
      <div class="detail-heading">
        <div>
          <span class="card-category">${escapeHtml(recipe.category)}</span>
          <h2>${escapeHtml(recipe.title)}</h2>
          <p>${escapeHtml(recipe.intro)}</p>
        </div>
        <div class="detail-actions">
          <button class="quiet-button" type="button" id="detailFavorite">
            ${favorites.has(recipe.id) ? "Saved" : "Save"}
          </button>
          <button class="print-button" type="button" id="printRecipe">Print</button>
        </div>
      </div>

      <dl class="detail-stats">
        <div>
          <dt>Time</dt>
          <dd>${recipeTime(recipe)}</dd>
        </div>
        <div>
          <dt>Serves</dt>
          <dd>${escapeHtml(recipe.servings)}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>${sourceMarkup(recipe)}</dd>
        </div>
      </dl>

      <div class="recipe-columns">
        <section>
          <h3>Ingredients</h3>
          <ul>${listItems(recipe.ingredients, "li")}</ul>
        </section>
        <section>
          <h3>Method</h3>
          <ol>${listItems(recipe.steps, "li")}</ol>
        </section>
      </div>

      <section class="notes">
        <h3>Notes</h3>
        <ul>${listItems(recipe.notes, "li")}</ul>
      </section>
    `;

    detail.querySelector("#detailFavorite").addEventListener("click", () => toggleFavorite(recipe.id));
    detail.querySelector("#printRecipe").addEventListener("click", () => window.print());
  }

  function renderFilters() {
    document.querySelectorAll(".filter-button").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.category === state.category);
    });

    favoriteFilter.classList.toggle("is-active", state.favoritesOnly);
    favoriteFilter.setAttribute("aria-pressed", String(state.favoritesOnly));
  }

  function render() {
    renderFilters();
    renderCards();
  }

  searchInput.addEventListener("input", (event) => {
    state.search = event.target.value;
    render();
  });

  sortSelect.addEventListener("change", (event) => {
    state.sort = event.target.value;
    render();
  });

  filterGroup.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) {
      return;
    }

    state.category = button.dataset.category;
    render();
  });

  favoriteFilter.addEventListener("click", () => {
    state.favoritesOnly = !state.favoritesOnly;
    render();
  });

  renderCategoryButtons();
  render();
})();
