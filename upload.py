import csv

from models import Restaurant

from google.cloud.firestore import Client
from firedantic import configure

client = Client()

configure(client, prefix="snacks-")

with open("restaurant_data.csv", "r") as f:
    reader = csv.reader(f.readlines())
    for line in reader:
        name, url, rating, cuisine, address, latitude, longitude, poap_uri = line
        Restaurant(name=name, url=url, rating=float(rating), cuisine=cuisine, address=address, geolocation={"latitude": latitude, "longitude": longitude}, poap_uri=poap_uri).save()