# Litterboxd API - Complete Setup Guide

## Overview
Litterboxd is a real-time bathroom review and rating system built for HackIllinois 2026. This is the complete implementation using DigitalOcean MySQL database with AI-powered summaries, webhook notifications, and real-time stall tracking.

## Prerequisites

- Python 3.10+
- pip package manager
- DigitalOcean MySQL credentials (provided below)
- Gemini API Key (free tier available at https://makersuite.google.com)
- MySQL CLI tools (optional, for direct database access)

## Database Connection Details

**Host:** `litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com`  
**Port:** `25060`  
**User:** `doadmin`  
**Database:** `defaultdb`  

**MySQL CLI Access:**
```bash
mysql -u doadmin -pAVNS_vDsyhyKt0X96AeGBxtA \
  -h litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com \
  -P 25060 -D defaultdb
```

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt** should contain:
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
aiomysql==0.2.0
aiofiles==23.2.1
python-dotenv==1.0.0
google-genai==0.3.0
httpx==0.25.0
pydantic==2.5.0
```

### Step 2: Configure Environment Variables

Create a `.env` file in the root directory:

```
# .env file
GEMINI_API_KEY=your_gemini_api_key_here

# DigitalOcean MySQL Configuration
MYSQL_USER=doadmin
MYSQL_PORT=25060
MYSQL_DB=defaultdb
```

⚠️ **Security Note**: Add `.env` to `.gitignore`:
```
.env
.env.local
venv/
__pycache__/
*.pyc
.DS_Store
```

### Step 3: Initialize Database

Run the initialization script to create all database tables:

```bash
python init_db.py
```

Expected output:
```
🔄 Initializing Litterboxd Database...
Database: defaultdb
Host: litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com
✅ Database tables created successfully!
✅ Database connection test passed!

📊 Tables created:
  - bathrooms (stores bathroom metadata)
  - reviews (stores student reviews)
  - webhooks (stores webhook subscriptions)
  - favorites (stores user favorite bathrooms)

✨ Database initialization complete!

You can now start the API with:
  uvicorn main:app --reload
```

### Step 4: Start the API Server

Development mode (with auto-reload):
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Production mode:
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

The API will be available at `http://localhost:8000`

## Interactive API Documentation

FastAPI automatically generates interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These allow you to test endpoints directly in the browser.

## Database Schema

### Bathrooms Table
```sql
CREATE TABLE bathrooms (
  id VARCHAR(36) PRIMARY KEY,
  building VARCHAR(100) NOT NULL,
  floor INT NOT NULL,
  gender VARCHAR(50) NOT NULL,
  avg_rating FLOAT DEFAULT 0.0,
  is_low_supply BOOLEAN DEFAULT FALSE,
  stalls JSON DEFAULT '{}',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_bathroom_location (building, floor, gender),
  INDEX idx_building (building),
  INDEX idx_low_supply (is_low_supply)
);
```

### Reviews Table
```sql
CREATE TABLE reviews (
  id VARCHAR(36) PRIMARY KEY,
  bathroom_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(100) NOT NULL,
  cleanliness INT NOT NULL,
  ambience INT NOT NULL,
  sink_pressure INT NOT NULL,
  paper_towel_type VARCHAR(100),
  toilet_paper_type VARCHAR(100),
  baby_changing_station BOOLEAN DEFAULT FALSE,
  hygiene_products BOOLEAN DEFAULT FALSE,
  comment VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_bathroom_review (bathroom_id, user_id),
  FOREIGN KEY (bathroom_id) REFERENCES bathrooms(id) ON DELETE CASCADE,
  INDEX idx_bathroom_id (bathroom_id),
  INDEX idx_user_id (user_id),
  INDEX idx_created_at (created_at)
);
```

### Webhooks Table
```sql
CREATE TABLE webhooks (
  id VARCHAR(36) PRIMARY KEY,
  url VARCHAR(2000) NOT NULL UNIQUE,
  event_type VARCHAR(50) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_triggered_at DATETIME,
  failure_count INT DEFAULT 0,
  INDEX idx_event_type (event_type),
  INDEX idx_is_active (is_active)
);
```

### Favorites Table
```sql
CREATE TABLE favorites (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  bathroom_id VARCHAR(36) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_bathroom_favorite (user_id, bathroom_id),
  FOREIGN KEY (bathroom_id) REFERENCES bathrooms(id) ON DELETE CASCADE,
  INDEX idx_user_id (user_id),
  INDEX idx_bathroom_id (bathroom_id)
);
```

## Quick Start Testing

### Test Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok"}
```

### Create a Bathroom
```bash
curl -X POST http://localhost:8000/v1/bathrooms \
  -H "Content-Type: application/json" \
  -d '{
    "building": "Siebel Center",
    "floor": 1,
    "gender": "Men'"'"'s"
  }'
```

### Submit a Review
```bash
curl -X POST http://localhost:8000/v1/bathrooms/{bathroom_id}/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "student@university.edu",
    "cleanliness": 8,
    "ambience": 7,
    "sink_pressure": 6,
    "paper_towel_type": "Electric hand dryer",
    "toilet_paper_type": "Standard 1-ply",
    "baby_changing_station": false,
    "hygiene_products": true,
    "comment": "Pretty clean!"
  }'
```

### Get AI Vibe Check
```bash
curl http://localhost:8000/v1/bathrooms/{bathroom_id}/vibe-check
```

### Register Webhook
```bash
curl -X POST http://localhost:8000/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/alerts/low-supply",
    "event_type": "low_supply"
  }'
```

### Add to Favorites
```bash
curl -X POST http://localhost:8000/v1/users/student@university.edu/favorites \
  -H "Content-Type: application/json" \
  -d '{"bathroom_id": "{bathroom_id}"}'
```

## Key Features

✅ **Five Rating Metrics** - Cleanliness, ambience, sink pressure, paper towel type, toilet paper type  
✅ **Facility Tracking** - Baby changing stations and hygiene products availability  
✅ **Automatic Averages** - Rating calculations happen automatically  
✅ **Low Supply Alert System** - Triggers webhook notifications when rating < 4.0  
✅ **AI-Powered Summaries** - Gemini generates witty 2-sentence vibe checks  
✅ **Real-time Stall Occupancy** - IoT sensor integration for stall status  
✅ **User Favorites** - Bookmark and track favorite bathrooms  
✅ **Webhook Notifications** - Notify facilities of low-supply situations  
✅ **Duplicate Review Protection** - One review per user per bathroom  
✅ **Data Relationships** - Proper foreign keys and cascading deletes  
✅ **Async/Await** - Full non-blocking database operations  
✅ **Automatic Retry Logic** - Webhook delivery with exponential backoff  

## Registered Buildings

Valid buildings for bathroom registration:
- `Siebel Center`
- `ECEB`
- `Grainger`

Attempting to create a bathroom in an unregistered building returns a 403 error.

## Project Structure

```
Litterboxd/
├── main.py                    # FastAPI app & all endpoints
├── models.py                  # SQLAlchemy ORM & Pydantic models
├── database.py                # Async MySQL connection setup
├── ai_service.py              # Gemini API integration
├── webhooks.py                # Webhook notification system
├── init_db.py                 # Database initialization
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create this)
├── .gitignore                 # Git ignore rules
├── API_DOCUMENTATION.md       # Complete API reference
├── SETUP_GUIDE.md             # This file
└── README.md                  # Project overview
```

## API Endpoint Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/bathrooms` | Create bedroom |
| `GET` | `/v1/bathrooms` | List all bathrooms |
| `GET` | `/v1/bathrooms/{id}` | Get specific bathroom |
| `POST` | `/v1/bathrooms/{id}/reviews` | Add review |
| `PUT` | `/v1/bathrooms/{id}/reviews/{id}` | Update review |
| `POST` | `/v1/bathrooms/{id}/stalls` | Update stall status |
| `GET` | `/v1/bathrooms/{id}/vibe-check` | Get AI summary |
| `POST` | `/v1/webhooks` | Register webhook |
| `GET` | `/v1/webhooks` | List webhooks |
| `DELETE` | `/v1/webhooks/{id}` | Delete webhook |
| `POST` | `/v1/users/{id}/favorites` | Add favorite |
| `GET` | `/v1/users/{id}/favorites` | List favorites |
| `DELETE` | `/v1/users/{id}/favorites/{id}` | Remove favorite |
| `GET` | `/health` | Health check |

## Troubleshooting

### MySQL Connection Error
```
Error: Can't connect to MySQL server
```
**Solution**: Verify credentials in `.env` and test connection:
```bash
mysql -u doadmin -pAVNS_vDsyhyKt0X96AeGBxtA \
  -h litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com \
  -P 25060 -D defaultdb -e "SELECT 1;"
```

### Gemini API Error
```
Error: Invalid API key or rate limit exceeded
```
**Solution**:
1. Verify API key in `.env` is correct
2. Check you're using the free tier correctly
3. Ensure API is enabled in Google Cloud Console

### Import Error on Startup
```
ModuleNotFoundError: No module named 'google'
```
**Solution**: Reinstall dependencies:
```bash
pip install --upgrade -r requirements.txt
```

### Port Already in Use
```
OSError: [Errno 48] Address already in use
```
**Solution**: Use a different port:
```bash
uvicorn main:app --reload --port 8001
```

## Database Management

### View all tables
```bash
mysql -u doadmin -pAVNS_vDsyhyKt0X96AeGBxtA \
  -h litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com \
  -P 25060 -D defaultdb -e "SHOW TABLES;"
```

### Export data
```bash
mysqldump -u doadmin -pAVNS_vDsyhyKt0X96AeGBxtA \
  -h litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com \
  -P 25060 defaultdb > backup.sql
```

### Reset database (⚠️ Deletes all data)
```bash
python init_db.py  # Re-run initialization
```

## Performance Notes

- All database operations use async/await for high concurrency
- Automatic connection pooling via SQLAlchemy
- Indexes on frequently-queried columns (building, low_supply, user_id)
- Webhook notifications are sent asynchronously (don't block API)

## For HackIllinois Judging

**Track:** Best Web API
**Prizes:** 
- Most creative use of API
- Best use of DigitalOcean
- Best use of Gemini/OpenAI API
- Most useful (or useless) project

This submission features:
✅ Fully functional REST API with all CRUD operations
✅ Real-time data synchronization
✅ AI integration (Gemini 2.5 Flash for vibe checks)
✅ Webhook system for external notifications
✅ Proper database design with relationships
✅ Comprehensive error handling
✅ Production-ready async code
✅ Complete API documentation

---

**Last Updated:** February 28, 2026  
**Version:** 1.0.0

## Database Connection Details

**Host:** `litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com`  
**Port:** `25060`  
**User:** `doadmin`  

**MySQL CLI Access:**
```bash
mysql -u doadmin -pAVNS_vDsyhyKt0X96AeGBxtA \
  -h litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com \
  -P 25060 -D defaultdb
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `sqlalchemy>=2.0` - ORM for MySQL
- `aiomysql` - Async MySQL driver
- `python-dotenv` - Environment variable management
- `google-genai` - Gemini API integration

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Then edit `.env` with your Gemini API Key:

```
MYSQL_USER=doadmin
MYSQL_HOST=litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com
MYSQL_PORT=25060
MYSQL_DB=defaultdb
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Initialize Database

Run the initialization script to create all tables:

```bash
python init_db.py
```

This will create two tables:
- **bathrooms** - Stores bathroom metadata (building, floor, gender, ratings, stall occupancy)
- **reviews** - Stores individual student reviews with ratings and comments

### 4. Start the API Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

**Interactive API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database Schema

### Bathrooms Table
```sql
CREATE TABLE bathrooms (
  id VARCHAR(36) PRIMARY KEY,
  building VARCHAR(100) NOT NULL,
  floor INT NOT NULL,
  gender VARCHAR(50) NOT NULL,
  avg_rating FLOAT DEFAULT 0.0,
  is_low_supply BOOLEAN DEFAULT FALSE,
  stalls JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_bathroom_location (building, floor, gender),
  INDEX idx_building (building),
  INDEX idx_low_supply (is_low_supply)
);
```

### Reviews Table
```sql
CREATE TABLE reviews (
  id VARCHAR(36) PRIMARY KEY,
  bathroom_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(100) NOT NULL,
  cleanliness INT NOT NULL,
  ambience INT NOT NULL,
  sink_pressure INT NOT NULL,
  paper_towel_type VARCHAR(100),
  toilet_paper_type VARCHAR(100),
  comment VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_bathroom_review (bathroom_id, user_id),
  FOREIGN KEY (bathroom_id) REFERENCES bathrooms(id) ON DELETE CASCADE,
  INDEX idx_bathroom_id (bathroom_id),
  INDEX idx_user_id (user_id),
  INDEX idx_created_at (created_at)
);
```

## API Endpoints

### Create Bathroom
```
POST /v1/bathrooms
Content-Type: application/json

{
  "building": "Siebel Center",
  "floor": 1,
  "gender": "Men's"
}

Response: 
{
  "id": "uuid",
  "message": "Bathroom indexed successfully."
}
```

### List Bathrooms
```
GET /v1/bathrooms?building=Siebel%20Center

Response: [
  {
    "id": "uuid",
    "building": "Siebel Center",
    "floor": 1,
    "gender": "Men's",
    "avg_rating": 7.5,
    "is_low_supply": false,
    "stalls": {},
    "reviews": [...]
  }
]
```

### Get Specific Bathroom
```
GET /v1/bathrooms/{bathroom_id}
```

### Add Review
```
POST /v1/bathrooms/{bathroom_id}/reviews
Content-Type: application/json

{
  "user_id": "student123",
  "cleanliness": 8,
  "ambience": 7,
  "sink_pressure": 6,
  "paper_towel_type": "standard",
  "toilet_paper_type": "soft",
  "comment": "Generally clean, but soap dispenser empty"
}

Response: (ReviewResponse object with review details)
```

### Update Review
```
PUT /v1/bathrooms/{bathroom_id}/reviews/{review_id}
```

### Update Stall Status
```
POST /v1/bathrooms/{bathroom_id}/stalls
Content-Type: application/json

{
  "bathroom_id": "uuid",
  "stall_id": 1,
  "is_occupied": true
}
```

### Get Vibe Check (AI-Generated)
```
GET /v1/bathrooms/{bathroom_id}/vibe-check

Response:
{
  "bathroom_id": "uuid",
  "vibe_check": "This men's room is basically a pressure washer simulator with mysterious socks as air freshener. Cleanliness is 4/10, vibe is 'industrial disaster area'."
}
```

### Health Check
```
GET /health

Response:
{
  "status": "ok"
}
```

## Key Features

✅ **MySQL Database Integration** - All data persists in DigitalOcean MySQL  
✅ **Async Operations** - Full async/await support for high performance  
✅ **Bathroom Management** - Create and track bathrooms by building/floor/gender  
✅ **Review System** - Students can review bathrooms (1 review per user per bathroom)  
✅ **Automatic Rating** - Average cleanliness rating calculated automatically  
✅ **Low Supply Alert** - Bathrooms flagged when average rating < 4.0  
✅ **Stall Occupancy** - Real-time tracking of stall availability  
✅ **AI Vibe Checks** - Gemini-powered witty summaries of bathroom conditions  
✅ **Data Relationships** - Proper foreign keys and cascading deletes  
✅ **Unique Constraints** - Prevent duplicate bathrooms and reviews  

## Registered Buildings

Valid buildings that can be registered:
- Siebel Center
- ECEB
- Grainger

Attempting to create a bathroom in an unregistered building returns a 403 error.

## Error Handling

All endpoints include proper error handling:
- **400** - Bad request (duplicate bathroom/review)
- **403** - Forbidden (unregistered building)
- **404** - Not found (bathroom or review not found)
- **500** - Server error (database issues)

## Testing the Connection

You can test the database connection manually:

```bash
mysql -u doadmin -pAVNS_vDsyhyKt0X96AeGBxtA \
  -h litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com \
  -P 25060 -D defaultdb

# Once connected, you can query:
SHOW TABLES;
DESCRIBE bathrooms;
DESCRIBE reviews;
```

## Troubleshooting

### Connection Issues
- Verify your IP is whitelisted on DigitalOcean (usually already done)
- Check `.env` file for correct credentials
- Ensure port 25060 is accessible from your network

### Database Not Initializing
- Run `python init_db.py` to create tables
- Check for connection errors in the output
- Verify MySQL credentials are correct

### Reviews Not Saving
- Ensure bathroom exists before adding reviews
- Check that user_id is provided
- Verify all required fields are present

## Production Deployment

For production deployment:

1. Use environment variables via container orchestration
2. Set `echo=False` in SQLAlchemy engine (already done)
3. Use a process manager like Gunicorn:
   ```bash
   gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
   ```
4. Consider adding connection pooling limits
5. Set up proper logging and monitoring

## Architecture

```
┌─────────────────┐
│   FastAPI App   │
├─────────────────┤
│  main.py        │
│  (Endpoints)    │
├─────────────────┤
│  SQLAlchemy ORM │
├─────────────────┤
│  aiomysql Async │
├─────────────────┤
│  DigitalOcean   │
│  MySQL Database │
└─────────────────┘
```

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review error messages carefully
3. Check DigitalOcean console for database status
4. Verify database connection with MySQL CLI

---

**Last Updated:** February 28, 2026  
**Version:** 1.0.0
