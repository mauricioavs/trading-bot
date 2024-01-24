from os import getenv
from dotenv import load_dotenv


load_dotenv()

TEST_API_KEY = getenv("TEST_API_KEY")

TEST_SECRET_KEY = getenv("TEST_SECRET_KEY")

API_KEY = getenv("API_KEY")

SECRET_KEY = getenv("API_KEY")
