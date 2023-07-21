import csv
from fastapi import FastAPI

from models import Restaurant
from geopy.geocoders import Nominatim

app = FastAPI()

restaurants = []
with open("restaurant_data.csv", "r") as f:
    reader = csv.reader(f.readlines())
    for line in reader:
        name, url, rating, cuisine, address, latitude, longitude = line
        restaurants.append(Restaurant(name=name, url=url, rating=float(rating), cuisine=cuisine, address=address, geolocation={"latitude": latitude, "longitude": longitude}))

@app.get("/restaurants")
async def get_restaurants() -> list[Restaurant]:
    return restaurants
