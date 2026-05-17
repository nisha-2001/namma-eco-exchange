# Namma EcoExchange — Backend (Hackathon Build)

User-centric API: enter kg of waste → Claude prices the reward dynamically → graph shows history.

## What's built

| Endpoint                                  | What it does                                               |
| ----------------------------------------- | ---------------------------------------------------------- |
| `POST /api/v1/users/`                     | Register a user (name, email, address, rating, plant link) |
| `GET /api/v1/users/{id}`                  | User profile + points balance                              |
| `GET /api/v1/users/{id}/transactions`     | Points history                                             |
| `POST /api/v1/rewards/{id}/preview`       | **Core** — enter kg, get AI-priced points estimate         |
| `GET /api/v1/rewards/{id}/history?days=7` | **Graph data** — multiplier history over time              |
| `POST /api/v1/plants/`                    | Create a biogas plant                                      |
| `GET /api/v1/plants/`                     | List plants                                                |
| `PATCH /api/v1/plants/{id}/fill`          | Update plant fill % (drives pricing)                       |
| `POST /api/v1/plants/drop-off-points/`    | Add a drop-off point                                       |

Interactive docs: **http://localhost:8000/docs**

---

## How the graph works

Every call to `/rewards/{id}/preview` saves a row to `reward_previews` with:

- timestamp, multiplier, plant_fill_pct, demand_level, user_rating

`/rewards/{id}/history` queries these rows and returns them as a time-series.
The frontend plots `points_per_kg` on the Y axis and `timestamp` on the X axis.

**For the hackathon**: run `python scripts/seed.py` to pre-fill 7 days × 24 hours of
realistic history so the graph looks live from day one.

---

## Setup

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Create .env
cp .env.example .env
# Set DATABASE_URL and ANTHROPIC_API_KEY

# 3. Start Postgres (or use Docker)
docker run -d --name pg -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:16

# 4. Create DB
docker exec -it pg psql -U postgres -c "CREATE DATABASE ecoexchange;"

# 5. Seed demo data (creates plant + 2 users + 7 days of graph data)
python scripts/seed.py

# 6. Run the server
uvicorn app.main:app --reload --port 8000
```

## Graph API response shape

```json
GET /api/v1/rewards/{user_id}/history?days=7

{
  "user_rating": 4.8,
  "current_multiplier": 1.9,
  "current_points_per_kg": 19.0,
  "history": [
    {
      "timestamp": "2026-04-18T06:23:00Z",
      "multiplier": 1.6,
      "points_per_kg": 16.0,
      "plant_fill_pct": 22.4,
      "demand_level": "high"
    },
    ...
  ]
}
```

Plot `points_per_kg` vs `timestamp`. Show two lines for high vs low rating users to demonstrate how AI rewards quality depositors more.

## Scalability note

`reward_previews` is append-only and indexed on `(user_id, created_at)`.
At Bengaluru city scale (~50k previews/day) this table stays fast in Postgres for years.
When you add BigQuery later: stream rows from this table, schema doesn't change.
