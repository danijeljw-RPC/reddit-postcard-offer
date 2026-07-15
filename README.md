# Reddit Postcard Offer

Responsive static website for displaying postcard collection photos and directing requests back to the Reddit thread.

## Repository

The repository is already initialised with `main` as the default branch and this SSH remote:

```text
git@github.com:danijeljw-RPC/reddit-postcard-offer.git
```

Expected GitHub Pages URL:

```text
https://danijeljw-rpc.github.io/reddit-postcard-offer/
```

## Add the postcard photos

Copy approximately 16 photos into:

```text
src/images/
```

Supported source files:

- `.HEIC`
- `.HEIF`
- `.jpg`
- `.jpeg`

Name each file using the heading that should appear above it. The extension is removed from the displayed heading.

Examples:

```text
Australian Animals - 01.HEIC
Australian Animals - 02.HEIC
Vintage Tourism - 01.jpg
```

The generated headings will be:

```text
Australian Animals - 01
Australian Animals - 02
Vintage Tourism - 01
```

HEIC/HEIF originals remain untouched. JPG copies are created beside them in `src/images/`.

## Build locally

### macOS or Linux

```bash
./scripts/build.sh
```

### Windows PowerShell

```powershell
./scripts/build.ps1
```

The generated website is written to `dist/`.

To preview it locally:

```bash
python -m http.server 8000 --directory dist
```

Then open `http://localhost:8000`.

## Run only the HEIC conversion

```bash
python scripts/convert_heic.py
```

Replace previously converted JPG files:

```bash
python scripts/convert_heic.py --overwrite
```

## Edit the wording

Edit:

```text
src/site.json
```

This contains the Reddit link, mailing date, site URL and instructions shown on the page.

The supplied mailing date is **Tuesday, 21 July 2026**. Change it before deploying if required.

## Publish

Push the prepared repository:

```bash
git push -u origin main
```

The GitHub Actions workflow will:

1. Convert HEIC/HEIF files to JPG.
2. Generate the responsive website from the JPG filenames.
3. Publish the built output to the `gh-pages` branch.
4. Deploy the same output through GitHub's official Pages deployment actions.

For the first deployment, open the repository on GitHub and set:

```text
Settings → Pages → Build and deployment → Source → GitHub Actions
```

Every later push to `main` rebuilds and redeploys the site automatically.

## Image behaviour

- Each JPG becomes its own page section.
- The filename without `.jpg` or `.jpeg` is the section heading.
- Photos are naturally sorted, so `Card 2` appears before `Card 10`.
- Images are lazy-loaded and can be opened at full size.
- The layout uses two columns on larger screens and one column on phones/tablets.
