# from pydantic import BaseModel, Field
# from typing import Optional, List
# from datetime import datetime


# class ReviewBase(BaseModel):
#     cleanliness: int = Field(..., ge=1, le=10)
#     ambience: int = Field(..., ge=1, le=10)
#     sink_pressure: int = Field(..., ge=1, le=10)
#     paper_towel_type: str
#     toilet_paper_type: str
#     comment: str


# class ReviewCreate(ReviewBase):
#     user_id: str


# class Review(ReviewBase):
#     id: str
#     user_id: str
#     created_at: datetime


# class Bathroom(BaseModel):
#     id: str
#     building: str
#     floor: int
#     gender: str
#     avg_rating: float = 0.0
#     is_low_supply: bool = False
#     reviews: List[Review] = []
