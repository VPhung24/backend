import csv
from fastapi import FastAPI

from models import Restaurant, Review
from firedantic import configure
from google.cloud.firestore import Client

client = Client()

configure(client, prefix="snacks-")

app = FastAPI()


@app.get("/restaurants")
async def get_restaurants() -> list[Restaurant]:
    return Restaurant.find()


@app.post("/post_review")
async def post_review(
    user_id: str, restaurant_id: str, rating: float, text: str
) -> None:
    review = Review(
        user_id=user_id, restaurant_id=restaurant_id, rating=rating, text=text
    )
    Restaurant.find_one({"_id": restaurant_id}).reviews.append(review)


@app.get("/reviews")
async def get_reviews(restaurant_id: str) -> list[Review]:
    Restaurant.find_one({"_id": restaurant_id}).reviews
