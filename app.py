from http.client import HTTPException
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI
from web3 import Web3

from models import Restaurant, Review, User
from firedantic import configure
from google.cloud.firestore import Client
import os
from abi import tummy_abi, erc6551_registry_abi, erc6551_account_abi

load_dotenv()
client = Client()

configure(client, prefix="snacks-")

app = FastAPI()
w3 = Web3(Web3.HTTPProvider(os.environ["RPC_HTTP_URL"]))
private_key = os.environ["DEPLOYER_PRIVATE_KEY"]
tummy_contract_instance = w3.eth.contract(
    address=os.environ["TUMMY_NFT_ADDRESS"], abi=tummy_abi
)
erc6551_registry_instance = w3.eth.contract(
    address=os.environ["ERC6551_REGISTRY_ADDRESS"], abi=erc6551_registry_abi
)
erc6551_account_instance = w3.eth.contract(
    address=os.environ["ERC6551_ACCOUNT_ADDRESS"], abi=erc6551_account_abi
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


@app.get("/users/{wallet_address}")
async def get_user(wallet_address: str, background_tasks: BackgroundTasks) -> User:
    try:
        return User.find_one({"wallet_address": wallet_address})
    except Exception:
        # We need to create a new user
        user = User(wallet_address=wallet_address)
        # When a new user is created, we need to mint them a Tummy NFT
        user.tummy_token_id = tummy_contract_instance.functions._tokenIds().call()
        user.profile_picture_url = f"https://ipfs.io/ipfs/bafybeifv3aptenmwi5zup2dkir7yk5aq4lqf7y32rdowitziozj4gwb5iy/604.png"
        user.save()
        background_tasks.add_task(
            mint_and_create_6551,
            user,
            "bafybeifv3aptenmwi5zup2dkir7yk5aq4lqf7y32rdowitziozj4gwb5iy/604",
        )
        return user


def mint_and_create_6551(user: User, metadata_uri: str) -> None:
    # When a new user is created, we need to mint them a Tummy NFT and then create an ERC-6551 for the NFT
    nonce = w3.eth.get_transaction_count(os.environ["DEPLOYER_ADDRESS"])
    tx = tummy_contract_instance.functions.mintNFT(
        user.wallet_address,
        metadata_uri,
    ).build_transaction(
        {
            "chainId": 5,
            "gas": 1000000,
            "maxFeePerGas": w3.to_wei("20", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("10", "gwei"),
            "nonce": nonce,
        }
    )
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    _ = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Tummy NFT minted")
    # Now we need to create an ERC-6551 for the NFT
    nonce = w3.eth.get_transaction_count(os.environ["DEPLOYER_ADDRESS"])
    tx = erc6551_registry_instance.functions.createAccount(
        erc6551_account_instance.address,
        5,
        tummy_contract_instance.address,
        user.tummy_token_id,
        1,
        "0x",
    ).build_transaction(
        {
            "chainId": 5,
            "gas": 1000000,
            "maxFeePerGas": w3.to_wei("20", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("10", "gwei"),
            "nonce": nonce,
        }
    )
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    _ = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("ERC-6551 created")
    # Get the address of the ERC-6551 account
    user.tummy_6551_account = erc6551_registry_instance.functions.account(
        erc6551_account_instance.address,
        5,
        tummy_contract_instance.address,
        user.tummy_token_id,
        1,
    ).call()
    user.save()
    print("ERC-6551 account address saved")
    


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
