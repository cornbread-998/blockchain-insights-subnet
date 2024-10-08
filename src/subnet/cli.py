import asyncio
import signal
import sys
import threading
from datetime import datetime

from communex._common import get_node_url
from communex.client import CommuneClient
from communex.compat.key import classic_load_key
from loguru import logger

from src.subnet.validator.database.models.challenge_balance_tracking import ChallengeBalanceTrackingManager
from src.subnet.validator.database.models.challenge_funds_flow import ChallengeFundsFlowManager
from src.subnet.protocol.blockchain import get_networks
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.validator.database.models.miner_receipts import MinerReceiptManager
from src.subnet.validator.database.models.validation_prompt import ValidationPromptManager
from src.subnet.validator.database.models.validation_prompt_response import ValidationPromptResponseManager
from src.subnet.validator.database.session_manager import DatabaseSessionManager, run_migrations
from src.subnet.validator.llm.factory import LLMFactory
from src.subnet.validator.weights_storage import WeightsStorage
from src.subnet.validator._config import ValidatorSettings, load_environment
from src.subnet.validator.validator import Validator
from src.subnet.validator.llm_prompt_utility import main as llm_main
from src.subnet.validator.challenge_utility import main as funds_flow_main, main as balance_tracking_main



class PromptGeneratorThread(threading.Thread):
    def __init__(self, settings, environment, network, frequency, threshold, terminate_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = settings
        self.environment = environment
        self.network = network
        self.frequency = frequency
        self.threshold = threshold
        self.terminate_event = terminate_event

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(llm_main(self.settings, self.network, self.frequency, self.threshold, self.terminate_event))
        finally:
            loop.close()


class FundsFlowChallengeGeneratorThread(threading.Thread):
    def __init__(self, settings, environment, network, frequency, threshold, terminate_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = settings
        self.environment = environment
        self.network = network
        self.model = 'funds_flow'
        self.frequency = frequency
        self.threshold = threshold
        self.terminate_event = terminate_event

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(funds_flow_main(self.settings, self.network, self.model, self.frequency, self.threshold, self.terminate_event))
        finally:
            loop.close()


class BalanceTrackingChallengeGeneratorThread(threading.Thread):
    def __init__(self, settings, environment, network, frequency, threshold, terminate_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = settings
        self.environment = environment
        self.network = network
        self.model = 'balance_tracking'
        self.frequency = frequency
        self.threshold = threshold
        self.terminate_event = terminate_event

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(balance_tracking_main(self.settings, self.network, self.model, self.frequency, self.threshold, self.terminate_event))
        finally:
            loop.close()

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python -m subnet.cli <environment>")
        sys.exit(1)

    environment = sys.argv[1]
    load_environment(environment)

    settings = ValidatorSettings()
    keypair = classic_load_key(settings.VALIDATOR_KEY)

    def patch_record(record):
        record["extra"]["validator_key"] = keypair.ss58_address
        record["extra"]["service"] = 'validator'
        record["extra"]["timestamp"] = datetime.utcnow().isoformat()
        record["extra"]["level"] = record['level'].name

        return True

    logger.remove()
    logger.add(
        "../logs/validator.log",
        rotation="500 MB",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}",
        level="DEBUG",
        filter=patch_record
    )

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <blue>{message}</blue> | {extra}",
        level="DEBUG",
        filter=patch_record,
    )

    c_client = CommuneClient(get_node_url(use_testnet=(environment == 'testnet')))
    weights_storage = WeightsStorage(settings.WEIGHTS_FILE_NAME)

    session_manager = DatabaseSessionManager()
    session_manager.init(settings.DATABASE_URL)

    run_migrations()

    miner_discovery_manager = MinerDiscoveryManager(session_manager)
    miner_receipt_manager = MinerReceiptManager(session_manager)
    validation_prompt_manager = ValidationPromptManager(session_manager)
    validation_prompt_response_manager = ValidationPromptResponseManager(session_manager)
    challenge_funds_flow_manager = ChallengeFundsFlowManager(session_manager)
    challenge_balance_tracking_manager = ChallengeBalanceTrackingManager(session_manager)
    llm = LLMFactory.create_llm(settings)

    validator = Validator(
        keypair,
        settings.NET_UID,
        c_client,
        weights_storage,
        miner_discovery_manager,
        validation_prompt_manager,
        validation_prompt_response_manager,
        challenge_funds_flow_manager,
        challenge_balance_tracking_manager,
        miner_receipt_manager,
        llm,
        query_timeout=settings.QUERY_TIMEOUT,
        challenge_timeout=settings.CHALLENGE_TIMEOUT,
        llm_query_timeout=settings.LLM_QUERY_TIMEOUT
    )


    def shutdown_handler(signal_num, frame):
        logger.info("Received shutdown signal, stopping...")
        validator.terminate_event.set()
        logger.debug("Shutdown handler finished")

    # Signal handling for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    networks = get_networks()
    prompt_generator_threads = []
    funds_flow_challenge_generator_threads = []
    balance_tracking_challenge_generator_threads = []

    # Launch Prompt Generator Threads
    for network in networks:
        prompt_generator_thread = PromptGeneratorThread(
            settings=settings,
            environment=environment,
            network=network,
            frequency=settings.PROMPT_FREQUENCY,
            threshold=settings.PROMPT_THRESHOLD,
            terminate_event=validator.terminate_event
        )
        prompt_generator_threads.append(prompt_generator_thread)
        prompt_generator_thread.start()

    # Launch Funds Flow Challenge Generator Threads
    for network in networks:
        funds_flow_thread = FundsFlowChallengeGeneratorThread(
            settings=settings,
            environment=environment,
            network=network,
            frequency=settings.FUNDS_FLOW_CHALLENGE_FREQUENCY,
            threshold=settings.FUNDS_FLOW_CHALLENGE_THRESHOLD,
            terminate_event=validator.terminate_event
        )
        funds_flow_challenge_generator_threads.append(funds_flow_thread)
        funds_flow_thread.start()

    # Launch Balance Tracking Challenge Generator Threads
    for network in networks:
        balance_tracking_thread = BalanceTrackingChallengeGeneratorThread(
            settings=settings,
            environment=environment,
            network=network,
            frequency=settings.BALANCE_TRACKING_CHALLENGE_FREQUENCY,
            threshold=settings.BALANCE_TRACKING_CHALLENGE_THRESHOLD,
            terminate_event=validator.terminate_event
        )
        balance_tracking_challenge_generator_threads.append(balance_tracking_thread)
        balance_tracking_thread.start()

    try:
        asyncio.run(validator.validation_loop(settings))
    except KeyboardInterrupt:
        logger.info("Validator loop interrupted")

    # Wait for all threads to finish
    for thread in prompt_generator_threads + funds_flow_challenge_generator_threads + balance_tracking_challenge_generator_threads:
        thread.join()
        logger.info(f"Generator for {thread.network} ({getattr(thread, 'model', 'prompt')}) stopped successfully.")

    logger.info("Validator, Prompt Generator, and Challenge Generator stopped successfully.")
