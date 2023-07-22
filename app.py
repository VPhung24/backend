import csv
from http.client import HTTPException
from fastapi import FastAPI

from models import Restaurant, Review, User
from firedantic import configure
from google.cloud.firestore import Client

client = Client()

configure(client, prefix="snacks-")

app = FastAPI()


@app.get("/restaurants")
async def get_restaurants() -> list[Restaurant]:
    return Restaurant.find()


@app.post("/reviews/new")
async def post_review(
    wallet_address: str, restaurant_id: str, rating: float, text: str
) -> None:
    user = User.find_one({"wallet_address": wallet_address})
    if restaurant_id not in user.visited_restaurants:
        raise HTTPException("User has not visited this restaurant")
    review = Review(
        wallet_address=wallet_address,
        restaurant_id=restaurant_id,
        rating=rating,
        text=text,
    )
    restaurant = Restaurant.find_one({"_id": restaurant_id})
    restaurant.reviews.append(review)
    restaurant.save()
    user.reviews.append(review)
    user.save()


@app.get("restaurants/{restaurant_id}/reviews")
async def get_reviews(restaurant_id: str) -> list[Review]:
    return Restaurant.find_one({"_id": restaurant_id}).reviews


@app.get("users/{wallet_address}/reviews")
async def get_reviews(wallet_address: str) -> list[Review]:
    return User.find_one({"wallet_address": wallet_address}).reviews


@app.post("/users/new")
async def create_user(wallet_address: str) -> None:
    User(wallet_address=wallet_address).save()


@app.get("/users/{wallet_address}")
async def get_user(wallet_address: str) -> User:
    return User.find_one({"wallet_address": wallet_address})


@app.post("restaurants/{restaurant_id}/checkin")
async def checkin(restaurant_id: str, wallet_address: str) -> None:
    user = User.find_one({"wallet_address": wallet_address})
    user.visited_restaurants.append(restaurant_id)
    user.save()
    # TODO emit a POAP


@app.get("/.well-known/apple-app-site-association")
def apple_app_site_association():
    return {
        "applinks": {
            "details": [{"appIDs": ["xyz.parisbeepboop.LeSnacks"], "components": []}]
        },
        "webcredentials": {"apps": ["xyz.parisbeepboop.LeSnacks"]},
    }
