from dotenv import load_dotenv
from binbot import Config, run_loop

dotenv_path = ".env"

load_dotenv(dotenv_path)

cfg = Config()
run_loop(cfg)