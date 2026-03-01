# Litterboxd API Developer Guide

**Complete Reference for Building with the Litterboxd API**

Table of Contents:
- [Setup & Configuration](#setup--configuration)
- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [API Endpoints](#api-endpoints)
- [Request & Response Examples](#request--response-examples)
- [Webhook Integration](#webhook-integration)
- [Testing Guide](#testing-guide)
- [Status Codes Reference](#status-codes-reference)

---

## Setup & Configuration

### Prerequisites
- Python 3.10+
- pip package manager
- Google Gemini API key (free tier: https://makersuite.google.com/app/apikey)
- Database credentials (configured automatically for DigitalOcean MySQL)

### Installation

```bash
# 1. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# 4. Initialize database
python init_db.py

# 5. Start API
uvicorn main:app --reload
```

### Environment Variables

**Required:**
- `GEMINI_API_KEY` - Your Google Gemini API key for AI summaries

**Optional:**
- `DATABASE_URL` - MySQL connection string (auto-configured for DigitalOcean)
- `PORT` - Server port (default: 8000)
- `HOST` - Server host (default: 0.0.0.0)

### Starting the Server

**Development (with auto-reload):**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production (Gunicorn + Uvicorn):**
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Server will be available at:
- **API:** http://localhost:8000/v1
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Authentication

Currently, the API uses a simple `user_id` parameter for basic user tracking. All endpoints that require a user ID accept it as:

**Query Parameter:**
```bash
curl "http://localhost:8000/v1/bathrooms/1/reviews?user_id=student@university.edu"
```

**User ID Format:** `string` (typically email or student netid)

**Future:** JWT-based authentication planned for v2.0

---

## Error Handling

### Error Response Format

All errors return a standardized JSON response:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "field": "field_name (if applicable)",
    "constraint": "constraint_type (if applicable)"
  },
  "status_code": 400,
  "request_id": "uuid-for-debugging",
  "timestamp": "2026-03-01T10:30:45.123456"
}
```

### Error Types

| Code | Status | Meaning | Example |
|------|--------|---------|---------|
| `VALIDATION_ERROR` | 400 | Invalid input data | Missing required field |
| `INVALID_RATING` | 400 | Rating not 1-10 | rating: 15 |
| `INVALID_FLOOR` | 400 | Floor < 0 | floor_number: -1 |
| `INVALID_URL` | 400 | URL not http/https | url: "ftp://evil" |
| `INVALID_ID` | 400 | ID not positive | bathroom_id: 0 |
| `INVALID_STALL` | 400 | Stall number invalid | stall_number: -5 |
| `NOT_FOUND` | 404 | Resource missing | GET /bathrooms/9999 |
| `FORBIDDEN` | 403 | Operation denied | Building not registered |
| `CONFLICT` | 409 | Duplicate entry | User already reviewed |
| `INTERNAL_SERVER_ERROR` | 500 | Server error | Database timeout |

### Request ID Tracking

Every request receives a unique UUID for debugging:

```bash
$ curl http://localhost:8000/v1/bathrooms/1
# Response includes: "request_id": "abc123-def456-ghi789"
```

Check your application logs for the request ID to trace issues:

```bash
tail -f api.log | grep "abc123-def456-ghi789"
```

---

## API Endpoints

### Quick Reference

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| **Bathrooms** |
| POST | `/v1/bathrooms` | 201, 400, 403, 409, 500 | Create bathroom |
| GET | `/v1/bathrooms` | 200, 400, 500 | List bathrooms |
| GET | `/v1/bathrooms/{id}` | 200, 404, 500 | Get bathroom details |
| **Reviews** |
| POST | `/v1/bathrooms/{id}/reviews` | 201, 400, 404, 409, 500 | Add review |
| PUT | `/v1/bathrooms/{id}/reviews/{id}` | 200, 400, 404, 500 | Update review |
| GET | `/v1/bathrooms/{id}/vibe-check` | 200, 404, 500 | Get AI summary |
| **Stalls (IoT)** |
| POST | `/v1/bathrooms/{id}/stalls` | 200, 400, 404, 500 | Update stall |
| GET | `/v1/bathrooms/{id}/stalls` | 200, 404, 500 | Get stall data |
| **Webhooks** |
| POST | `/v1/webhooks` | 201, 400, 409, 500 | Register webhook |
| GET | `/v1/webhooks` | 200, 400, 500 | List webhooks |
| DELETE | `/v1/webhooks/{id}` | 204, 404, 500 | Delete webhook |
| **Favorites** |
| POST | `/v1/users/{id}/favorites` | 201, 404, 409, 500 | Add favorite |
| GET | `/v1/users/{id}/favorites` | 200, 500 | List favorites |
| DELETE | `/v1/users/{id}/favorites/{id}` | 204, 404, 500 | Remove favorite |
| **Health** |
| GET | `/health` | 200 | Health check |

---

## Request & Response Examples

### 1. Bathrooms Endpoints

#### Create Bathroom (201 Created)

Only bathrooms in registered buildings (Siebel, Grainger, CIF) can be created.

**Request:**
```bash
curl -X POST http://localhost:8000/v1/bathrooms \
  -H "Content-Type: application/json" \
  -d '{
    "building_name": "Siebel",
    "floor_number": 2,
    "bathroom_gender": "Unisex",
    "tp_supply": "High",
    "hygiene_supply": "High",
    "is_accessible": true
  }'
```

**Response (201):**
```json
{
  "bathroom_id": 1,
  "message": "Bathroom indexed successfully."
}
```

**Error - Invalid Building (403 Forbidden):**
```bash
curl -X POST http://localhost:8000/v1/bathrooms \
  -H "Content-Type: application/json" \
  -d '{
    "building_name": "InvalidBuilding",
    "floor_number": 2,
    "bathroom_gender": "Unisex"
  }'
```

**Response (403):**
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Building InvalidBuilding not registered by faculty. Only Siebel, Grainger, CIF are allowed.",
    "field": null,
    "constraint": null
  },
  "status_code": 403,
  "request_id": "abc-123",
  "timestamp": "2026-03-01T10:30:45"
}
```

**Error - Duplicate Bathroom (409 Conflict):**
```json
{
  "error": {
    "code": "CONFLICT",
    "message": "Bathroom already exists at this location (Siebel, Floor 2, Unisex)",
    "field": null,
    "constraint": null
  },
  "status_code": 409
}
```

**Error - Invalid Floor (400 Bad Request):**
```bash
curl -X POST http://localhost:8000/v1/bathrooms \
  -H "Content-Type: application/json" \
  -d '{
    "building_name": "Siebel",
    "floor_number": -5,
    "bathroom_gender": "Unisex"
  }'
```

**Response (400):**
```json
{
  "error": {
    "code": "INVALID_FLOOR",
    "message": "Floor number must be >= 0",
    "field": "floor_number",
    "constraint": "non-negative"
  },
  "status_code": 400
}
```

---

#### List Bathrooms (200 OK)

```bash
curl http://localhost:8000/v1/bathrooms
```

**Response:**
```json
[
  {
    "bathroom_id": 1,
    "building_name": "Siebel",
    "floor_number": 2,
    "bathroom_gender": "Unisex",
    "ai_review": null,
    "tp_supply": "High",
    "hygiene_supply": "High",
    "is_accessible": true,
    "created_at": "2026-03-01T10:00:00",
    "avg_rating": 0.0,
    "is_low_supply": false,
    "reviews": [],
    "stalls": []
  }
]
```

**Filter by Building:**
```bash
curl "http://localhost:8000/v1/bathrooms?building=Grainger"
```

---

#### Get Bathroom Details (200 OK)

```bash
curl http://localhost:8000/v1/bathrooms/1
```

**Response:**
```json
{
  "bathroom_id": 1,
  "building_name": "Siebel",
  "floor_number": 2,
  "bathroom_gender": "Unisex",
  "ai_review": "This bathroom is clean and spacious.",
  "tp_supply": "High",
  "hygiene_supply": "Medium",
  "is_accessible": true,
  "created_at": "2026-03-01T10:00:00",
  "avg_rating": 8.5,
  "is_low_supply": false,
  "reviews": [
    {
      "review_id": 10,
      "rating": 8,
      "comment": "Great bathroom!"
    }
  ],
  "stalls": [
    {
      "stall_number": 1,
      "is_occupied": false,
      "last_updated": "2026-03-01T10:25:00"
    }
  ]
}
```

**Error - Not Found (404):**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Bathroom not found: ID 9999",
    "field": null,
    "constraint": null
  },
  "status_code": 404
}
```

---

### 2. Reviews Endpoints

#### Add Review (201 Created)

**Important:** Reviews use **Form data**, not JSON body.

**Request:**
```bash
curl -X POST "http://localhost:8000/v1/bathrooms/1/reviews?user_id=student@example.com" \
  -F "rating=8" \
  -F "comment=Clean and well-maintained!"
```

**Response (201):**
```json
{
  "review_id": 42,
  "bathroom_id": 1,
  "rating": 8,
  "comment": "Clean and well-maintained!",
  "created_at": "2026-03-01T10:15:30"
}
```

**Error - Invalid Rating (400):**
```bash
curl -X POST "http://localhost:8000/v1/bathrooms/1/reviews?user_id=student@example.com" \
  -F "rating=15" \
  -F "comment=Invalid"
```

**Response (400):**
```json
{
  "error": {
    "code": "INVALID_RATING",
    "message": "rating must be between 1 and 10",
    "field": "rating",
    "constraint": "range"
  },
  "status_code": 400
}
```

**Error - Duplicate Review (409 Conflict):**
```json
{
  "error": {
    "code": "CONFLICT",
    "message": "User student@example.com has already reviewed this bathroom. Use PUT to update your review.",
    "field": null,
    "constraint": null
  },
  "status_code": 409
}
```

---

#### Get AI Vibe Check (200 OK)

Generates a witty AI summary based on all reviews.

```bash
curl http://localhost:8000/v1/bathrooms/1/vibe-check
```

**Response:**
```json
{
  "bathroom_id": 1,
  "vibe_check": "This bathroom is surprisingly clean for a basement level. The water pressure will blow your face off (in a good way)."
}
```

**With No Reviews (200 OK):**
```json
{
  "bathroom_id": 1,
  "vibe_check": "No reviews yet. Be the first to describe this bathroom!"
}
```

---

### 3. Real-Time Stalls (IoT) Endpoints

#### Update Stall Occupancy (200 OK)

Perfect for IoT sensors (ESP32, Raspberry Pi).

**Request:**
```bash
curl -X POST http://localhost:8000/v1/bathrooms/1/stalls \
  -H "Content-Type: application/json" \
  -d '{
    "stall_number": 1,
    "is_occupied": true
  }'
```

**Response (200):**
```json
{
  "stall_number": 1,
  "bathroom_id": 1,
  "is_occupied": true,
  "last_updated": "2026-03-01T10:20:15"
}
```

**Error - Invalid Stall (400):**
```bash
curl -X POST http://localhost:8000/v1/bathrooms/1/stalls \
  -H "Content-Type: application/json" \
  -d '{
    "stall_number": -1,
    "is_occupied": false
  }'
```

**Response (400):**
```json
{
  "error": {
    "code": "INVALID_STALL",
    "message": "Stall number must be positive",
    "field": "stall_number",
    "constraint": "positive"
  },
  "status_code": 400
}
```

---

#### Get Stall Status (200 OK)

```bash
curl http://localhost:8000/v1/bathrooms/1/stalls
```

**Response:**
```json
[
  {
    "stall_number": 1,
    "bathroom_id": 1,
    "is_occupied": true,
    "last_updated": "2026-03-01T10:20:15"
  },
  {
    "stall_number": 2,
    "bathroom_id": 1,
    "is_occupied": false,
    "last_updated": "2026-03-01T10:18:00"
  }
]
```

---

### 4. Webhooks Endpoints

#### Register Webhook (201 Created)

Receive automatic notifications when a bathroom rating drops below 4.0/10.

**Request:**
```bash
curl -X POST http://localhost:8000/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://facilities.university.edu/alerts",
    "event_type": "low_supply"
  }'
```

**Response (201):**
```json
{
  "webhook_id": 5,
  "url": "https://facilities.university.edu/alerts",
  "event_type": "low_supply",
  "is_active": true,
  "created_at": "2026-03-01T10:25:00",
  "last_triggered_at": null,
  "failure_count": 0
}
```

**Error - Invalid URL (400):**
```bash
curl -X POST http://localhost:8000/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "not-a-url",
    "event_type": "low_supply"
  }'
```

**Response (400):**
```json
{
  "error": {
    "code": "INVALID_URL",
    "message": "URL must start with http:// or https://",
    "field": "url",
    "constraint": "valid_url"
  },
  "status_code": 400
}
```

**Error - Duplicate URL (409 Conflict):**
```json
{
  "error": {
    "code": "CONFLICT",
    "message": "Webhook URL already registered: https://facilities.university.edu/alerts",
    "field": null,
    "constraint": null
  },
  "status_code": 409
}
```

---

#### List Webhooks (200 OK)

```bash
curl http://localhost:8000/v1/webhooks
```

**Response:**
```json
[
  {
    "webhook_id": 5,
    "url": "https://facilities.university.edu/alerts",
    "event_type": "low_supply",
    "is_active": true,
    "created_at": "2026-03-01T10:25:00",
    "last_triggered_at": "2026-03-01T11:00:00",
    "failure_count": 0
  }
]
```

**Filter by Event Type:**
```bash
curl "http://localhost:8000/v1/webhooks?event_type=low_supply"
```

---

#### Delete Webhook (204 No Content)

```bash
curl -X DELETE http://localhost:8000/v1/webhooks/5
```

**Response (204):** No body returned

**Error - Not Found (404):**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Webhook not found: ID 9999",
    "field": null,
    "constraint": null
  },
  "status_code": 404
}
```

---

### 5. Favorites Endpoints

#### Add Favorite (201 Created)

```bash
curl -X POST http://localhost:8000/v1/users/student@example.com/favorites \
  -H "Content-Type: application/json" \
  -d '{"bathroom_id": 1}'
```

**Response (201):**
```json
{
  "favorite_id": 10,
  "user_id": "student@example.com",
  "bathroom_id": 1,
  "created_at": "2026-03-01T10:30:00"
}
```

**Error - Already Favorited (409 Conflict):**
```json
{
  "error": {
    "code": "CONFLICT",
    "message": "Already favorited",
    "field": null,
    "constraint": null
  },
  "status_code": 409
}
```

---

#### List Favorites (200 OK)

```bash
curl http://localhost:8000/v1/users/student@example.com/favorites
```

**Response:**
```json
[
  {
    "favorite_id": 10,
    "user_id": "student@example.com",
    "bathroom_id": 1,
    "created_at": "2026-03-01T10:30:00"
  }
]
```

---

#### Remove Favorite (204 No Content)

```bash
curl -X DELETE http://localhost:8000/v1/users/student@example.com/favorites/1
```

**Response (204):** No body returned

---

## Webhook Integration

### How Webhooks Work

When a bathroom's average rating drops below 4.0/10, the system automatically sends a POST request to all registered webhook URLs with low-supply alerts.

### Webhook Payload Format

```json
{
  "bathroom_id": 1,
  "building": "Siebel",
  "floor": 2,
  "gender": "Unisex",
  "avg_rating": 3.5,
  "alert_type": "low_supply",
  "timestamp": "2026-03-01T10:30:45.123456"
}
```

### Register Your Webhook

```bash
curl -X POST http://localhost:8000/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/bathroom-alert",
    "event_type": "low_supply"
  }'
```

### Testing with webhook.site

1. Visit https://webhook.site
2. Copy your unique URL (e.g., `https://webhook.site/abc-def-ghi`)
3. Register it with the API:
   ```bash
   curl -X POST http://localhost:8000/v1/webhooks \
     -H "Content-Type: application/json" \
     -d '{"url":"https://webhook.site/abc-def-ghi","event_type":"low_supply"}'
   ```
4. Trigger a low-supply alert by submitting a low rating (< 4.0)
5. Refresh webhook.site and see the incoming POST

### Webhook Retry Logic

- **3 automatic retry attempts** if delivery fails
- **5-second delay** between retries
- **10-second timeout** per request
- Successful delivery: HTTP 200, 201, 202, or 204 response
- Failed delivery after 3 attempts: logged with `failure_count` incremented

### Webhook Headers

All webhook requests include:
```
Content-Type: application/json
X-Litterboxd-Signature: sha256=<signature>
```

---

## Testing Guide

### Health Check

```bash
curl http://localhost:8000/health
```

### Complete Test Workflow

```bash
# 1. Create a bathroom
RESPONSE=$(curl -s -X POST http://localhost:8000/v1/bathrooms \
  -H "Content-Type: application/json" \
  -d '{"building_name":"Siebel","floor_number":2,"bathroom_gender":"Unisex"}')

BATHROOM_ID=$(echo $RESPONSE | grep -o '"bathroom_id":[0-9]*' | cut -d: -f2)
echo "Created bathroom: $BATHROOM_ID"

# 2. Submit a review (triggers rating calculation)
curl -X POST "http://localhost:8000/v1/bathrooms/$BATHROOM_ID/reviews?user_id=test1@example.com" \
  -F "rating=8" \
  -F "comment=Great!"

# 3. Get AI summary
curl http://localhost:8000/v1/bathrooms/$BATHROOM_ID/vibe-check

# 4. Update stall status
curl -X POST "http://localhost:8000/v1/bathrooms/$BATHROOM_ID/stalls" \
  -H "Content-Type: application/json" \
  -d '{"stall_number":1,"is_occupied":false}'

# 5. Add to favorites
curl -X POST "http://localhost:8000/v1/users/test1@example.com/favorites" \
  -H "Content-Type: application/json" \
  -d "{\"bathroom_id\":$BATHROOM_ID}"

# 6. List favorites
curl "http://localhost:8000/v1/users/test1@example.com/favorites"
```

### Postman Collection

Import the following requests as a Postman collection:

**Environment Variable:**
```
{{base_url}} = http://localhost:8000
{{bathroom_id}} = 1
```

Then import these requests:
1. POST `/v1/bathrooms`
2. GET `/v1/bathrooms`
3. GET `/v1/bathrooms/{{bathroom_id}}`
4. POST `/v1/bathrooms/{{bathroom_id}}/reviews?user_id=test@test.edu`
5. GET `/v1/bathrooms/{{bathroom_id}}/vibe-check`
6. POST `/v1/bathrooms/{{bathroom_id}}/stalls`
7. POST `/v1/webhooks`
8. GET `/v1/webhooks`
9. POST `/v1/users/test@test.edu/favorites`
10. GET `/v1/users/test@test.edu/favorites`

---

## Status Codes Reference

| Code | Meaning | When Used | Example |
|------|---------|-----------|---------|
| **200** | OK | Successful GET/update | GET /bathrooms/1 |
| **201** | Created | Successful POST (new resource) | POST /bathrooms |
| **204** | No Content | Successful DELETE | DELETE /webhooks/1 |
| **400** | Bad Request | Invalid input validation | Invalid rating (>10) |
| **403** | Forbidden | Operation not allowed | Building not registered |
| **404** | Not Found | Resource doesn't exist | GET /bathrooms/9999 |
| **409** | Conflict | Duplicate entry | User already reviewed |
| **500** | Server Error | Unexpected error | Database connection failure |

---

## Best Practices for API Integration

1. **Always check status codes** - Handle 4xx and 5xx errors gracefully
2. **Use request IDs** - Save request IDs from error responses for debugging
3. **Implement retry logic** - For 5xx errors, retry with exponential backoff
4. **Validate input** - The API validates, but prevent invalid requests client-side
5. **Use webhooks** - Don't poll; register webhooks for event notifications
6. **Cache responses** - Cache bathroom data locally when possible
7. **Rate limit client-side** - Be respectful; don't hammer the API
8. **Log errors**  - Log all 4xx/5xx responses for debugging

---

## Common Issues & Solutions

### Issue: 422 Unprocessable Entity on /reviews

**Cause:** Reviews expect Form data, not JSON  
**Solution:** Use `-F` flag with curl:
```bash
curl -X POST "http://localhost:8000/v1/bathrooms/1/reviews?user_id=test@example.com" \
  -F "rating=8" \
  -F "comment=comment"
```

### Issue: 403 Forbidden on POST /bathrooms

**Cause:** Building name not in registered list (Siebel, Grainger, CIF)  
**Solution:** Use one of the registered building names or contact admin to register a new building

### Issue: 409 Conflict on POST /reviews

**Cause:** User already reviewed this bathroom  
**Solution:** Use PUT to update the existing review, or use a different user_id

### Issue: Webhook not being triggered

**Cause:** Average rating must be < 4.0 to trigger  
**Solution:** Submit reviews with ratings below 4, then check webhook.site for POST delivery

---

## Support & Debugging

### Interactive Documentation
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### View Server Logs
```bash
# Tail logs in real-time
tail -f api.log

# Search logs by request ID
grep "abc123-def456" api.log
```

### Check Database Connection
```bash
python init_db.py  # Re-run initialization to verify DB connection
```

---

## API Versioning

Current API version: **v1**

All endpoints use the `/v1/` prefix. Future versions will use `/v2/`, `/v3/`, etc., allowing backward compatibility.

---

**Ready to build?** Start with [README.md](./README.md) for setup, then come back here for detailed endpoint reference.
