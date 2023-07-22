from http.client import HTTPException
from dotenv import load_dotenv
from fastapi import FastAPI
from web3 import Web3

from models import Restaurant, Review, User
from firedantic import configure
from google.cloud.firestore import Client
import os
from abi import tummy_abi

load_dotenv()
client = Client()

configure(client, prefix="snacks-")

app = FastAPI()
w3 = Web3(Web3.HTTPProvider(os.environ["RPC_HTTP_URL"]))
private_key = os.environ["DEPLOYER_PRIVATE_KEY"]
tummy_contract_instance = w3.eth.contract(
    address=os.environ["TUMMY_NFT_ADDRESS"], abi=tummy_abi
)


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
async def create_user(wallet_address: str) -> str:
    User(wallet_address=wallet_address).save()
    # When a new user is created, we need to mint them a Tummy NFT
    nonce = w3.eth.get_transaction_count('0xc4e1bf51752b4D55ef81FcA2334404245A07680c')
    tx = tummy_contract_instance.functions.mintNFT(wallet_address, "test").buildTransaction(
        {
            "chainId": 5,
            "gas": 1000000,
            "gasPrice": w3.toWei("5", "gwei"),
            "nonce": nonce,
        }
    )
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash

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
