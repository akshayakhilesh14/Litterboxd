import asyncio
import uuid
import boto3
from fastapi import UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
import logging
from fastapi import FastAPI, HTTPException, status, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from models import EventModel
import math
from sqlalchemy import text

from fastapi.responses import FileResponse

from database import AsyncSession, init_db, get_db
from models import (
    BathroomModel, ReviewModel, WebhookModel, FavoriteModel, StallModel,
    BathroomCreate, BathroomResponse,
    ReviewCreate, ReviewResponse,
    WebhookCreate, WebhookResponse,
    FavoriteCreate, FavoriteResponse,
    StallUpdate, StallResponse,
    BuildingEnum,
    BathroomMapPoint,
    SensorStallUpdate,
)
from ai_service import generate_vibe_check
from webhooks import notify_low_supply
from error_handlers import (
    ValidationError, NotFoundError, ConflictError, InternalServerError,
    ForbiddenError,
    validate_rating, validate_floor_number, validate_url,
    validate_bathroom_id, validate_stall_number
)
from middleware import RequestLoggingMiddleware, ErrorLoggingMiddleware

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with metadata
app = FastAPI(
    title="Litterboxd API",
    version="1.0.0",
    description="Real-time campus bathroom review and rating system with AI-powered summaries",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware for request tracking and error logging
app.add_middleware(ErrorLoggingMiddleware)
app.add_middleware(RequestLoggingMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins (dev only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# First route registered: locations (so it's never shadowed). Your running process must load THIS file.
@app.get("/v1/locations", tags=["Locations"])
async def get_v1_locations(db: AsyncSession = Depends(get_db)) -> List[dict]:
    """Bathroom map points: floor, building, longitude, latitude, and stall occupancy (has_available_stall)."""
    result = await db.execute(
        select(BathroomModel)
        .options(selectinload(BathroomModel.stalls))
    )
    bathrooms = result.scalars().unique().all()
    out = []
    for b in bathrooms:
        stalls_total = len(b.stalls) if b.stalls else 0
        stalls_open = sum(1 for s in b.stalls if not s.is_occupied) if b.stalls else 0
        out.append({
            "bathroom_id": b.bathroom_id,
            "floor_number": b.floor_number,
            "building_name": b.building_name,
            "longitude": float(b.longitude) if b.longitude is not None else None,
            "latitude": float(b.latitude) if b.latitude is not None else None,
            "stalls_open": stalls_open,
            "stalls_total": stalls_total,
        })
    return out


REGISTERED_BUILDINGS = {BuildingEnum.SIEBEL,
                        BuildingEnum.GRAINGER, BuildingEnum.CIF}
LOW_SUPPLY_THRESHOLD = 4.0  # out of 10

@app.get("/locations", include_in_schema=False)
async def list_bathroom_map_points_alias(db: AsyncSession = Depends(get_db)) -> List[dict]:
    """Alias for GET /v1/locations (same response including has_available_stall)."""
    return await get_v1_locations(db)


@app.on_event("startup")
async def startup():
    """Initialize database on startup (non-blocking so server comes up even if DB is slow/unreachable)."""
    try:
        await asyncio.wait_for(init_db(), timeout=10.0)
        logger.info("Database initialized.")
    except asyncio.TimeoutError:
        logger.warning("Database init timed out after 10s. Server is up; first DB request may fail.")
    except Exception as e:
        logger.warning("Database init failed: %s. Server is up; first DB request may fail.", e)


@app.post("/v1/bathrooms", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_bathroom(
    bathroom: BathroomCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new bathroom entry.

    **Status Codes:**
    - 201: Bathroom created successfully
    - 400: Invalid input data
    - 403: Building not registered by faculty
    - 409: Bathroom already exists at this location
    - 500: Internal server error
    """

    logger.info(
        f"Creating bathroom: {bathroom.building_name} Floor {bathroom.floor_number}")

    # Validate building is registered
    if bathroom.building_name not in REGISTERED_BUILDINGS:
        logger.warning(
            f"Attempt to create bathroom with unregistered building: {bathroom.building_name}")
        raise ForbiddenError(
            message=f"Building {bathroom.building_name.value} not registered by faculty. Only {', '.join([b.value for b in REGISTERED_BUILDINGS])} are allowed."
        )

    # Validate floor number
    validate_floor_number(bathroom.floor_number)

    try:
        # Create new bathroom (store as plain string to match existing DB values)
        new_bathroom = BathroomModel(
            building_name=bathroom.building_name.value,
            floor_number=bathroom.floor_number,
            bathroom_gender=bathroom.bathroom_gender.value,
            ai_review=None,
            tp_supply=(
                bathroom.tp_supply.value if bathroom.tp_supply is not None else None),
            hygiene_supply=(
                bathroom.hygiene_supply.value if bathroom.hygiene_supply is not None else None),
            last_cleaned=bathroom.last_cleaned,
            is_accessible=bathroom.is_accessible
        )

        db.add(new_bathroom)
        await db.commit()

        logger.info(
            f"Bathroom created successfully with ID: {new_bathroom.bathroom_id}")

        return {
            "bathroom_id": new_bathroom.bathroom_id,
            "message": "Bathroom indexed successfully."
        }
    except IntegrityError:
        await db.rollback()
        logger.warning(
            f"Bathroom already exists at {bathroom.building_name} Floor {bathroom.floor_number}")
        raise ConflictError(
            message=f"Bathroom already exists at this location ({bathroom.building_name.value}, Floor {bathroom.floor_number}, {bathroom.bathroom_gender.value})"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating bathroom: {str(e)}", exc_info=True)
        raise InternalServerError(
            message=f"Failed to create bathroom: {str(e)}"
        )


@app.get("/v1/bathrooms", response_model=List[BathroomResponse])
async def list_bathrooms(
    building: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List all bathrooms, optionally filtered by building"""

    query = select(BathroomModel).options(
        selectinload(BathroomModel.reviews),
        selectinload(BathroomModel.stalls)
    )

    if building:
        try:
            building_enum = BuildingEnum(building)
            # compare against stored string value
            query = query.where(
                BathroomModel.building_name == building_enum.value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid building: {building}"
            )

    result = await db.execute(query)
    bathrooms = result.scalars().unique().all()

    return bathrooms


@app.get("/v1/bathrooms/{bathroom_id}", response_model=BathroomResponse)
async def get_bathroom(
    bathroom_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific bathroom by ID.

    **Status Codes:**
    - 200: Bathroom found and returned
    - 404: Bathroom not found
    - 500: Internal server error
    """

    logger.info(f"Fetching bathroom {bathroom_id}")

    validate_bathroom_id(bathroom_id)

    try:
        query = select(BathroomModel).where(
            BathroomModel.bathroom_id == bathroom_id
        ).options(
            selectinload(BathroomModel.reviews),
            selectinload(BathroomModel.stalls)
        )

        result = await db.execute(query)
        bathroom = result.scalar_one_or_none()

        if not bathroom:
            logger.warning(f"Bathroom not found: {bathroom_id}")
            raise NotFoundError("Bathroom", f"ID {bathroom_id}")

        return bathroom
    except Exception as e:
        if isinstance(e, NotFoundError):
            raise
        logger.error(f"Error fetching bathroom: {str(e)}", exc_info=True)
        raise InternalServerError()


# @app.post("/v1/bathrooms/{bathroom_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
# async def add_review(
#     bathroom_id: int,
#     review_in: ReviewCreate,
#     user_id: str = Query(..., min_length=1, description="Student email or user ID"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Add a review to a bathroom.

#     **Status Codes:**
#     - 201: Review created successfully
#     - 400: Invalid input data or rating out of range
#     - 404: Bathroom not found
#     - 409: User already reviewed this bathroom
#     - 500: Internal server error
#     """

#     logger.info(f"Adding review for bathroom {bathroom_id} by user {user_id}")

#     # Validate inputs
#     validate_bathroom_id(bathroom_id)
#     validate_rating(review_in.rating, "rating")

#     # Check if bathroom exists
#     bathroom_result = await db.execute(
#         select(BathroomModel).where(BathroomModel.bathroom_id == bathroom_id)
#     )
#     bathroom = bathroom_result.scalar_one_or_none()

#     if not bathroom:
#         logger.warning(f"Bathroom not found: {bathroom_id}")
#         raise NotFoundError("Bathroom", f"ID {bathroom_id}")

#     try:
#         # Create new review
#         new_review = ReviewModel(
#             bathroom_id=bathroom_id,
#             rating=review_in.rating,
#             comment=review_in.comment
#         )

#         db.add(new_review)
#         await db.commit()
#         await db.refresh(new_review)

#         logger.info(f"Review created successfully: ID {new_review.review_id}")

#         # Update bathroom's AI review if there's a new review
#         await update_bathroom_ai_review(bathroom_id, db)

#         # Check if low supply and trigger webhook
#         avg_rating = await get_bathroom_avg_rating(bathroom_id, db)
#         if avg_rating < LOW_SUPPLY_THRESHOLD:
#             # Get all active webhooks and notify
#             webhook_result = await db.execute(
#                 select(WebhookModel).where(
#                     and_(
#                         WebhookModel.is_active == True,
#                         WebhookModel.event_type == "low_supply"
#                     )
#                 )
#             )
#             webhooks = webhook_result.scalars().all()
#             webhook_urls = [w.url for w in webhooks]

#             if webhook_urls:
#                 logger.info(f"Low supply alert triggered for bathroom {bathroom_id}, rating: {avg_rating}")
#                 await notify_low_supply(
#                     bathroom_id,
#                     getattr(bathroom.building_name, "value", bathroom.building_name),
#                     bathroom.floor_number,
#                     getattr(bathroom.bathroom_gender, "value", bathroom.bathroom_gender),
#                     avg_rating,
#                     webhook_urls
#                 )

#         return new_review

#     except IntegrityError:
#         await db.rollback()
#         logger.warning(f"User {user_id} already reviewed bathroom {bathroom_id}")
#         raise ConflictError(
#             message=f"User {user_id} has already reviewed this bathroom. Use PUT to update your review."
#         )
#     except Exception as e:
#         await db.rollback()
#         logger.error(f"Error creating review: {str(e)}", exc_info=True)
#         raise InternalServerError(
#             message=f"Failed to create review: {str(e)}"
#         )

"""
@app.post("/v1/bathrooms/{bathroom_id}/stalls", status_code=status.HTTP_200_OK, response_model=StallResponse)
async def post_stall_data(
    bathroom_id: int,
    data: StallUpdate,
    db: AsyncSession = Depends(get_db)
):
    
    Update stall occupancy status (from IoT sensors).

    **Status Codes:**
    - 200: Stall status updated
    - 400: Invalid input data
    - 404: Bathroom not found
    - 500: Internal server error
    

    logger.info(
        f"Updating stall {data.stall_number} for bathroom {bathroom_id}")

    # Validate inputs
    validate_bathroom_id(bathroom_id)
    validate_stall_number(data.stall_number)

    # Check if bathroom exists
    bathroom_result = await db.execute(
        select(BathroomModel).where(BathroomModel.bathroom_id == bathroom_id)
    )
    bathroom = bathroom_result.scalar_one_or_none()

    if not bathroom:
        logger.warning(f"Bathroom not found: {bathroom_id}")
        raise NotFoundError("Bathroom", f"ID {bathroom_id}")

    try:
        # Get or create stall
        stall_result = await db.execute(
            select(StallModel).where(
                and_(
                    StallModel.bathroom_id == bathroom_id,
                    StallModel.stall_number == data.stall_number
                )
            )
        )
        stall = stall_result.scalar_one_or_none()

        if stall:
            stall.is_occupied = data.is_occupied
        else:
            stall = StallModel(
                bathroom_id=bathroom_id,
                stall_number=data.stall_number,
                is_occupied=data.is_occupied
            )
            db.add(stall)

        await db.commit()
        await db.refresh(stall)

        return stall

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating stall: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
"""

@app.post("/v1/bathrooms/{bathroom_id}/stalls", 
          status_code=status.HTTP_200_OK, 
          response_model=StallResponse)
async def post_stall_data(
    bathroom_id: int,
    data: StallUpdate,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Updating stall {data.stall_number} for bathroom {bathroom_id}")

    validate_bathroom_id(bathroom_id)
    validate_stall_number(data.stall_number)

    # Ensure bathroom exists
    bathroom_result = await db.execute(
        select(BathroomModel).where(BathroomModel.bathroom_id == bathroom_id)
    )
    if not bathroom_result.scalar_one_or_none():
        raise NotFoundError("Bathroom", f"ID {bathroom_id}")

    try:
        # Get stall
        stall_result = await db.execute(
            select(StallModel).where(
                and_(
                    StallModel.bathroom_id == bathroom_id,
                    StallModel.stall_number == data.stall_number
                )
            )
        )
        stall = stall_result.scalar_one_or_none()

        state_changed = False

        if stall:
            if stall.is_occupied != data.is_occupied:
                state_changed = True
                stall.is_occupied = data.is_occupied
                stall.last_updated = datetime.utcnow()
        else:
            state_changed = True
            stall = StallModel(
                bathroom_id=bathroom_id,
                stall_number=data.stall_number,
                is_occupied=data.is_occupied,
                last_updated=datetime.utcnow()
            )
            db.add(stall)

        if state_changed:
            new_event = EventModel(
                bathroom_id=bathroom_id,
                stall_number=data.stall_number,
                is_occupied=data.is_occupied,
                created_at=datetime.utcnow()
            )
            db.add(new_event)

        await db.commit()
        await db.refresh(stall)

        return stall

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating stall: {str(e)}", exc_info=True)
        raise InternalServerError(message="Failed to update stall")


@app.get("/v1/bathrooms/{bathroom_id}/vibe-check")
async def get_vibe_check(
    bathroom_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI vibe check for a bathroom based on reviews"""

    query = select(BathroomModel).where(
        BathroomModel.bathroom_id == bathroom_id
    ).options(selectinload(BathroomModel.reviews))

    result = await db.execute(query)
    bathroom = result.scalar_one_or_none()

    if not bathroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bathroom not found"
        )

    # Extract review comments
    review_comments = [r.comment for r in bathroom.reviews if r.comment]

    if not review_comments:
        return {
            "bathroom_id": bathroom_id,
            "vibe_check": "No reviews yet. Be the first to describe this bathroom!"
        }

    # Generate AI vibe check
    vibe_check = generate_vibe_check(
        gender=getattr(bathroom.bathroom_gender, "value",
                       bathroom.bathroom_gender),
        building=getattr(bathroom.building_name, "value",
                         bathroom.building_name),
        floor=bathroom.floor_number,
        reviews=review_comments
    )

    # Update AI review in database
    bathroom.ai_review = vibe_check
    await db.commit()

    return {
        "bathroom_id": bathroom_id,
        "vibe_check": vibe_check
    }


@app.get("/v1/bathrooms/{bathroom_id}/stalls", response_model=List[StallResponse])
async def get_stalls(
    bathroom_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all stalls for a bathroom"""

    result = await db.execute(
        select(StallModel).where(StallModel.bathroom_id == bathroom_id)
    )
    stalls = result.scalars().all()

    return stalls


@app.put("/v1/bathrooms/{bathroom_id}/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    bathroom_id: int,
    review_id: int,
    review_in: ReviewCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing review"""

    # Get the review
    review_result = await db.execute(
        select(ReviewModel).where(
            and_(
                ReviewModel.review_id == review_id,
                ReviewModel.bathroom_id == bathroom_id
            )
        )
    )
    review = review_result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    try:
        # Update review
        review.rating = review_in.rating
        review.comment = review_in.comment

        await db.commit()
        await db.refresh(review)

        # Update bathroom's AI review
        await update_bathroom_ai_review(bathroom_id, db)

        # Check low supply again
        avg_rating = await get_bathroom_avg_rating(bathroom_id, db)
        if avg_rating < LOW_SUPPLY_THRESHOLD:
            webhook_result = await db.execute(
                select(WebhookModel).where(
                    and_(
                        WebhookModel.is_active == True,
                        WebhookModel.event_type == "low_supply"
                    )
                )
            )
            webhooks = webhook_result.scalars().all()
            webhook_urls = [w.url for w in webhooks]

            if webhook_urls:
                bathroom = await db.execute(
                    select(BathroomModel).where(
                        BathroomModel.bathroom_id == bathroom_id)
                )
                bath = bathroom.scalar_one()

                await notify_low_supply(
                    bathroom_id,
                    getattr(bath.building_name, "value", bath.building_name),
                    bath.floor_number,
                    getattr(bath.bathroom_gender, "value",
                            bath.bathroom_gender),
                    avg_rating,
                    webhook_urls
                )

        return review

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/v1/webhooks", status_code=status.HTTP_201_CREATED, response_model=WebhookResponse)
async def register_webhook(
    webhook: WebhookCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a webhook endpoint for low-supply alerts.

    **Status Codes:**
    - 201: Webhook registered successfully
    - 400: Invalid URL format
    - 409: Webhook URL already registered
    - 500: Internal server error
    """

    logger.info(f"Registering webhook: {webhook.url}")

    # Validate URL format
    validate_url(webhook.url)

    try:
        new_webhook = WebhookModel(
            url=webhook.url,
            event_type=webhook.event_type,
            is_active=True
        )

        db.add(new_webhook)
        await db.commit()
        await db.refresh(new_webhook)

        logger.info(
            f"Webhook registered successfully: ID {new_webhook.webhook_id}")

        return new_webhook

    except IntegrityError:
        await db.rollback()
        logger.warning(f"Webhook already registered: {webhook.url}")
        raise ConflictError(
            message=f"Webhook URL already registered: {webhook.url}"
        )
    except ValidationError:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error registering webhook: {str(e)}", exc_info=True)
        raise InternalServerError(
            message=f"Failed to register webhook: {str(e)}"
        )


@app.get("/v1/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    event_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List all webhooks, optionally filtered by event type"""

    query = select(WebhookModel)

    if event_type:
        query = query.where(WebhookModel.event_type == event_type)

    result = await db.execute(query)
    webhooks = result.scalars().all()

    return webhooks


@app.delete("/v1/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a webhook"""

    webhook_result = await db.execute(
        select(WebhookModel).where(WebhookModel.webhook_id == webhook_id)
    )
    webhook = webhook_result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    try:
        await db.delete(webhook)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/v1/users/{user_id}/favorites", status_code=status.HTTP_201_CREATED, response_model=FavoriteResponse)
async def add_favorite(
    user_id: str,
    favorite_in: FavoriteCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a bathroom to user favorites"""

    # Verify bathroom exists
    bathroom_result = await db.execute(
        select(BathroomModel).where(
            BathroomModel.bathroom_id == favorite_in.bathroom_id)
    )
    if not bathroom_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bathroom not found"
        )

    try:
        new_favorite = FavoriteModel(
            user_id=user_id,
            bathroom_id=favorite_in.bathroom_id
        )

        db.add(new_favorite)
        await db.commit()
        await db.refresh(new_favorite)

        return new_favorite

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already favorited"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding favorite: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/v1/users/{user_id}/favorites", response_model=List[FavoriteResponse])
async def list_favorites(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List user favorite bathrooms"""

    result = await db.execute(
        select(FavoriteModel).where(FavoriteModel.user_id == user_id)
    )
    favorites = result.scalars().all()

    return favorites


@app.delete("/v1/users/{user_id}/favorites/{bathroom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    user_id: str,
    bathroom_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove a bathroom from user favorites"""

    favorite_result = await db.execute(
        select(FavoriteModel).where(
            and_(
                FavoriteModel.user_id == user_id,
                FavoriteModel.bathroom_id == bathroom_id
            )
        )
    )
    favorite = favorite_result.scalar_one_or_none()

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )

    try:
        await db.delete(favorite)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Error removing favorite: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ===== HEALTH CHECK =====

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    **Status Codes:**
    - 200: Server is healthy and ready to accept requests
    """
    logger.debug("Health check requested")
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Litterboxd API is running"
    }


# ===== MINIMUM UI (optional; revert by removing these two routes and static/) =====

_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", include_in_schema=False)
async def ui_index():
    """Serve list-of-bathrooms UI."""
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/review", include_in_schema=False)
async def ui_review():
    """Serve review form UI."""
    return FileResponse(_STATIC_DIR / "review.html")


@app.get("/map", include_in_schema=False)
async def ui_map():
    """Serve locations/map UI (longitude, latitude)."""
    return FileResponse(_STATIC_DIR / "map.html")


@app.get("/favorites", include_in_schema=False)
async def ui_favorites():
    """Serve My Favorites UI."""
    return FileResponse(_STATIC_DIR / "favorites.html")


@app.get("/reviews", include_in_schema=False)
async def ui_reviews():
    """Serve bathroom reviews list UI (individual reviews for one bathroom)."""
    return FileResponse(_STATIC_DIR / "reviews.html")


# ===== HELPER FUNCTIONS =====

async def get_bathroom_avg_rating(bathroom_id: int, db: AsyncSession) -> float:
    """Calculate average rating for a bathroom"""
    result = await db.execute(
        select(func.avg(ReviewModel.rating)).where(
            ReviewModel.bathroom_id == bathroom_id
        )
    )
    avg = result.scalar()
    return float(avg) if avg else 0.0


async def update_bathroom_ai_review(bathroom_id: int, db: AsyncSession):
    """Update bathroom's AI review based on current reviews"""
    bathroom_result = await db.execute(
        select(BathroomModel).where(
            BathroomModel.bathroom_id == bathroom_id
        ).options(selectinload(BathroomModel.reviews))
    )
    bathroom = bathroom_result.scalar_one_or_none()

    if bathroom and bathroom.reviews:
        review_comments = [r.comment for r in bathroom.reviews if r.comment]

        if review_comments:
            vibe_check = generate_vibe_check(
                gender=getattr(bathroom.bathroom_gender,
                               "value", bathroom.bathroom_gender),
                building=getattr(bathroom.building_name,
                                 "value", bathroom.building_name),
                floor=bathroom.floor_number,
                reviews=review_comments
            )
            bathroom.ai_review = vibe_check
            await db.commit()


# Initialize DigitalOcean Spaces client (can also do this at startup)
session = boto3.session.Session()
s3_client = session.client(
    's3',
    region_name='nyc3',  # e.g., 'nyc3'
    endpoint_url='https://nyc3.digitaloceanspaces.com',
    aws_access_key_id='DO00A9UE4DWXF984YR8N',
    aws_secret_access_key='K0TsC6rZMlyOujgLg2De0K0mxzPG9B7fsb8/ZycyDgo'
)


async def upload_image_to_do_space(file: UploadFile) -> str:
    """
    Upload file to DigitalOcean Space and return public URL
    """
    ext = file.filename.split('.')[-1]
    key = f"reviews/{uuid.uuid4()}.{ext}"

    s3_client.upload_fileobj(
        file.file,
        'litterboxd-space',  # replace with your Space name
        key,
        ExtraArgs={'ACL': 'public-read', 'ContentType': file.content_type}
    )

    return f"https://litterboxd-space.nyc3.digitaloceanspaces.com/{key}"


@app.post("/v1/bathrooms/{bathroom_id}/reviews", response_model=ReviewResponse, status_code=201)
async def add_review(
    bathroom_id: int,
    rating: float = Form(..., ge=0, le=10),
    comment: str = Form(None),
    image: UploadFile = File(None),  # optional image
    user_id: str = Query(..., min_length=1,
                         description="Student email or user ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a review to a bathroom, optionally including an image.
    """
    # Validate bathroom exists
    bathroom_result = await db.execute(
        select(BathroomModel).where(BathroomModel.bathroom_id == bathroom_id)
    )
    bathroom = bathroom_result.scalar_one_or_none()
    if not bathroom:
        raise NotFoundError("Bathroom", f"ID {bathroom_id}")

    # Validate rating
    validate_rating(rating, "rating")

    # Upload image if provided
    image_url = None
    if image:
        image_url = await upload_image_to_do_space(image)

    try:
        new_review = ReviewModel(
            bathroom_id=bathroom_id,
            rating=rating,
            comment=comment,
            image_url=image_url
        )
        db.add(new_review)
        await db.commit()
        await db.refresh(new_review)

        # Update AI vibe check
        await update_bathroom_ai_review(bathroom_id, db)

        # Trigger low supply webhooks if needed
        avg_rating = await get_bathroom_avg_rating(bathroom_id, db)
        if avg_rating < LOW_SUPPLY_THRESHOLD:
            webhook_result = await db.execute(
                select(WebhookModel).where(
                    and_(WebhookModel.is_active == True,
                         WebhookModel.event_type == "low_supply")
                )
            )
            webhooks = webhook_result.scalars().all()
            webhook_urls = [w.url for w in webhooks]
            if webhook_urls:
                await notify_low_supply(
                    bathroom_id,
                    getattr(bathroom.building_name, "value",
                            bathroom.building_name),
                    bathroom.floor_number,
                    getattr(bathroom.bathroom_gender, "value",
                            bathroom.bathroom_gender),
                    avg_rating,
                    webhook_urls
                )

        return new_review

    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            message=f"User {user_id} has already reviewed this bathroom. Use PUT to update."
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating review: {str(e)}", exc_info=True)
        raise InternalServerError(message=f"Failed to create review: {str(e)}")

"""
@app.post("/v1/sensors/stalls", status_code=status.HTTP_200_OK, response_model=StallResponse)
async def sensor_post_stall_update(
    payload: SensorStallUpdate = Body(...),
    db: AsyncSession = Depends(get_db)
):
    
    Sensor ingest endpoint.
    Expects JSON: {"id": "<device_id>", "stall_id": <int>, "is_occupied": true/false}
    Updates stalls table by stall_number (= stall_id) and sets last_updated.
    
    validate_stall_number(payload.stall_id)
    try:
        stall_result = await db.execute(
            select(StallModel).where(StallModel.stall_number == payload.stall_id)
        )
        stall = stall_result.scalar_one_or_none()
        if not stall:
            raise NotFoundError("Stall", f"stall_number {payload.stall_id}")
        stall.is_occupied = payload.is_occupied
        stall.last_updated = datetime.utcnow()
        await db.commit()
        await db.refresh(stall)
        return stall
    except Exception as e:
        await db.rollback()
        if isinstance(e, NotFoundError):
            raise
        logger.error(f"Error ingesting sensor stall update: {str(e)}", exc_info=True)
        raise InternalServerError(message=f"Failed to ingest sensor update: {str(e)}")
"""

@app.post("/v1/sensors/stalls", status_code=status.HTTP_200_OK, response_model=StallResponse)
async def sensor_post_stall_update(
    payload: SensorStallUpdate = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Sensor ingest endpoint.
    Expects JSON: {"id": "<device_id>", "stall_id": <int>, "is_occupied": true/false}

    Writes:
      - stalls (current truth used by /v1/locations)
      - events (history used for analytics/prediction)
    """
    validate_stall_number(payload.stall_id)

    try:
        # 1) Load current snapshot row
        stall_result = await db.execute(
            select(StallModel).where(StallModel.stall_number == payload.stall_id)
        )
        stall = stall_result.scalar_one_or_none()
        if not stall:
            raise NotFoundError("Stall", f"stall_number {payload.stall_id}")

        # 2) Detect real state change
        changed = (bool(stall.is_occupied) != bool(payload.is_occupied))

        # 3) Update snapshot ALWAYS (so /v1/locations stays correct)
        stall.is_occupied = payload.is_occupied
        stall.last_updated = datetime.utcnow()

        # 4) Append event ONLY when changed (prevents redundant spam)
        if changed:
            db.add(EventModel(
                bathroom_id=stall.bathroom_id,   # taken from stall row
                stall_number=stall.stall_number,
                is_occupied=payload.is_occupied,
                created_at=datetime.utcnow(),
            ))

        await db.commit()
        await db.refresh(stall)
        return stall

    except Exception as e:
        await db.rollback()
        if isinstance(e, NotFoundError):
            raise
        logger.error(f"Error ingesting sensor stall update: {str(e)}", exc_info=True)
        raise InternalServerError(message=f"Failed to ingest sensor update: {str(e)}")
    
@app.get("/v1/bathrooms/{bathroom_id}/availability-forecast", tags=["Real-time"])
async def availability_forecast(
    bathroom_id: int,
    minutes: int = Query(5, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
):
    """
    Predict probability that at least one stall will be free within `minutes`.

    Uses:
      - stalls table: current occupancy (truth right now)
      - events table: historical occupied->free durations (to estimate rate)
    Formula used HERE:
      For currently occupied stalls:
        P(free within T) = 1 - exp(-T / avg_occupied_time)
      For currently free stalls:
        P(free within T) = 1
    """
    validate_bathroom_id(bathroom_id)

    # --- 0) Ensure bathroom exists (reuse your existing pattern)
    bathroom_result = await db.execute(
        select(BathroomModel).where(BathroomModel.bathroom_id == bathroom_id)
    )
    if not bathroom_result.scalar_one_or_none():
        raise NotFoundError("Bathroom", f"ID {bathroom_id}")

    T_sec = minutes * 60

    # --- 1) Load current stalls for this bathroom (current state)
    stalls_result = await db.execute(
        select(StallModel.stall_number, StallModel.is_occupied, StallModel.last_updated)
        .where(StallModel.bathroom_id == bathroom_id)
    )
    stalls = stalls_result.all()

    if not stalls:
        return {
            "bathroom_id": bathroom_id,
            "minutes": minutes,
            "overall_probability_any_free": 0.0,
            "per_stall": [],
            "note": "No stalls registered for this bathroom."
        }

    stall_numbers = [s.stall_number for s in stalls]

    # --- 2) Compute avg occupied duration per stall from events
    # We pair each occupied event with the next event for that stall, and only keep occupied->free transitions.
    # Requires MySQL 8+ window functions (LEAD).
    avg_sql = text("""
        WITH ordered AS (
          SELECT
            bathroom_id,
            stall_number,
            is_occupied,
            created_at,
            LEAD(is_occupied) OVER (PARTITION BY bathroom_id, stall_number ORDER BY created_at) AS next_occ,
            LEAD(created_at)  OVER (PARTITION BY bathroom_id, stall_number ORDER BY created_at) AS next_time
          FROM events
          WHERE bathroom_id = :bathroom_id
            AND stall_number IN :stall_numbers
        ),
        sessions AS (
          SELECT
            stall_number,
            TIMESTAMPDIFF(SECOND, created_at, next_time) AS occ_seconds
          FROM ordered
          WHERE is_occupied = 1
            AND next_occ = 0
            AND next_time IS NOT NULL
        )
        SELECT stall_number, AVG(occ_seconds) AS avg_occ_seconds
        FROM sessions
        GROUP BY stall_number;
    """)

    avg_result = await db.execute(
        avg_sql,
        {"bathroom_id": bathroom_id, "stall_numbers": tuple(stall_numbers)}
    )
    avg_rows = avg_result.all()
    avg_map = {r.stall_number: (float(r.avg_occ_seconds) if r.avg_occ_seconds is not None else None)
               for r in avg_rows}

    # --- 3) Apply the formula HERE (THIS IS WHERE IT IS USED)
    per_stall = []
    p_none_free = 1.0  # used to compute overall = 1 - product(1 - p_i_free)

    for stall_number, is_occupied, last_updated in stalls:
        if not is_occupied:
            # already free => probability free within T is 1
            p_free_T = 1.0
            avg_occ = avg_map.get(stall_number)
        else:
            avg_occ = avg_map.get(stall_number)
            if avg_occ is None or avg_occ <= 0:
                # no history: can't estimate. choose conservative default.
                p_free_T = 0.0
            else:
                # P(free within T) = 1 - exp(-T / avg_occ)
                p_free_T = 1.0 - math.exp(-float(T_sec) / float(avg_occ))

        per_stall.append({
            "stall_number": stall_number,
            "is_occupied_now": bool(is_occupied),
            "avg_occupied_seconds": avg_occ,   # can be None
            "p_free_within_minutes": round(p_free_T, 6),
            "last_updated": last_updated.isoformat() if last_updated else None,
        })

        p_none_free *= (1.0 - p_free_T)

    overall = 1.0 - p_none_free

    return {
        "bathroom_id": bathroom_id,
        "minutes": minutes,
        "overall_probability_any_free": round(overall, 6),
        "per_stall": per_stall,
        "formula_used": "occupied: 1-exp(-T/avg_occ), free: 1",
        "assumptions": {
            "avg_occ_seconds": "computed from occupied->free transitions in events",
            "no_history_behavior": "occupied stall with no history => probability 0.0 (conservative)"
        }
    }
