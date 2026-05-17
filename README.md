# Our Family Recipes

A small static recipe website for GitHub Pages. It runs with plain HTML, CSS, and JavaScript, so there is no build step and no paid hosting requirement.

## Edit Recipes

Open `recipes.js` and add or change items in `window.familyRecipes`. Each recipe has:

- `title`, `category`, `timeMinutes`, `servings`, and `source`
- `tags` for search and filtering
- `ingredients`, `steps`, and `notes`
- `accent` for the card color: `green`, `tomato`, `yellow`, `blue`, `purple`, or `red`

## Preview Locally

Open `index.html` in a browser, or run a tiny local server:

```powershell
python -m http.server 8080
```

Then visit `http://localhost:8080`.

## Import Recipes From Markdown

Use `scripts/import_recipes.py` to replace `recipes.js` with recipes from a folder of `*.md` files.

```powershell
python scripts\import_recipes.py "C:\Users\Michael\Documents\Obsidian Vault\PARA\03 Resources\031 Recipes"
```

The importer expects simple Markdown like:

```markdown
Link: https://example.com/recipe

For the sauce:
* 1 tbsp mustard
* 2 tbsp mayonnaise

Preparation (in 10 minutes)

- Mix the sauce.
- Serve.
```

Useful options:

```powershell
python scripts\import_recipes.py "C:\path\to\recipes" --output recipes.js
python scripts\import_recipes.py "C:\path\to\recipes" --recursive
```

After importing, refresh the local preview page.

## Publish On GitHub Pages

GitHub Pages works on a free GitHub account when the repository is public. Do not put private family details in the recipes unless you are comfortable with the site and repository being public.

Upload these files and folders to the root of your public GitHub repository:

- `index.html`
- `styles.css`
- `app.js`
- `recipes.js`
- `README.md`
- `.nojekyll`
- `assets/`
- `scripts/`

Do not upload `.git/` or the stray `recipes-web/` folder.

In GitHub, open the repository and go to **Settings** -> **Pages**. Under **Build and deployment**, choose **Deploy from a branch**, select branch `main` and folder `/ (root)`, then save. Your site will be available at `https://YOUR-USERNAME.github.io/recipes-web/`.

To use `https://YOUR-USERNAME.github.io/` directly, name the repository `YOUR-USERNAME.github.io` and publish from the same root folder.
