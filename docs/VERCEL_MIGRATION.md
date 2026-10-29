# Deploy KOREA RE:READ on Vercel Hobby

This is a **static website**: HTML/CSS/JavaScript with JSON catalogs, no Node/Next.js runtime, no API keys and no database. GitHub remains the source of truth.

## Before migrating
1. In Netlify, set **Stopped builds** (or disconnect the GitHub deploy integration), to prevent future Netlify builds.
2. Keep the existing Netlify project until you have checked the replacement. It is not necessary to delete the source files.
3. Check that the work is a noncommercial personal/academic use eligible for Vercel Hobby.

## Import existing GitHub repository
1. Sign in at https://vercel.com with GitHub; use **Hobby**.
2. Dashboard > **Add New... > Project** (or New Project).
3. Import **itsranyoung/Korea-reread** (authorize Vercel GitHub app for this repository if asked).
4. Project name: `korea-reread` if available.
5. **Framework Preset: Other.**
6. **Root Directory: .** (repository root).
7. **Build Command: python3 scripts/build_static.py**.
8. **Output Directory: .vercel-output-static**.
9. No environment variables required.
10. Click Deploy and inspect the generated `*.vercel.app` address.

The repo's `vercel.json` carries the above build/output settings, and
`git.deploymentEnabled:false` disables automatic deployments. If the
initial Git import refuses to deploy because of that setting, perform
the first deployment manually from the Vercel project Deployments screen
or temporarily enable it via a reviewed commit, then disable again.
Do not leave automatic builds on if you wish to avoid deployment usage.

## Smoke tests after deployment
- `/` shows the 1901–1906 year gallery.
- Choose 1901 > January to see the existing article title entries.
- Choose 1904 or 1906 > a month and view catalog cards.
- Choose 1902, 1903 or 1905: these are not yet published as
  verified article records; their annual-index drafts are excluded.
- `/data/1901.json`, `/data/1904.json`, `/data/1906.json`,
  and `/data/issues-1901-1906.json` return valid JSON.
- Verify that `/scripts/process_archive.py`,
  `/audit/catalog-audit.json`, and `/data/1902-draft.json`
  are NOT publicly accessible.

## Why a small build step?
Repository root includes research scripts, audit reports and unreviewed
catalog drafts. Pointing Vercel's output at the repository root would
risk publishing them. `scripts/build_static.py` copies only three
HTML pages and four approved JSON files into a clean output directory.
It has no third-party Python dependencies. This preserves the existing
webpage and URLs while excluding research-only artifacts.

## Delayed releases
Continue committing changes to GitHub. The Vercel setting
`git.deploymentEnabled:false` prevents automatic Git-based deployments.
When ready to update the public site, use Vercel's **Create Deployment**
or Vercel CLI manually and confirm the release.

## Limitations
Vercel Hobby is subject to plan resource limits and noncommercial-use
restrictions. The code-based static build does not eliminate Vercel usage,
only avoids unnecessary deployment triggers. Large source OCR files should
not be put in the public output or Git repository without licensing and
size review. Previously saved user annotations in browser localStorage
are origin-specific and will not transfer automatically from Netlify
to the new Vercel hostname.
