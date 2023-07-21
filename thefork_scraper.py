from dataclasses import dataclass
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By


@dataclass
class Restaurant:
    name: str
    url: str
    rating: float
    cuisine: str
    address: str

URL = "https://www.thefork.com/search?cityId=415144"
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--incognito')
# Adding argument to disable the AutomationControlled flag 
options.add_argument("--disable-blink-features=AutomationControlled") 
# Exclude the collection of enable-automation switches 
options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
# Turn-off userAutomationExtension 
options.add_experimental_option("useAutomationExtension", False) 
# options.add_experimental_option("detach", True)
# options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})") 
# page_source = driver.page_source
# print(page_source)

useragentarray = [ 
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36", 
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36", 
]
restaurants = []
print("name,url,rating,cuisine,address")
for i in range(2):
    # Setting user agent iteratively as Chrome 108 and 107
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": useragentarray[i % 2]}) 
    driver.get(f"{URL}&p={i+1}")
    WebDriverWait(driver, timeout=60).until(lambda d: d.find_element(By.ID,"srp-filters-container"))
    restaurants_elems = driver.find_elements(By.XPATH, "//div[contains(@class, 'content')]")
    for restaurant in restaurants_elems:
        try:
            name = restaurant.find_element(By.XPATH, ".//h2/a").text
            url = restaurant.find_element(By.XPATH, ".//h2/a").get_attribute("href")
            cuisine = restaurant.find_element(By.XPATH, ".//span[@data-test='search-restaurant-tags-DEFAULT']").text
            rating = restaurant.find_element(By.XPATH, ".//div/span/span").text
            address = restaurant.find_element(By.XPATH, "./div[2]//p").text
            print(f'"{name}",{url},{rating},{cuisine},"{address}"')
            # restaurants.append(Restaurant(name, url, rating, cuisine, address))
        except:
            continue
    time.sleep(10)
    # print(f"Page {i+1} loaded")

# print(*restaurants, sep="\n")
driver.close()