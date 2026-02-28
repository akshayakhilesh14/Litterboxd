# Litterboxd API - Complete Usage Guide with cURL Examples

## Overview

The Litterboxd API is a RESTful API for managing campus bathroom reviews and ratings. It supports HTTP operations (GET, POST, PUT, DELETE) and returns JSON responses with comprehensive error handling.

**Base URL:** `http://localhost:8000`

---

## Quick Test: Health Check

Verify the API is running:

```bash
curl -X GET http://localhost:8000/health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "timestamp": "2026-02-28T10:30:45.123456",
  "message": "Litterboxd API is running"
}
```

---

## API Endpoints Summary

| Method | Endpoint | Status Codes | Description |
|--------|----------|--------------|-------------|
| POST | `/v1/bathrooms` | 201, 400, 403, 409, 500 | Create bathroom |
| GET | `/v1/bathrooms` | 200, 400, 500 | List bathrooms |
| GET | `/v1/bathrooms/{id}` | 200, 404, 500 | Get bathroom details |
| POST | `/v1/bathrooms/{id}/reviews` | 201, 400, 404, 409, 500 | Add review |
| GET | `/v1/bathrooms/{id}/vibe-check` | 200, 404, 500 | Get AI summary |
| POST | `/v1/bathrooms/{id}/stalls` | 200, 400, 404, 500 | Update stall status |
| GET | `/v1/bathrooms/{id}/stalls` | 200, 404, 500 | Get stall data |
| PUT | `/v1/bathrooms/{id}/reviews/{id}` | 200, 400, 404, 500 | Update review |
| POST | `/v1/webhooks` | 201, 400, 409, 500 | Register webhook |
| GET | `/v1/webhooks` | 200, 400, 500 | List webhooks |
| DELETE | `/v1/webhooks/{id}` | 204, 404, 500 | Delete webhook |
| POST | `/v1/users/{id}/favorites` | 201, 404, 409, 500 | Add favorite |
| GET | `/v1/users/{id}/favorites` | 200, 500 | List favorites |
| DELETE | `/v1/users/{id}/favorites/{id}` | 204, 404, 500 | Remove favorite |

---

## 1. Bathrooms Endpoints

### Create a Bathroom (201 Created)

Faculty-only endpoint to register a new bathroom.

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

**Response (201 Created):**
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
    "building_name": "NonExistent",
    "floor_number": 2,
    "bathroom_gender": "Unisex"
  }'
```

**Response (403):**
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Building NonExistent not registered by faculty. Only Siebel, Grainger, CIF are allowed.",
    "field": null,
    "constraint": null
  },
  "status_code": 403
}
```

**Error - Bathroom Already Exists (409 Conflict):**
```bash
curl -X POST http://localhost:8000/v1/bathrooms \
  -H "Content-Type: application/json" \
  -d '{
    "building_name": "Siebel",
    "floor_number": 2,
    "bathroom_gender": "Unisex"
  }'
```

**Response (409):**
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

---

### List All Bathrooms (200 OK)

```bash
curl -X GET http://localhost:8000/v1/bathrooms
```

**Response (200 OK):**
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
    "last_cleaned": null,
    "is_accessible": true,
    "created_at": "2026-02-28T10:00:00",
    "avg_rating": 0.0,
    "is_low_supply": false,
    "reviews": [],
    "stalls": []
  }
]
```

### Filter by Building

```bash
curl -X GET "http://localhost:8000/v1/bathrooms?building=Grainger"
```

**Error - Invalid Building (400 Bad Request):**
```bash
curl -X GET "http://localhost:8000/v1/bathrooms?building=InvalidBuilding"
```

**Response (400):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid building: InvalidBuilding",
    "field": "building",
    "constraint": null
  },
  "status_code": 400
}
```

---

### Get Bathroom Details (200 OK)

```bash
curl -X GET http://localhost:8000/v1/bathrooms/1
```

**Response (200 OK):**
```json
{
  "bathroom_id": 1,
  "building_name": "Siebel",
  "floor_number": 2,
  "bathroom_gender": "Unisex",
  "ai_review": null,
  "tp_supply": "High",
  "hygiene_supply": "High",
  "is_accessible": true,
  "created_at": "2026-02-28T10:00:00",
  "avg_rating": 0.0,
  "is_low_supply": false,
  "reviews": [],
  "stalls": []
}
```

**Error - Bathroom Not Found (404):**
```bash
curl -X GET http://localhost:8000/v1/bathrooms/9999
```

**Response (404 Not Found):**
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

## 2. Reviews Endpoints

### Submit a Review (201 Created)

Rating must be between 1 and 10.

```bash
curl -X POST http://localhost:8000/v1/bathrooms/1/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 8,
    "comment": "Clean restroom with good water pressure!"
  }' \
  '?user_id=student@university.edu'
```

**Response (201 Created):**
```json
{
  "review_id": 42,
  "bathroom_id": 1,
  "rating": 8,
  "comment": "Clean restroom with good water pressure!",
  "created_at": "2026-02-28T10:15:30"
}
```

**Error - Invalid Rating (400 Bad Request):**
```bash
curl -X POST http://localhost:8000/v1/bathrooms/1/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 15,
    "comment": "Out of range!"
  }' \
  '?user_id=student@university.edu'
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

**Error - User Already Reviewed (409 Conflict):**
```bash
curl -X POST http://localhost:8000/v1/bathrooms/1/reviews \
  -H "Content-Type: application/json" \
  -d '{"rating": 7}' \
  '?user_id=student@university.edu'
```

**Response (409):**
```json
{
  "error": {
    "code": "CONFLICT",
    "message": "User student@university.edu has already reviewed this bathroom. Use PUT to update your review.",
    "field": null,
    "constraint": null
  },
  "status_code": 409
}
```

---

### Get AI Vibe Check (200 OK)

Generate AI-powered summary of bathroom based on reviews.

```bash
curl -X GET http://localhost:8000/v1/bathrooms/1/vibe-check
```

**Response (200 OK):**
```json
{
  "bathroom_id": 1,
  "vibe": "This bathroom is surprisingly clean for a basement level. The water pressure will blow your face off (in a good way)."
}
```

---

## 3. Real-Time Stalls Endpoints

### Update Stall Occupancy (200 OK)

For IoT sensor integration.

```bash
curl -X POST http://localhost:8000/v1/bathrooms/1/stalls \
  -H "Content-Type: application/json" \
  -d '{
    "stall_number": 1,
    "is_occupied": true
  }'
```

**Response (200 OK):**
```json
{
  "stall_number": 1,
  "bathroom_id": 1,
  "is_occupied": true,
  "last_updated": "2026-02-28T10:20:15"
}
```

**Error - Invalid Stall Number (400 Bad Request):**
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

### Get Stall Status (200 OK)

```bash
curl -X GET http://localhost:8000/v1/bathrooms/1/stalls
```

**Response (200 OK):**
```json
[
  {
    "stall_number": 1,
    "bathroom_id": 1,
    "is_occupied": true,
    "last_updated": "2026-02-28T10:20:15"
  },
  {
    "stall_number": 2,
    "bathroom_id": 1,
    "is_occupied": false,
    "last_updated": "2026-02-28T10:18:00"
  }
]
```

---

## 4. Webhooks Endpoints

### Register Webhook (201 Created)

Receive notifications when bathroom rating drops below 4.0.

```bash
curl -X POST http://localhost:8000/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://facilities.university.edu/alerts",
    "event_type": "low_supply"
  }'
```

**Response (201 Created):**
```json
{
  "webhook_id": 5,
  "url": "https://facilities.university.edu/alerts",
  "event_type": "low_supply",
  "is_active": true,
  "created_at": "2026-02-28T10:25:00",
  "last_triggered_at": null,
  "failure_count": 0
}
```

**Error - Invalid URL (400 Bad Request):**
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

**Error - URL Already Registered (409 Conflict):**
```bash
curl -X POST http://localhost:8000/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://facilities.university.edu/alerts",
    "event_type": "low_supply"
  }'
```

**Response (409):**
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

### List Webhooks (200 OK)

```bash
curl -X GET http://localhost:8000/v1/webhooks
```

**Response (200 OK):**
```json
[
  {
    "webhook_id": 5,
    "url": "https://facilities.university.edu/alerts",
    "event_type": "low_supply",
    "is_active": true,
    "created_at": "2026-02-28T10:25:00",
    "last_triggered_at": null,
    "failure_count": 0
  }
]
```

---

### Delete Webhook (204 No Content)

```bash
curl -X DELETE http://localhost:8000/v1/webhooks/5
```

**Response (204 No Content):**
```
[No body returned]
```

**Error - Webhook Not Found (404):**
```bash
curl -X DELETE http://localhost:8000/v1/webhooks/9999
```

**Response (404):**
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

## 5. Favorites Endpoints

### Add Favorite (201 Created)

```bash
curl -X POST http://localhost:8000/v1/users/student@university.edu/favorites \
  -H "Content-Type: application/json" \
  -d '{
    "bathroom_id": 1
  }'
```

**Response (201 Created):**
```json
{
  "favorite_id": 10,
  "user_id": "student@university.edu",
  "bathroom_id": 1,
  "created_at": "2026-02-28T10:30:00"
}
```

**Error - Bathroom Not Found (404):**
```bash
curl -X POST http://localhost:8000/v1/users/student@university.edu/favorites \
  -H "Content-Type: application/json" \
  -d '{"bathroom_id": 9999}'
```

**Response (404):**
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

**Error - Already Favorited (409 Conflict):**
```bash
curl -X POST http://localhost:8000/v1/users/student@university.edu/favorites \
  -H "Content-Type: application/json" \
  -d '{"bathroom_id": 1}'
```

**Response (409):**
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

### List User Favorites (200 OK)

```bash
curl -X GET http://localhost:8000/v1/users/student@university.edu/favorites
```

**Response (200 OK):**
```json
[
  {
    "favorite_id": 10,
    "user_id": "student@university.edu",
    "bathroom_id": 1,
    "created_at": "2026-02-28T10:30:00"
  }
]
```

---

### Remove Favorite (204 No Content)

```bash
curl -X DELETE http://localhost:8000/v1/users/student@university.edu/favorites/1
```

**Response (204 No Content):**
```
[No body returned]
```

---

## HTTP Status Codes Reference

| Code | Meaning | Common Causes |
|------|---------|---------------|
| **200** | OK | Request succeeded |
| **201** | Created | Resource created successfully |
| **204** | No Content | Deletion successful |
| **400** | Bad Request | Invalid input, validation error |
| **403** | Forbidden | Building not registered |
| **404** | Not Found | Resource doesn't exist |
| **409** | Conflict | Duplicate entry, already exists |
| **500** | Internal Server Error | Server-side error |

---

## Error Response Format

All errors follow this standardized format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "field": "field_name (if applicable)",
    "constraint": "constraint_type (if applicable)"
  },
  "status_code": 400,
  "request_id": "uuid (optional)",
  "timestamp": "ISO timestamp (optional)"
}
```

---

## Testing with Postman

Import the following as a Postman collection:

1. **Create Bathroom:** POST `http://localhost:8000/v1/bathrooms`
2. **Add Review:** POST `http://localhost:8000/v1/bathrooms/1/reviews?user_id=test@test.edu`
3. **Get AI Summary:** GET `http://localhost:8000/v1/bathrooms/1/vibe-check`
4. **Update Stall:** POST `http://localhost:8000/v1/bathrooms/1/stalls`
5. **Register Webhook:** POST `http://localhost:8000/v1/webhooks`
6. **Add Favorite:** POST `http://localhost:8000/v1/users/test@test.edu/favorites`

---

## Tips for Production Use

1. **Always validate input** - The API validates ratings (1-10), floor numbers (≥0), URLs (http/https)
2. **Handle errors gracefully** - Check status codes and error details
3. **Use webhooks for notifications** - Get notified when bathrooms drop below 4.0 rating
4. **Request IDs** - Logged for debugging, useful for support
5. **Rate limiting** - Consider implementing client-side rate limiting

---

## Support

For issues, check the logs at `http://localhost:8000/docs` for interactive API documentation.
