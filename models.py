from typing import Optional
from pydantic import BaseModel
from firedantic import Model


class Geolocation(BaseModel):
    latitude: float
    longitude: float


class Reservation(BaseModel):
    restaurant_id: str
    user_id: str
    date: str
    time: str
    party_size: int


class Review(BaseModel):
    wallet_address: str
    restaurant_id: str
    rating: float
    text: str


class Restaurant(Model):
    __collection__ = "restaurants"
    name: str
    url: str
    rating: float
    cuisine: str
    address: str
    geolocation: Geolocation
    reviews: list[Review] = []


class User(Model):
    __collection__ = "users"
    wallet_address: str
    world_id: Optional[str] = None
    visited_restaurants: list[Restaurant] = []
    reviews: list[Review] = []
