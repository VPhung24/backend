from pydantic import BaseModel


class Geolocation(BaseModel):
    latitude: float
    longitude: float


class Restaurant(BaseModel):
    name: str
    url: str
    rating: float
    cuisine: str
    address: str
    # geolocation: Geolocation
