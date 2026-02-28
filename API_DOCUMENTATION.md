# Litterboxd API Documentation

**Real-time bathroom cleanliness tracking and rating system**

## Overview

Litterboxd is an API service that allows students to track and rate bathroom facilities in real-time. The API enables users to:

- Review and rate bathrooms across registered buildings
- Get AI-powered summaries of bathroom conditions
- Track real-time stall occupancy
- Subscribe to favorite bathrooms for updates
- Register webhooks for low-supply alerts

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API uses simple `user_id` strings for basic user tracking. Future versions will implement JWT-based authentication.

User ID Format: `string` (e.g., `"netid@university.edu"`)

## Data Types

### Bathroom Rating Scale
All ratings are on a 1-10 scale:
- **1-3**: Poor condition
- **4-6**: Acceptable condition
- **7-9**: Good condition
- **10**: Excellent condition

### Low Supply Threshold
Bathrooms are flagged for low supply when average rating falls below `4.0/10`

## API Endpoints

### Bathrooms

#### Create Bathroom
```
POST /v1/bathrooms
```

**Description**: Add a new bathroom to the system (faculty only)

**Request Body**:
```json
{
  "building": "Siebel Center",
  "floor": 1,
  "gender": "Men's"
}
```

**Allowed Buildings**: `Siebel Center`, `ECEB`, `Grainger`

**Response** `201 Created`:
```json
{
  "id": "uuid-string",
  "message": "Bathroom indexed successfully."
}
```

---

#### List Bathrooms
```
GET /v1/bathrooms
```

**Description**: List all bathrooms, optionally filtered by building

**Query Parameters**:
- `building` (optional): Filter by building name

**Response** `200 OK`:
```json
[
  {
    "id": "uuid-string",
    "building": "Siebel Center",
    "floor": 1,
    "gender": "Men's",
    "avg_rating": 7.5,
    "is_low_supply":false,
    "stalls": {
      "1": false,
      "2": true,
      "3": false
    },
    "created_at": "2026-02-28T12:00:00",
    "reviews": []
  }
]
```

---

#### Get Bathroom by ID
```
GET /v1/bathrooms/{bathroom_id}
```

**Response** `200 OK`: Same as list response

---

### Reviews

#### Add Review
```
POST /v1/bathrooms/{bathroom_id}/reviews
```

**Description**: Submit a review for a bathroom

**Request Body**:
```json
{
  "user_id": "netid@university.edu",
  "cleanliness": 7,
  "ambience": 6,
  "sink_pressure": 8,
  "paper_towel_type": "Electric hand dryer",
  "toilet_paper_type": "Standard 1-ply",
  "baby_changing_station": true,
  "hygiene_products": false,
  "comment": "Generally clean, water pressure could be better"
}
```

**Response** `201 Created`:
```json
{
  "id": "uuid-string",
  "user_id": "netid@university.edu",
  "bathroom_id": "uuid-string",
  "cleanliness": 7,
  "ambience": 6,
  "sink_pressure": 8,
  "paper_towel_type": "Electric hand dryer",
  "toilet_paper_type": "Standard 1-ply",
  "baby_changing_station": true,
  "hygiene_products": false,
  "comment": "Generally clean, water pressure could be better",
  "created_at": "2026-02-28T12:00:00"
}
```

**Note**: Users can only have one review per bathroom. Use PUT to edit existing reviews.

---

#### Update Review
```
PUT /v1/bathrooms/{bathroom_id}/reviews/{review_id}
```

**Request Body**: Same as Add Review

**Response** `200 OK`: Same as Add Review response

---

### Vibe Check (AI Summary)

#### Get Vibe Check
```
GET /v1/bathrooms/{bathroom_id}/vibe-check
```

**Description**: Get AI-generated summary of bathroom reviews using Gemini API

**Response** `200 OK`:
```json
{
  "bathroom_id": "uuid-string",
  "vibe_check": "This bathroom is generally clean with good ambience, though the fountain pressure is a bit wimpy. Grab a paper towel and you'll be golden!"
}
```

---

### Stall Occupancy

#### Update Stall Status
```
POST /v1/bathrooms/{bathroom_id}/stalls
```

**Description**: Real-time stall occupancy data (from IoT sensors)

**Request Body**:
```json
{
  "bathroom_id": "uuid-string",
  "stall_id": 1,
  "is_occupied": true
}
```

**Response** `200 OK`:
```json
{
  "stall_id": 1,
  "is_occupied": true
}
```

---

### Webhooks

#### Register Webhook
```
POST /v1/webhooks
```

**Description**: Register a webhook endpoint to receive low-supply alerts

**Request Body**:
```json
{
  "url": "https://facilities.example.com/alerts/low-supply",
  "event_type": "low_supply"
}
```

**Response** `201 Created`:
```json
{
  "id": "uuid-string",
  "url": "https://facilities.example.com/alerts/low-supply",
  "event_type": "low_supply",
  "is_active": true,
  "created_at": "2026-02-28T12:00:00",
  "last_triggered_at": null,
  "failure_count": 0
}
```

---

#### List Webhooks
```
GET /v1/webhooks
```

**Query Parameters**:
- `event_type` (optional): Filter by event type (`low_supply`, etc.)

**Response** `200 OK`: Array of webhook objects

---

#### Delete Webhook
```
DELETE /v1/webhooks/{webhook_id}
```

**Response** `204 No Content`

---

### Favorites

#### Add to Favorites
```
POST /v1/users/{user_id}/favorites
```

**Request Body**:
```json
{
  "bathroom_id": "uuid-string"
}
```

**Response** `201 Created`:
```json
{
  "id": "uuid-string",
  "user_id": "netid@university.edu",
  "bathroom_id": "uuid-string",
  "created_at": "2026-02-28T12:00:00"
}
```

---

#### List User Favorites
```
GET /v1/users/{user_id}/favorites
```

**Response** `200 OK`: Array of favorite objects

---

#### Remove from Favorites
```
DELETE /v1/users/{user_id}/favorites/{bathroom_id}
```

**Response** `204 No Content`

---

### Health Check

#### Health Check
```
GET /health
```

**Response** `200 OK`:
```json
{
  "status": "ok"
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

| Status | Message | Cause |
|--------|---------|-------|
| 400 | Bathroom already exists | Duplicate building/floor/gender combination |
| 400 | User already reviewed bathroom | Attempt to create second review for same bathroom |
| 400 | Webhook URL already registered | Duplicate webhook URL |
| 403 | Building not registered by faculty | Trying to add bathroom to invalid building |
| 404 | Bathroom not found | Invalid bathroom ID |
| 404 | Review not found | Invalid review ID |
| 404 | Webhook not found | Invalid webhook ID |
| 500 | Internal server error | Database or processing error |

---

## Webhook Payload Format

When a bathroom's rating drops below 4.0/10, webhooks receive:

```json
{
  "bathroom_id": "uuid-string",
  "building": "Siebel Center",
  "floor": 1,
  "gender": "Men's",
  "avg_rating": 3.8,
  "alert_type": "low_supply",
  "timestamp": "2026-02-28T12:00:00"
}
```

---

## Rate Limiting

Currently, no rate limiting is enforced. Future versions will implement per-user rate limits.

---

## Database Schema

### Bathrooms Table
- `id` (UUID): Primary key
- `building` (String): Building name
- `floor` (Integer): Floor number
- `gender` (String): Bathroom gender designation
- `avg_rating` (Float): Average review rating
- `is_low_supply` (Boolean): Flagged for low supply
- `stalls` (JSON): Stall occupancy map
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

### Reviews Table
- `id` (UUID): Primary key
- `bathroom_id` (UUID): Foreign key to bathrooms
- `user_id` (String): User identifier
- `cleanliness` (Integer): 1-10 rating
- `ambience` (Integer): 1-10 rating
- `sink_pressure` (Integer): 1-10 rating
- `paper_towel_type` (String): Type description
- `toilet_paper_type` (String): Type description
- `baby_changing_station` (Boolean): Availability
- `hygiene_products` (Boolean): Availability
- `comment` (String): Text review
- `created_at` (DateTime): Submission timestamp

### Webhooks Table
- `id` (UUID): Primary key
- `url` (String): Webhook endpoint URL
- `event_type` (String): Type of event to trigger on
- `is_active` (Boolean): Whether webhook is active
- `created_at` (DateTime): Registration timestamp
- `last_triggered_at` (DateTime): Last notification time
- `failure_count` (Integer): Number of failed deliveries

### Favorites Table
- `id` (UUID): Primary key
- `user_id` (String): User identifier
- `bathroom_id` (UUID): Foreign key to bathrooms
- `created_at` (DateTime): Addition timestamp

---

## Technology Stack

- **Framework**: FastAPI (Python)
- **Database**: MySQL (DigitalOcean)
- **ORM**: SQLAlchemy with async support
- **AI/LLM**: Google Gemini 2.5 Flash
- **Async**: Python asyncio with aiohttp

---

## Getting Started

See [SETUP_GUIDE.md](./SETUP_GUIDE.md) for detailed setup instructions.
