# GitHub Pages Setup

This project uses GitHub Pages to host documentation at:
**https://fork-tongue.github.io/collagraph/**

## One-Time Setup

1. **Enable GitHub Pages** in the repository:
   - Go to: https://github.com/fork-tongue/collagraph/settings/pages
   - Under "Source", select "Deploy from a branch"
   - Under "Branch", select `gh-pages` and `/ (root)`
   - Click "Save"

2. **First deployment**:
   The workflow will automatically run when you push changes to `docs/**` or `mkdocs.yml`.

   Or trigger manually:
   - Go to: https://github.com/fork-tongue/collagraph/actions/workflows/docs.yml
   - Click "Run workflow"

3. **Wait for deployment**:
   - Check the Actions tab to see the workflow progress
   - Once complete, visit: https://fork-tongue.github.io/collagraph/

## How It Works

1. The GitHub Actions workflow (`.github/workflows/docs.yml`) runs when:
   - Changes are pushed to `docs/**` or `mkdocs.yml` on the `master` branch
   - Manually triggered via the Actions tab

2. The workflow:
   - Checks out the code
   - Installs uv and Python
   - Installs docs dependencies with `uv sync --group docs`
   - Builds and deploys with `uv run mkdocs gh-deploy`

3. MkDocs creates a `gh-pages` branch with the built site

4. GitHub Pages serves the site from the `gh-pages` branch

## Local Development

Build and serve locally:
```bash
uv sync --group docs
uv run mkdocs serve
```

Open http://127.0.0.1:8000

## Manual Deployment

Deploy manually from your machine:
```bash
uv run mkdocs gh-deploy
```

This requires push access to the repository.

## Troubleshooting

**404 Not Found:**
- Ensure GitHub Pages is enabled and set to the `gh-pages` branch
- Check that the workflow ran successfully in the Actions tab
- Wait a few minutes for changes to propagate

**Workflow fails:**
- Check the Actions tab for error messages
- Ensure `uv sync --group docs` works locally
- Verify `mkdocs.yml` is valid

**Old content showing:**
- Clear your browser cache
- GitHub Pages CDN may take a few minutes to update
