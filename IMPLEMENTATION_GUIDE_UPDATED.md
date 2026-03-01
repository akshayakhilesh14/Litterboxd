# Litterboxd – Implementation Guide (HackIllinois 2026)

This guide is the “how it works + how to run it” reference for the **Litterboxd API**. It is written to be usable by:
- teammates spinning up the project locally
- judges / reviewers testing endpoints quickly
- anyone deploying the API to a public domain

> **Source of truth:** the running API’s OpenAPI docs at `/docs`, plus the code in `main.py`, `models.py`, and `database.py`.

---

## 0) What this project is

Litterboxd is a campus bathroom review + real‑time stall availability backend:

- **Bathrooms**: metadata (building, floor, gender), supply fields, accessibility, (optional) **longitude/latitude**
- **Reviews**: numeric ratings + comment + optional image upload (stored in **DigitalOcean Spaces**)
- **AI Vibe Check**: Gemini generates a short summary from reviews
- **Stalls**: “current snapshot” occupancy per stall (for map / availability)
- **Sensors**: IoT devices POST JSON updates to keep stalls current, plus an **events** history table for analytics/prediction
- **Webhooks**: notify facilities coordinators when average rating drops below a threshold
- **Favorites**: user bookmarks

---

## 1) Repo structure (important files)

- `main.py` – FastAPI app + routes
- `models.py` – SQLAlchemy ORM models + Pydantic request/response schemas
- `database.py` – async SQLAlchemy engine + session dependency
- `init_db.py` – create tables / initialize DB
- `ai_service.py` – Gemini integration for vibe check
- `webhooks.py` – outbound webhook delivery logic
- `middleware.py` – request ID + logging middleware
- `requirements.txt` – Python deps
- `static/` – optional minimal UIs served by the API (index/review/map/favorites/reviews)

---

## 2) Environment variables / secrets

Create a `.env` file (copy from `.env.example` if present). **Do not commit `.env`.**

### Required for database
- `MYSQL_PASSWORD` *(required)*
- `MYSQL_USER` *(default: `doadmin`)*
- `MYSQL_HOST` *(default set in `database.py`)*
- `MYSQL_PORT` *(default: `25060`)*
- `MYSQL_DB` *(default: `defaultdb`)*

### Required for AI vibe checks (only needed if you call `/v1/bathrooms/{id}/vibe-check`)  
- `GEMINI_API_KEY`

### Required for image uploads to DigitalOcean Spaces (reviews with images)
**Important:** In `main.py`, the Spaces credentials are currently hardcoded. For production, move them into environment variables and load them with `os.getenv(...)`.

Suggested env vars:
- `DO_SPACES_KEY`
- `DO_SPACES_SECRET`
- `DO_SPACES_REGION` (example: `nyc3`)
- `DO_SPACES_ENDPOINT` (example: `https://nyc3.digitaloceanspaces.com`)
- `DO_SPACES_BUCKET` (example: `litterboxd-space`)

---

## 3) Local setup (dev)

### 3.1 Create venv + install deps
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.2 Initialize DB schema
```bash
python init_db.py
```

### 3.3 Run the API
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3.4 Open docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 4) Database schema (tables)

The schema is created by `Base.metadata.create_all()` (see `database.py` + `init_db.py`).

### bathrooms
Stores bathroom metadata + aggregate fields.

Common columns you’ll see in MySQL:
- `bathroom_id` (PK)
- `building_name` (string)
- `floor_number` (int)
- `bathroom_gender` (string)
- `ai_review` (text, nullable)
- `tp_supply`, `hygiene_supply` (string / nullable)
- `last_cleaned` (datetime / nullable)
- `is_accessible` (bool)
- `avg_rating` (float; derived in practice from reviews, may be 0 if none)
- `longitude`, `latitude` (float/decimal, nullable)

### reviews
- `review_id` (PK)
- `bathroom_id` (FK → bathrooms)
- `rating` (float)
- `comment` (text, nullable)
- `image_url` (text, nullable) – set when an image is uploaded to Spaces
- `created_at` (datetime)

### stalls (current snapshot)
Represents “current truth” used by `/v1/locations`.

- `stall_number` (int; used as stable identifier)
- `bathroom_id` (FK → bathrooms)
- `is_occupied` (bool)
- `last_updated` (datetime)

### events (history)
Each sensor update is also appended to `events` to enable analytics/predictions.

- `event_id` (PK)
- `bathroom_id`
- `stall_number`
- `is_occupied`
- `created_at`

### webhooks
- `webhook_id` (PK)
- `url`
- `event_type` (default `low_supply`)
- `is_active`
- `created_at`
- `last_triggered_at`
- `failure_count`

### favorites
- `favorite_id` (PK)
- `user_id`
- `bathroom_id`
- `created_at`

---

## 5) API endpoints (complete list)

All API endpoints are under `/v1` except the health check and optional UI routes.

### 5.1 Locations / map feed

#### `GET /v1/locations`
Returns bathroom map points **plus live stall counts**, designed for map UIs.

**Response fields**
- `bathroom_id`
- `floor_number`
- `building_name`
- `longitude` (nullable)
- `latitude` (nullable)
- `stalls_open`
- `stalls_total`

**Example**
```bash
curl http://localhost:8000/v1/locations
```

> There is also `GET /locations` (legacy/alias) which returns the same idea but is not guaranteed long‑term.

---

### 5.2 Bathrooms

#### `POST /v1/bathrooms` (201)
Create a bathroom. Building name must be one of the registered buildings in `main.py`.

**Request (JSON)**
```json
{
  "building_name": "Siebel",
  "floor_number": 0,
  "bathroom_gender": "Sombr",
  "tp_supply": "High",
  "hygiene_supply": "High",
  "last_cleaned": "2026-02-28T00:00:00",
  "is_accessible": true
}
```

**Example**
```bash
curl -X POST http://localhost:8000/v1/bathrooms   -H "Content-Type: application/json"   -d '{"building_name":"Siebel","floor_number":0,"bathroom_gender":"Sombr","is_accessible":true}'
```

#### `GET /v1/bathrooms`
List bathrooms. Optional query: `?building=Siebel`

```bash
curl "http://localhost:8000/v1/bathrooms?building=Siebel"
```

#### `GET /v1/bathrooms/{bathroom_id}`
Fetch a single bathroom (includes reviews + stalls via eager loading).

```bash
curl http://localhost:8000/v1/bathrooms/1
```

---

### 5.3 Reviews (with optional image upload)

#### `POST /v1/bathrooms/{bathroom_id}/reviews` (201)
Creates a review. **This endpoint expects `multipart/form-data`** (because image upload is supported).

**Query param**
- `user_id` (required)

**Form fields**
- `rating` (required, 0–10)
- `comment` (optional)
- `image` (optional file upload)

**curl example (no image)**
```bash
curl -X POST "http://localhost:8000/v1/bathrooms/1/reviews?user_id=test@example.com"   -F "rating=8"   -F "comment=Clean and spacious"
```

**curl example (with image)**
```bash
curl -X POST "http://localhost:8000/v1/bathrooms/1/reviews?user_id=test@example.com"   -F "rating=7"   -F "comment=Looks good"   -F "image=@./photo.jpg"
```

Behavior:
- Inserts into `reviews`
- Updates AI summary (if Gemini is configured)
- If average rating drops below `LOW_SUPPLY_THRESHOLD` (currently **4.0**), sends webhooks

#### `PUT /v1/bathrooms/{bathroom_id}/reviews/{review_id}` (200)
Updates a review (JSON body).

```bash
curl -X PUT http://localhost:8000/v1/bathrooms/1/reviews/10   -H "Content-Type: application/json"   -d '{"rating":9,"comment":"Updated review"}'
```

---

### 5.4 AI Vibe Check

#### `GET /v1/bathrooms/{bathroom_id}/vibe-check`
Generates a summary from review comments using Gemini.

```bash
curl http://localhost:8000/v1/bathrooms/1/vibe-check
```

Notes:
- Requires `GEMINI_API_KEY` set, otherwise returns server error (misconfiguration).
- If there are no review comments yet, returns a friendly “no reviews yet” message.

---

### 5.5 Stall snapshot (bathroom-scoped)

#### `POST /v1/bathrooms/{bathroom_id}/stalls`
Sets the current occupancy for a stall (manual update / testing).

**Request (JSON)**
```json
{ "stall_number": 4, "is_occupied": true }
```

```bash
curl -X POST http://localhost:8000/v1/bathrooms/1/stalls   -H "Content-Type: application/json"   -d '{"stall_number":4,"is_occupied":true}'
```

#### `GET /v1/bathrooms/{bathroom_id}/stalls`
Returns all stalls for a bathroom.

```bash
curl http://localhost:8000/v1/bathrooms/1/stalls
```

---

### 5.6 Sensor ingest (device → API)

#### `POST /v1/sensors/stalls`
Primary ingest endpoint for IoT devices.

**Request (JSON)**
```json
{
  "id": "esp32-001",
  "stall_id": 4,
  "is_occupied": true,
  "ts": 1700000000,
  "seq": 15
}
```

**Meaning**
- `stall_id` maps to `stalls.stall_number`
- Updates the **stalls** snapshot row and writes a new **events** row

**curl example**
```bash
curl -X POST http://localhost:8000/v1/sensors/stalls   -H "Content-Type: application/json"   -d '{"id":"esp32-001","stall_id":4,"is_occupied":true,"ts":1700000000,"seq":15}'
```

**ESP32 tips**
- Use the correct host + port: `http://<server-ip>:8000/v1/sensors/stalls`
- If you see HTTP 500, check server logs for validation/DB errors (request IDs are logged).

---

### 5.7 Availability prediction (analytics/prediction)

#### `GET /v1/bathrooms/{bathroom_id}/availability-forecast?minutes=5`
Uses the `events` table to estimate **probability a stall becomes free within T minutes**.
Implementation uses an exponential model:

- If a stall is already free → probability = 1
- If occupied and history exists → `P(free within T) = 1 - exp(-T / avg_occ)`
- If occupied with no history → probability = 0 (conservative default)

```bash
curl "http://localhost:8000/v1/bathrooms/1/availability-forecast?minutes=5"
```

Response includes:
- overall probability at least one stall frees up
- per-stall probabilities + `avg_occupied_seconds`

---

### 5.8 Webhooks

#### `POST /v1/webhooks` (201)
Register a webhook URL.

```bash
curl -X POST http://localhost:8000/v1/webhooks   -H "Content-Type: application/json"   -d '{"url":"https://webhook.site/your-id","event_type":"low_supply"}'
```

#### `GET /v1/webhooks`
```bash
curl http://localhost:8000/v1/webhooks
```

#### `DELETE /v1/webhooks/{webhook_id}` (204)
```bash
curl -X DELETE http://localhost:8000/v1/webhooks/1
```

---

### 5.9 Favorites

#### `POST /v1/users/{user_id}/favorites` (201)
```bash
curl -X POST http://localhost:8000/v1/users/test@example.com/favorites   -H "Content-Type: application/json"   -d '{"bathroom_id":1}'
```

#### `GET /v1/users/{user_id}/favorites`
```bash
curl http://localhost:8000/v1/users/test@example.com/favorites
```

#### `DELETE /v1/users/{user_id}/favorites/{bathroom_id}` (204)
```bash
curl -X DELETE http://localhost:8000/v1/users/test@example.com/favorites/1
```

---

### 5.10 Health

#### `GET /health`
```bash
curl http://localhost:8000/health
```

---

### 5.11 Optional UI routes (not in OpenAPI schema)

These serve simple static HTML from `static/` for demoing quickly:
- `GET /` – list of bathrooms UI
- `GET /review` – review form UI
- `GET /map` – map UI (consumes `/v1/locations`)
- `GET /favorites` – favorites UI
- `GET /reviews` – reviews list UI

---

## 6) Deployment (public domain)

You have two common choices:

### Option A: DigitalOcean App Platform (fastest)
1. Push repo to GitHub
2. Create DO App → “Deploy from GitHub”
3. Add environment variables in App settings (`MYSQL_*`, `GEMINI_API_KEY`, Spaces keys)
4. Set run command (example):
   ```bash
   gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT
   ```
5. Attach your domain:
   - Add domain in DO App settings
   - Add DNS records at the domain registrar (DO tells you which CNAME/A records)

### Option B: Droplet + Nginx (most control)
1. Create an Ubuntu droplet
2. Install Python + deps, pull repo
3. Run app with systemd + gunicorn
4. Put **Nginx** in front for TLS + nice domain routing
5. Point DNS A record to droplet IP

**Minimal Nginx idea**
- `api.yourhackathon-domain.com` → proxy to `localhost:8000`

---

## 7) Troubleshooting checklist (fast)

### 7.1 “422 Unprocessable Entity”
- You hit the wrong endpoint or wrong body type.
- Reviews are **multipart/form-data**, not JSON.

### 7.2 “500 Internal Server Error” from sensor or review
Check:
- DB connection (env vars correct? DB reachable?)
- Schema exists (`python init_db.py`)
- Request payload matches `SensorStallUpdate` (`stall_id` must be int)

### 7.3 DigitalOcean MySQL is “online” but you can’t connect
Common causes:
- **Trusted sources / IP whitelist** not set (DO-managed DBs often require allowing your client IP)
- Wrong port/host/user/password
- Using a network that blocks outbound DB ports

Fix pattern:
- Try connecting from the same host the API runs on (e.g., droplet), not from a random laptop network.
- Validate with `mysql` CLI:
  ```bash
  mysql -u "$MYSQL_USER" -p -h "$MYSQL_HOST" -P "$MYSQL_PORT" -D "$MYSQL_DB"
  ```

### 7.4 Gemini errors
- `GEMINI_API_KEY` missing → `/vibe-check` will fail.
- The API still runs fine without Gemini as long as you don’t call the vibe check endpoint.

---

## 8) Notes for hackathon scoring (API design)

- Single source of truth for live availability: **`/v1/locations`**
- Clear separation between:
  - “manual test updates” (`/v1/bathrooms/{id}/stalls`)
  - “sensor ingest” (`/v1/sensors/stalls`)
- Optional UI routes demonstrate integration quickly without another frontend repo.

---

## 9) Suggested next improvements (if time)

If you want more “wow” for a Web API track:
- Add auth for “faculty-only” create-bathroom (API key header)
- Add rate limiting for sensor ingest
- Add websocket/SSE endpoint for live stall updates (push instead of poll)
- Add `GET /v1/bathrooms/{id}/reviews` (paginate reviews)
- Add `GET /v1/events` analytics endpoints (peak times, occupancy heatmaps)
- Add geo search: `GET /v1/locations?near=lat,lon&radius=...`

---
