# AI Recommendation Engine

A local, API-first hybrid recommendation system. It combines:
- **Collaborative filtering** (user-item interaction similarity)
- **Content-based filtering** (TF-IDF similarity over product metadata)
- **Hybrid ranking** (weighted blend of both scores)
- **Popularity fallback** for new/unknown users
- SQLite interaction logging and a small browser UI

No API key, cloud account, or paid service is required. The app creates a demo catalog and interactions automatically on first start.

## Requirements
- Windows 10/11, macOS, or Linux
- Python 3.10–3.12 recommended
- Internet only for the first `pip install` (unless packages are already cached)

## Run on Windows
1. Extract the ZIP.
2. Open the extracted `AI_Recommendation_Engine` folder in PowerShell.
3. Run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```

If PowerShell blocks activation, run without activating:

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 run.py
```

Open **http://127.0.0.1:8000** in your browser.
API docs: **http://127.0.0.1:8000/docs**

If `py -3.12` is unavailable, use `python` instead. Python 3.13 may work depending on package wheels; Python 3.10–3.12 is the safest choice.

## Run on macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```

## Project roadmap (step by step)
1. **Define the problem:** recommend relevant products to a user based on their preferences and past interactions.
2. **Prepare data:** create a catalog with product ID, title, category, description, and tags; record ratings/clicks/purchases.
3. **Explore data:** inspect category counts, interaction counts, missing values, and user activity.
4. **Build content-based model:** TF-IDF vectorize product text and calculate cosine similarity.
5. **Build collaborative model:** construct a user-item matrix and find similar users; aggregate their positive interactions.
6. **Build hybrid model:** normalize component scores and blend them with configurable weights.
7. **Handle cold start:** use category preferences when available, otherwise popular products.
8. **Evaluate:** use a per-user holdout split and Precision@K, Recall@K, and NDCG@K.
9. **Serve recommendations:** expose FastAPI endpoints and persist feedback in SQLite.
10. **Build UI:** browse products, choose a user, request recommendations, and submit feedback.
11. **Test and document:** run tests, inspect `/docs`, explain architecture and limitations.
12. **Deploy later:** Docker + cloud hosting can be added after local validation.

## API examples
- `GET /health`
- `GET /api/products`
- `GET /api/users`
- `GET /api/recommendations/{user_id}?limit=5&method=hybrid`
- `POST /api/interactions` with JSON:
```json
{"user_id":"U001","product_id":"P001","event_type":"purchase","rating":5}
```
- `GET /api/metrics`

Supported `method`: `hybrid`, `collaborative`, `content`, `popular`.

## Project structure
```text
app/
  main.py             FastAPI routes
  recommender.py      TF-IDF, collaborative, hybrid algorithms
  data.py             Demo data creation/loading
  database.py         SQLite persistence
  evaluation.py       Offline ranking metrics
  static/index.html   Browser UI
  static/styles.css
  static/app.js
tests/test_recommender.py
run.py
```

## Notes
- Demo data is synthetic, not real customer data.
- This is a portfolio-ready learning baseline, not a production-scale ranking system.
- For production, add authentication, event pipelines, feature stores, monitoring, privacy controls, and time-aware evaluation.
