# Study_Group_Matcher
Group project with Jude,JJ,HyunJun

## Web version

The React + TypeScript web client is in [`web/`](web/README.md). It includes an
account-free demo and an API-connected mode for the existing FastAPI backend.
The original Flutter application remains in `frontend/`.

```sh
cd web
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` and select **Explore the demo**.

For a static demo deployment, set the Vercel project root to `web`, build with
`npm run build`, and publish `dist`. Live mode requires a separately deployed
FastAPI backend, `VITE_API_URL`, and validation against the real database.
