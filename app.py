from http.client import HTTPException
import random
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
proof_of_snack_contract_instance = w3.eth.contract(
    address=os.environ["PROOF_OF_SNACK_NFT_ADDRESS"], abi=tummy_abi
)
erc6551_registry_instance = w3.eth.contract(
    address=os.environ["ERC6551_REGISTRY_ADDRESS"], abi=erc6551_registry_abi
)
erc6551_account_instance = w3.eth.contract(
    address=os.environ["ERC6551_ACCOUNT_ADDRESS"], abi=erc6551_account_abi
)


BASE_TUMMIES_URIS = [
    "Qmb6xm57jyCZk2VxmU3izsrQ6aW9KCtuangPmvcQwQrADD/00",
    "Qmb6xm57jyCZk2VxmU3izsrQ6aW9KCtuangPmvcQwQrADD/10",
]


@app.get("/restaurants")
async def get_restaurants() -> list[Restaurant]:
    return Restaurant.find()


@app.get("/restaurants/{restaurant_id}")
async def get_restaurant(restaurant_id: str) -> Restaurant:
    return Restaurant.get_by_doc_id(restaurant_id)


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
    restaurant = Restaurant.get_by_doc_id(restaurant_id)
    restaurant.reviews.append(review)
    restaurant.save()
    user.reviews.append(review)
    user.save()


@app.get("/restaurants/{restaurant_id}/reviews")
async def get_reviews(restaurant_id: str) -> list[Review]:
    return Restaurant.get_by_doc_id(restaurant_id).reviews


@app.get("/users/{wallet_address}/reviews")
async def get_reviews(wallet_address: str) -> list[Review]:
    # Ensure address is checksummed
    wallet_address = w3.to_checksum_address(wallet_address)
    return User.find_one({"wallet_address": wallet_address}).reviews


@app.get("/users/{wallet_address}")
async def get_user(wallet_address: str, background_tasks: BackgroundTasks) -> User:
    # Ensure address is checksummed
    wallet_address = w3.to_checksum_address(wallet_address)
    try:
        return User.find_one({"wallet_address": wallet_address})
    except Exception:
        # We need to create a new user
        user = User(wallet_address=wallet_address)
        # When a new user is created, we need to mint them a Tummy NFT
        # First, choose a random base Tummy URI
        tummy_uri = random.choice(BASE_TUMMIES_URIS)
        user.tummy_token_id = tummy_contract_instance.functions._tokenIds().call()
        user.profile_picture_url = f"https://ipfs.io/ipfs/{tummy_uri}.png"
        user.save()
        background_tasks.add_task(
            mint_and_create_6551,
            user,
            tummy_uri,
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


def mint_proof_of_snack_and_transfer_to_6551_and_evolve(
    user: User, restaurant_id: str
) -> None:
    # We mint a ProofOfSnack NFT and transfer it to the Tummy ERC-6551
    nonce = w3.eth.get_transaction_count(os.environ["DEPLOYER_ADDRESS"])
    # Get the POAP URI from the restaurant
    print(f"Fetching restaurant {restaurant_id}")
    restaurant = Restaurant.get_by_doc_id(restaurant_id)
    metadata_uri = restaurant.poap_uri
    tx = proof_of_snack_contract_instance.functions.mintNFT(
        user.tummy_6551_account,
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
    print("ProofOfSnack NFT minted")
    # We evolve the user's Tummy NFT, this is done by incrementing the IPFS URI by 1 and replacing it
    # We want to get Qmb6xm57jyCZk2VxmU3izsrQ6aW9KCtuangPmvcQwQrADD/10.png from https://ipfs.io/ipfs/Qmb6xm57jyCZk2VxmU3izsrQ6aW9KCtuangPmvcQwQrADD/10.png
    metadata_uri = user.profile_picture_url.split("ipfs.io/ipfs/")[1].split(".png")[0]
    # Increment the last digit
    last_digit = metadata_uri[-1]
    new_last_digit = str(int(last_digit) + 1)
    metadata_uri = metadata_uri[:-1] + new_last_digit
    # Append .png
    metadata_uri = "https://ipfs.io/ipfs/" + metadata_uri + ".png"
    print(f"New metadata URI: {metadata_uri}")
    nonce = w3.eth.get_transaction_count(os.environ["DEPLOYER_ADDRESS"])
    tx = tummy_contract_instance.functions.updateMetadataURI(
        user.tummy_token_id,
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
    print("Tummy NFT evolved")
    user.profile_picture_url = metadata_uri
    user.save()


@app.post("/restaurants/{restaurant_id}/checkin")
async def checkin(
    restaurant_id: str, wallet_address: str, background_tasks: BackgroundTasks
) -> None:
    # Ensure address is checksummed
    wallet_address = w3.to_checksum_address(wallet_address)
    user = User.find_one({"wallet_address": wallet_address})
    user.visited_restaurants.append(restaurant_id)
    user.save()
    background_tasks.add_task(
        mint_proof_of_snack_and_transfer_to_6551_and_evolve,
        user,
        restaurant_id,
    )
    # We also need to evolve the user's Tummy NFT

    return 200


@app.get("/proof_of_snacks/{wallet_address}")
async def get_proof_of_snacks(wallet_address: str) -> list[Restaurant]:
    # Ensure address is checksummed
    wallet_address = w3.to_checksum_address(wallet_address)
    user = User.find_one({"wallet_address": wallet_address})
    restaurants = user.visited_restaurants
    # Filter only restaurants with POAPs
    restaurants = [
        Restaurant.get_by_doc_id(restaurant)
        for restaurant in restaurants
        if Restaurant.get_by_doc_id(restaurant).poap_uri != ""
    ]
    return restaurants

@app.get("/.well-known/apple-app-site-association")
def apple_app_site_association():
    return {
        "applinks": {
            "details": [{"appIDs": ["xyz.parisbeepboop.LeSnacks"], "components": []}]
        },
        "webcredentials": {"apps": ["xyz.parisbeepboop.LeSnacks"]},
    }
