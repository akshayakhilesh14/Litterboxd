# Litterboxd API - Complete Implementation Guide

**Production-Ready Campus Bathroom Review API with DigitalOcean MySQL**

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Setup](#environment-setup)
3. [Database Configuration](#database-configuration)
4. [Installation](#installation)
5. [Database Initialization](#database-initialization)
6. [Running the API](#running-the-api)
7. [API Endpoints](#api-endpoints)
8. [Testing the API](#testing-the-api)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

If you already have everything configured:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your .env file (copy from .env.example)
cp .env.example .env
# Then edit .env and add your GEMINI_API_KEY

# 3. Initialize the database
python init_db.py

# 4. Start the API
uvicorn main:app --reload
```

Then visit: **http://localhost:8000/docs** for the interactive API documentation.

---

## Environment Setup

### 1️⃣ Create a Python Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 2️⃣ Configure Your .env File

Copy the example and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
# Your Gemini API Key (free tier available)
# Get it here: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_api_key_here



**⚠️ IMPORTANT:** Never commit `.env` to git. It's already in `.gitignore`.

---

## Database Configuration

### DigitalOcean MySQL Details

**Connection String:**
```
```

**Manual Connection (for testing):**
```bash
mysql -u doadmin -pAVNS_vDsyhyKt0X96AeGBxtA \
  -h litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com \
  -P 25060 \
  -D defaultdb
```

### Database Schema

The app automatically creates these tables on initialization:

**bathrooms** - Bathroom locations and metadata
- `bathroom_id` (auto-increment primary key)
- `building_name` (Enum: Siebel, Grainger, CIF)
- `floor_number` (integer)
- `bathroom_gender` (Enum: Sombr, Gracie Abrams, Unisex)
- `ai_review` (AI-generated summary)
- `tp_supply` (toilet paper supply level)
- `hygiene_supply` (hygiene product supply level)
- `is_accessible` (wheelchair accessible)
- `created_at` (timestamp)

**reviews** - User ratings and comments
- `review_id` (auto-increment)
- `bathroom_id` (foreign key)
- `user_id` (student email)
- `rating` (1-10 scale)
- `comment` (optional text)
- `created_at` (timestamp)

**stalls** - Real-time occupancy (IoT integration)
- `stall_number` (auto-increment)
- `bathroom_id` (foreign key)
- `is_occupied` (boolean)
- `last_updated` (timestamp)

**webhooks** - Facility coordinator notifications
- `webhook_id` (auto-increment)
- `url` (webhook endpoint)
- `event_type` (low_supply)
- `is_active` (boolean)
- `created_at`, `last_triggered_at`, `failure_count`

**favorites** - User bookmarks
- `favorite_id` (auto-increment)
- `user_id` (student email)
- `bathroom_id` (foreign key)
- `created_at` (timestamp)

---

## Installation

### 1️⃣ Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Verify Imports Work

```bash
python -c "import fastapi, sqlalchemy, google.genai; print('✅ All dependencies installed')"
```

### 3️⃣ Test DigitalOcean Connection (Optional)

```bash
python -c "
import asyncio
from database import async_session

async def test():
    async with async_session() as session:
        result = await session.execute('SELECT 1')
        print('✅ Database connected!')

asyncio.run(test())
"
```

---

## Database Initialization

### 🔧 Initialize Tables

```bash
python init_db.py
```

**Expected output:**
```
🔄 Initializing Litterboxd Database...
Database: defaultdb
Host: litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com
✅ Database tables created successfully!
✅ Database connection test passed!

📊 Tables created:
  - bathrooms (stores bathroom metadata, ratings)
  - reviews (stores student reviews and ratings)
  - stalls (stores real-time stall occupancy)
  - webhooks (stores facility coordinator webhooks)
  - favorites (stores user favorite bathrooms)

✨ Database initialization complete!

You can now start the API with:
  uvicorn main:app --reload
```

### 💾 Verify Tables Were Created

```bash
mysql -u doadmin -pAVNS_vDsyhyKt0X96AeGBxtA \
  -h litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com \
  -P 25060 \
  -D defaultdb \
  -e "SHOW TABLES;"
```

Should output:
```
bathrooms
favorites
reviews
stalls
webhooks
```

---

## Running the API

### Development Mode (with auto-reload)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode (with Gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Docker Mode (Optional)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run:**
```bash
docker build -t litterboxd .
docker run -p 8000:8000 --env-file .env litterboxd
```

---

## API Endpoints

### 🏢 Bathrooms

**Create a bathroom** (faculty only)
```bash
curl -X POST http://localhost:8000/v1/bathrooms \
  -H "Content-Type: application/json" \
  -d '{
    "building_name": "Siebel",
    "floor_number": 2,
    "bathroom_gender": "Sombr"
  }'
```

**List all bathrooms**
```bash
curl http://localhost:8000/v1/bathrooms
```

**List bathrooms by building**
```bash
curl "http://localhost:8000/v1/bathrooms?building=Siebel"
```

**Get specific bathroom**
```bash
curl http://localhost:8000/v1/bathrooms/1
```

### ⭐ Reviews

**Add a review**
```bash
curl -X POST "http://localhost:8000/v1/bathrooms/1/reviews?user_id=student@university.edu" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 7,
    "comment": "Clean, but could use more soap dispensers"
  }'
```

**Update your review**
```bash
curl -X PUT "http://localhost:8000/v1/bathrooms/1/reviews/1" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 8,
    "comment": "Updated comment"
  }'
```

### 🤖 AI Vibe Check

**Get AI summary**
```bash
curl http://localhost:8000/v1/bathrooms/1/vibe-check
```

### 🚽 Stall Occupancy

**Update stall status** (from IoT sensor)
```bash
curl -X POST "http://localhost:8000/v1/bathrooms/1/stalls" \
  -H "Content-Type: application/json" \
  -d '{
    "stall_number": 1,
    "is_occupied": true
  }'
```

**Get all stalls**
```bash
curl http://localhost:8000/v1/bathrooms/1/stalls
```

### 🔔 Webhooks

**Register a webhook**
```bash
curl -X POST http://localhost:8000/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://facilities.example.com/alerts",
    "event_type": "low_supply"
  }'
```

**List webhooks**
```bash
curl http://localhost:8000/v1/webhooks
```

**Delete webhook**
```bash
curl -X DELETE http://localhost:8000/v1/webhooks/1
```

### ⭐ Favorites

**Add to favorites**
```bash
curl -X POST "http://localhost:8000/v1/users/student@university.edu/favorites" \
  -H "Content-Type: application/json" \
  -d '{"bathroom_id": 1}'
```

**Get user favorites**
```bash
curl "http://localhost:8000/v1/users/student@university.edu/favorites"
```

**Remove from favorites**
```bash
curl -X DELETE "http://localhost:8000/v1/users/student@university.edu/favorites/1"
```

### 🏥 Health Check

```bash
curl http://localhost:8000/health
```

---

## Testing the API

### Interactive API Documentation

**Swagger UI:** http://localhost:8000/docs
**ReDoc:** http://localhost:8000/redoc

### Test Flow

1. **Create a bathroom:**
   ```bash
   POST /v1/bathrooms
   ```

2. **Add a review:**
   ```bash
   POST /v1/bathrooms/{bathroom_id}/reviews?user_id=student@email.com
   ```

3. **Get AI vibe check:**
   ```bash
   GET /v1/bathrooms/{bathroom_id}/vibe-check
   ```

4. **Update stall status:**
   ```bash
   POST /v1/bathrooms/{bathroom_id}/stalls
   ```

5. **Add to favorites:**
   ```bash
   POST /v1/users/{user_id}/favorites
   ```

---

## Troubleshooting

### ❌ "Connection refused" Error

**Problem:** `Can't connect to DigitalOcean database`

**Solutions:**
1. Check if database credentials are correct in `.env`
2. Ensure your IP is whitelisted in DigitalOcean
3. Test connection manually:
   ```bash
   mysql -u doadmin -pAVNS_vDsyhyKt0X96AeGBxtA \
     -h litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com \
     -P 25060
   ```

### ❌ "SSL error" When Connecting

**Problem:** SSL certificate validation fails

**Solution:** The code already handles this with `ssl_verify_cert: False` in `database.py`. If issues persist, check your MySQL version compatibility.

### ❌ "Table already exists" Error

**Problem:** Running `init_db.py` twice tries to recreate tables

**Solution:** This is handled - the script checks if tables exist. If you want to reset, drop tables manually:
```bash
mysql -u doadmin ... -D defaultdb -e "DROP TABLE IF EXISTS favorites, webhooks, stalls, reviews, bathrooms;"
```

### ❌ "ImportError: No module named 'google.genai'"

**Problem:** Gemini package not installed

**Solution:**
```bash
pip install google-genai==0.3.0
```

### ❌ "No reviews yet" on Vibe Check

**Problem:** Vibe check returns "No reviews yet"

**Solution:** This is expected. Add at least one review before calling vibe-check.

### ✅ All Tests Pass?

Great! Your Litterboxd API is ready for:
- ✅ Real-time bathroom reviews
- ✅ AI-powered summaries
- ✅ Webhook notifications to facilities
- ✅ IoT sensor integration
- ✅ User favorites tracking

---

## Key Features Implemented

✅ **Complete REST API** with FastAPI  
✅ **Async SQLAlchemy** for efficient database operations  
✅ **DigitalOcean MySQL integration** with SSL  
✅ **Google Gemini AI** for vibe checks  
✅ **Webhook system** for low-supply alerts  
✅ **Real-time stall occupancy** tracking  
✅ **User favorites** management  
✅ **Automatic review averaging**  
✅ **Error handling & validation**  
✅ **Interactive API docs** (Swagger UI)  

---

## Next Steps

### 🎨 Frontend Development
- React/Vue component for bathroom reviews
- Real-time stall status display
- Favorites page

### 🔧 Hardware Integration
- ESP32/Raspberry Pi IoT sensors
- Real-time stall occupancy detection
- Campus-wide deployment

### 📊 Analytics
- Dashboard for facility coordinators
- Review trends over time
- Peak usage hours analysis

### 🚀 Deployment
- Deploy to Heroku, AWS, or DigitalOcean App Platform
- Set up CI/CD with GitHub Actions
- Configure production logging

---

**Questions?** Check [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed endpoint specs.

**Made for HackIllinois 2026** 🎓
