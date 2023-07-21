import csv
from fastapi import FastAPI

from models import Restaurant

app = FastAPI()

restaurants = []
with open("restaurant_data.csv", "r") as f:
    reader = csv.reader(f.readlines())
    for line in reader:
        name, url, rating, cuisine, address = line
        restaurants.append(Restaurant(name=name, url=url, rating=float(rating), cuisine=cuisine, address=address))

@app.get("/restaurants")
async def get_restaurants() -> list[Restaurant]:
    return restaurants
