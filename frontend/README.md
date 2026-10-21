# SWSS Frontend

Frontend for the Social Welfare Support System (SWSS). It uses plain
JavaScript, React, Vite, Tailwind CSS, shadcn/ui, React Router, and TanStack
Query.

## Run locally

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Create `.env` from `.env.example` when the API is
not running at the default address.

```env
VITE_API_URL=http://127.0.0.1:8000
```

Useful checks:

```powershell
npm run lint
npm run build
```

## Temporary login

The current local-only login is:

- Username: `Admin`
- Password: `Admin@123`

Authentication is stored in `sessionStorage`. Replace this before production.

## Folder map

```text
src/
  app/                 Router, providers, shell, dashboard, errors
  components/ui/       Shared shadcn components
  components/layout/   Sidebar, top bar, and page header
  components/explain/  Confidence and evidence display helpers
  features/            One owned folder per backend component
  i18n/                English, Sinhala, and Tamil resources
  lib/                 API, auth, environment, and utility helpers
```

Feature folders match the backend component names:

- `beneficiary_selection`
- `evidence_trust`
- `livelihood_planning`
- `market_risk`

## Ownership

Members edit only their own `src/features/<name>/` folder. Shared folders,
configuration, dependencies, and layout code belong to the project leader.
ESLint blocks imports from one feature into another; shared behavior belongs in
`src/components/` or `src/lib/` after leader approval.

## Add a page

1. Add the page component under the feature's `pages/` folder.
2. Add one route object to that feature's `routes.jsx`.
3. Add one matching item to that feature's `nav.js`.

The shared router and sidebar read the feature registry automatically. A
feature with an empty `items` array in `nav.js` appears as a label and icon
without a link or chevron, and it has no dashboard quick link. Members enable
their feature by adding matching entries to both `routes.jsx` and the `items`
array in `nav.js`.

The page title comes from the top bar, taken from the nav item, so pages should
not repeat it.
