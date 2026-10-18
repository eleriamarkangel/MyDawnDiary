# MyDawnDiary frontend

Responsive React, Vite, and TypeScript web app for the existing FastAPI backend.

## Local development

Start the backend at `http://127.0.0.1:8000`, then run from this folder:

```powershell
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/app/`. The Vite development server proxies the frontend API routes to FastAPI, so the browser uses the same API paths as the production build. Registration needs the backend's Resend sender and API key configured as described in `../backend/README.md`.

Vite updates the page automatically when you save frontend files. If you are viewing the FastAPI preview at `http://127.0.0.1:8000/app/`, run `npm run build` again after frontend changes, then press `Ctrl+R` or `F5` in the browser. Use `Ctrl+Shift+R` if the browser still shows the old build.

## Build and theme

```powershell
npm run build
```

The build goes to `dist/`. When it exists, FastAPI serves it at `/app/`; the repository root URL redirects there. `dist/` and `node_modules/` are ignored by Git.

Edit **`src/theme.css`** to change the global palette. Components use the semantic color variables there; `src/styles.css` holds layout and component styles. The horizontal paper rules are CSS gradients, so their color follows the theme. The sunrise illustration is used only on the account introduction.

The frontend covers email registration and verification, sign-in, and manual notes. The diary page lets you browse from today back through 30 previous days, with a date dropdown and one day's notes at a time. All Notes includes older notes beyond that navigation window. A note's **See Diary** button opens its assigned date, including dates older than the picker range. New notes can be assigned to any previous date; future dates are rejected. Trash lists deleted notes and conversations that are still within the three-day restore period and offers a Restore button. The Voice Note control is visibly disabled until on-device transcription is implemented and tested across desktop and mobile browsers.
