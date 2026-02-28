"""
Database Models (SQLAlchemy ORM) - DigitalOcean MySQL Schema
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


class BuildingEnum(str, enum.Enum):
    """Valid buildings for bathrooms"""
    SIEBEL = "Siebel"
    GRAINGER = "Grainger"
    CIF = "CIF"


class GenderEnum(str, enum.Enum):
    """Valid bathroom genders"""
    SOMBR = "Sombr"  # As specified in DO schema
    GRACIE_ABRAMS = "Gracie Abrams"  # As specified in DO schema
    UNISEX = "Unisex"


class SupplyEnum(str, enum.Enum):
    """Supply level enum"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class BathroomModel(Base):
    """SQLAlchemy ORM model for Bathroom - matches DigitalOcean schema"""
    __tablename__ = "bathrooms"

    bathroom_id = Column(Integer, primary_key=True, autoincrement=True)
    # store building name as plain string to be tolerant of database enum variants
    building_name = Column(String(50), nullable=False, index=True)
    floor_number = Column(Integer, nullable=False)
    # Store enums as plain strings to tolerate remote DB enum variations
    bathroom_gender = Column(String(50), nullable=False)
    ai_review = Column(Text, nullable=True)
    tp_supply = Column(String(20), default=SupplyEnum.HIGH.value)
    hygiene_supply = Column(String(20), default=SupplyEnum.HIGH.value)
    last_cleaned = Column(DateTime, nullable=True)
    is_accessible = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    reviews = relationship("ReviewModel", back_populates="bathroom", cascade="all, delete-orphan")
    stalls = relationship("StallModel", back_populates="bathroom", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('building_name', 'floor_number', 'bathroom_gender',
                         name='uq_bathroom_location'),
    )
    
    @property
    def avg_rating(self) -> float:
        """Calculate average rating from all reviews"""
        if not self.reviews:
            return 0.0
        return sum(r.rating for r in self.reviews) / len(self.reviews)
    
    @property
    def is_low_supply(self) -> bool:
        """Check if bathroom is low supply"""
        return self.avg_rating < 4.0 if self.reviews else False


class ReviewModel(Base):
    """SQLAlchemy ORM model for Review - matches DigitalOcean schema"""
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    bathroom_id = Column(Integer, ForeignKey("bathrooms.bathroom_id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # CHECK (rating BETWEEN 1 AND 10)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    bathroom = relationship("BathroomModel", back_populates="reviews")


class StallModel(Base):
    """SQLAlchemy ORM model for Stall - matches DigitalOcean schema"""
    __tablename__ = "stalls"

    stall_number = Column(Integer, primary_key=True, autoincrement=True)
    bathroom_id = Column(Integer, ForeignKey("bathrooms.bathroom_id"), nullable=False, index=True)
    is_occupied = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bathroom = relationship("BathroomModel", back_populates="stalls")

    __table_args__ = (
        UniqueConstraint('bathroom_id', 'stall_number', name='uq_bathroom_stall'),
    )


class WebhookModel(Base):
    """SQLAlchemy ORM model for Webhook subscriptions"""
    __tablename__ = "webhooks"

    webhook_id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), nullable=False, unique=True, index=True)
    event_type = Column(String(50), nullable=False)  # "low_supply"
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered_at = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)


class FavoriteModel(Base):
    """SQLAlchemy ORM model for User bathroom favorites"""
    __tablename__ = "favorites"

    favorite_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    bathroom_id = Column(Integer, ForeignKey("bathrooms.bathroom_id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    bathroom = relationship("BathroomModel")

    __table_args__ = (
        UniqueConstraint('user_id', 'bathroom_id', name='uq_user_bathroom_favorite'),
    )



"""
Pydantic Models (for API serialization)
"""


class ReviewCreate(BaseModel):
    """Request model for creating/updating a review"""
    rating: int = Field(..., ge=1, le=10)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    """Response model for review"""
    review_id: int
    bathroom_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class StallResponse(BaseModel):
    """Response model for stall"""
    stall_number: int
    bathroom_id: int
    is_occupied: bool
    last_updated: datetime

    class Config:
        from_attributes = True


class BathroomCreate(BaseModel):
    """Request model for creating a bathroom"""
    building_name: BuildingEnum
    floor_number: int
    bathroom_gender: GenderEnum
    tp_supply: Optional[SupplyEnum] = SupplyEnum.HIGH
    hygiene_supply: Optional[SupplyEnum] = SupplyEnum.HIGH
    last_cleaned: Optional[datetime] = None
    is_accessible: bool = False


class BathroomResponse(BaseModel):
    """Response model for bathroom"""
    bathroom_id: int
    building_name: BuildingEnum
    floor_number: int
    bathroom_gender: GenderEnum
    ai_review: Optional[str]
    tp_supply: SupplyEnum
    hygiene_supply: SupplyEnum
    last_cleaned: Optional[datetime]
    is_accessible: bool
    created_at: datetime
    avg_rating: Optional[float] = 0.0
    is_low_supply: bool = False
    reviews: List[ReviewResponse] = []
    stalls: List[StallResponse] = []

    class Config:
        from_attributes = True


class StallUpdate(BaseModel):
    """Request model for updating stall status"""
    stall_number: int
    is_occupied: bool


class WebhookCreate(BaseModel):
    """Request model for creating a webhook"""
    url: str
    event_type: str = "low_supply"


class WebhookResponse(BaseModel):
    """Response model for webhook"""
    webhook_id: int
    url: str
    event_type: str
    is_active: bool
    created_at: datetime
    last_triggered_at: Optional[datetime]
    failure_count: int

    class Config:
        from_attributes = True


class FavoriteCreate(BaseModel):
    """Request model for creating a favorite"""
    bathroom_id: int


class FavoriteResponse(BaseModel):
    """Response model for favorite"""
    favorite_id: int
    user_id: str
    bathroom_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Legacy compatibility (can be removed)
class Bathroom(BaseModel):
    """Legacy bathroom model"""
    id: Optional[int] = None
    building_name: BuildingEnum
    floor_number: int
    bathroom_gender: GenderEnum
    avg_rating: float = 0.0
    is_low_supply: bool = False
    reviews: List['ReviewCreate'] = []

    class Config:
        from_attributes = True
