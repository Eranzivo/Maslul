# Connection: GitHub

## What it is
Source code + frontend hosting via GitHub Pages.

## When to use
- Deploying frontend changes: `git push origin main` → live in ~1 min
- Reviewing commit history or diffs
- Managing the repo

## Key details
- Repo: https://github.com/eranzivo/Maslul
- Account: infomaslul@gmail.com
- Live URL: https://eranzivo.github.io/Maslul/
- No build step — push index.html directly

## Deployment
```
git add index.html
git commit -m "description"
git push origin main
```
GitHub Pages auto-deploys from `main` branch. Takes ~1 minute to go live.

## Notes
- Backend (Railway) also auto-deploys from `backend/` subfolder on every push to main
- `.gitignore` excludes `.env`, `PWs.txt`, and `*.lnk`
