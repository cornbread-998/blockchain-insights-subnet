import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


def load_environment(env: str):
    if env == 'mainnet':
        dotenv_path = os.path.abspath('../env/.env.validator.mainnet')
    elif env == 'testnet':
        dotenv_path = os.path.abspath('../env/.env.validator.testnet')
    else:
        raise ValueError(f"Unknown environment: {env}")

    load_dotenv(dotenv_path=dotenv_path)


class ValidatorSettings(BaseSettings):
    ITERATION_INTERVAL: int
    MAX_ALLOWED_WEIGHTS: int
    NET_UID: int
    VALIDATOR_KEY: str

    PORT: int = 9900
    WORKERS: int = 4

    WEIGHTS_FILE_NAME: str = 'weights.pkl'
    DATABASE_URL: str
    API_RATE_LIMIT: int
    REDIS_URL: str

    LLM_QUERY_TIMEOUT: int  # llm query timeout (organic prompt)
    QUERY_TIMEOUT: int   # cross check query timeout
    CHALLENGE_TIMEOUT: int  # challenge and llm challenge time

    LLM_API_KEY: str
    LLM_TYPE: str

    PROMPT_FREQUENCY: int
    PROMPT_THRESHOLD: int

    FUNDS_FLOW_CHALLENGE_FREQUENCY: int
    FUNDS_FLOW_CHALLENGE_THRESHOLD: int
    BALANCE_TRACKING_CHALLENGE_FREQUENCY: int
    BALANCE_TRACKING_CHALLENGE_THRESHOLD: int

    class Config:
        extra = 'ignore'
