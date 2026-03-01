# Litterboxd API

**Real-time campus bathroom review and rating system with AI-powered summaries**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.134+-green.svg)](https://fastapi.tiangolo.com)

## Overview

Litterboxd is a production-ready REST API built for HackIllinois 2026 that allows students to rate and track bathroom conditions in real-time across campus buildings. The system features AI-powered summaries via Google Gemini 2.5 Flash, webhook notifications for facilities coordinators, real-time stall occupancy tracking (IoT support), user favorites, and comprehensive error handling with request tracking.

**Track:** Stripe's Best Web API  
**Status:** Production-ready, fully tested

## ⭐ Key Features

### 📊 Comprehensive Rating System
- 1-10 scale ratings for bathroom conditions
- Automatic average rating computation
- Real-time updates across all users
- Supply level tracking (paper, hygiene products)
- Accessibility and cleanliness metrics

### 🤖 AI-Powered Summaries
Google Gemini 2.5 Flash generates witty, honest 2-sentence bathroom summaries:
> "This bathroom is surprisingly clean for a basement level. The water pressure will blow your face off (in a good way)."

### 🔔 Smart Webhook Alert System
- Automatic notifications when bathroom ratings drop below 4.0/10
- Includes location, rating, and timestamp
- Retry logic (3 attempts, 5-second delay between retries)
- Persistent webhook endpoint registration
- Request ID tracking for debugging
- Detailed logging of all delivery attempts

### ⭐ User Favorites
- Bookmark favorite bathrooms for quick access
- Track ratings and availability
- Personalized bathroom feed (future feature)

### 🚽 Real-Time Stall Occupancy
Perfect for IoT hardware integration:
- ESP32/Raspberry Pi sensor support
- Real-time stall status updates
- Campus-wide availability view

### 🛡️ Production-Grade Error Handling
- Standardized error schema across all endpoints
- 6 error types (validation, not found, conflict, forbidden, unauthorized, server error)
- Field-level validation feedback
- Consistent HTTP status codes (200, 201, 204, 400, 403, 404, 409, 500)
- Request ID tracking for debugging
- Comprehensive logging middleware

### 🔐 Data Integrity
- One review per user per bathroom (unique constraint)
- Faculty-only bathroom registration
- Cascade deletes for data consistency
- Async database operations for high concurrency

## 🚀 Quick Start

```bash
# 1. Clone and setup
cd /Users/kush/Downloads/Litterboxd
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your Gemini API key

# 4. Initialize database
python init_db.py

# 5. Start the server
uvicorn main:app --reload

# 6. Visit http://localhost:8000/docs for interactive API docs!
```

## 📚 API Endpoints Summary

### Bathrooms
- `POST /v1/bathrooms` - Create bathroom
- `GET /v1/bathrooms` - List all bathrooms
- `GET /v1/bathrooms/{id}` - Get specific bathroom

### Reviews
- `POST /v1/bathrooms/{id}/reviews` - Add review
- `PUT /v1/bathrooms/{id}/reviews/{id}` - Update review
- `GET /v1/bathrooms/{id}/vibe-check` - AI summary

### Webhooks
- `POST /v1/webhooks` - Register webhook
- `GET /v1/webhooks` - List webhooks
- `DELETE /v1/webhooks/{id}` - Delete webhook

### Favorites
- `POST /v1/users/{id}/favorites` - Add favorite
- `GET /v1/users/{id}/favorites` - List favorites
- `DELETE /v1/users/{id}/favorites/{id}` - Remove favorite

### Real-time
- `POST /v1/bathrooms/{id}/stalls` - Update stall status
- `GET /health` - Health check

**Complete documentation:** See [API_GUIDE.md](./API_GUIDE.md)

## 🏗️ Architecture

```
FastAPI Application
├── Endpoints (main.py)
├── SQLAlchemy ORM (models.py)
├── Async MySQL (database.py)
├── Gemini Integration (ai_service.py)
└── Webhook System (webhooks.py)
     ↓
DigitalOcean MySQL Database
├── bathrooms table
├── reviews table
├── webhooks table
└── favorites table
```

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI 0.104 |
| **Server** | Uvicorn + Gunicorn |
| **Database** | MySQL (DigitalOcean) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **AI/LLM** | Google Gemini 2.5 Flash |
| **Async** | Python asyncio |
| **Data Validation** | Pydantic v2 |

## 📋 Documentation

### For API Users & Developers
**📖 [API_GUIDE.md](./API_GUIDE.md)** - Complete developer guide
- Setup & configuration
- All 14 endpoints with curl examples
- Error handling details
- Webhook integration guide
- HTTP status codes reference
- Postman testing guide

### Interactive Documentation
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🧪 Testing Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Create Bathroom
```bash
curl -X POST http://localhost:8000/v1/bathrooms \
  -H "Content-Type: application/json" \
  -d '{
    "building": "Siebel Center",
    "floor": 1,
    "gender": "Men'"'"'s"
  }'
```

### Submit Review
```bash
curl -X POST http://localhost:8000/v1/bathrooms/{bathroom_id}/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "student@university.edu",
    "cleanliness": 8,
    "ambience": 7,
    "sink_pressure": 6,
    "paper_towel_type": "Electric",
    "toilet_paper_type": "Standard",
    "baby_changing_station": true,
    "hygiene_products": false,
    "comment": "Clean and spacious!"
  }'
```

### Get AI Vibe Check
```bash
curl http://localhost:8000/v1/bathrooms/{bathroom_id}/vibe-check
```



## 📄 License

MIT License - See LICENSE file for details

---

**Ready to test?** Run `uvicorn main:app --reload` and visit http://localhost:8000/docs

**Questions?** Check the documentation or review the source code - it's well-commented!