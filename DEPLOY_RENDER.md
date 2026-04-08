# Deploy ET FactLens on Render

This repo is set up for a two-service Render deployment:

- `et-factlens-backend`: FastAPI web service
- `et-factlens-frontend`: Vite static site
- `et-factlens-redis`: Render Key Value for cache storage

## Before You Deploy

Do not copy the current local `.env` file into Render as-is. The keys in it should be treated as compromised if they were ever committed or shared. Rotate these before production use:

- `GROQ_API_KEY`
- `SERPAPI_KEY`
- `NEWS_API_KEY`
- `HF_API_TOKEN` if you plan to use Hugging Face image inference

## Option 1: Blueprint Deploy

1. Push this repo to GitHub.
2. In Render, choose `New` -> `Blueprint`.
3. Select this repository.
4. Render will detect [render.yaml](/d:/ET_FactLens/render.yaml).
5. Provide secret values for:
   - `GROQ_API_KEY`
   - `SERPAPI_KEY`
   - `NEWS_API_KEY` (optional if unused)
   - `HF_API_TOKEN` (optional if unused)
6. Create the services.

Render will automatically:

- build the backend from `backend/`
- build the frontend from `frontend/`
- connect the backend to Render Key Value
- inject the backend public URL into the frontend build
- inject the frontend public URL into backend `CORS_ORIGINS`

## Option 2: Manual Service Creation

### Backend

Create a `Web Service` with:

- Root Directory: `backend`
- Runtime: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

Set environment variables:

- `GROQ_API_KEY`
- `SERPAPI_KEY`
- `NEWS_API_KEY` if needed
- `HF_API_TOKEN` if needed
- `REDIS_TIMEOUT_SEC=0.15`
- `REDIS_RETRY_AFTER_SEC=30`
- `RAG_SEARCH_TIMEOUT_SEC=2.5`
- `ARTICLE_FETCH_TIMEOUT_SEC=4.0`
- `CORS_ORIGINS=<your frontend Render URL>`

### Redis / Key Value

Create a `Key Value` instance and set these backend env vars from it:

- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_DB=0`

### Frontend

Create a `Static Site` with:

- Root Directory: `frontend`
- Build Command: `npm ci && npm run build`
- Publish Directory: `dist`

Set:

- `VITE_API_BASE_URL=<your backend Render URL>`

Add an SPA rewrite:

- Source: `/*`
- Destination: `/index.html`
- Action: `Rewrite`

## Post-Deploy Checks

After deployment, verify:

1. Backend health works at `/health`
2. Frontend loads without API URL errors
3. Fact check requests reach the backend
4. Voice and image routes work only if their external API keys are configured

## Notes

- The backend reads `.env` only for local development. Render should use dashboard or blueprint environment variables.
- The frontend now accepts either `VITE_API_BASE_URL` or `VITE_API_ORIGIN`. If the value does not end in `/api`, the app appends it automatically.
- Backend CORS is now controlled by `CORS_ORIGINS`.
