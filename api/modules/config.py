from dotenv import load_dotenv
import os

load_dotenv()

get_env_var = lambda var_name: os.getenv(var_name)