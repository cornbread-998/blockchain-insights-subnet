import random
from src.subnet.validator.blockchain.common.base_prompt_generator import BasePromptGenerator
from src.subnet.validator.database.models.validation_prompt import ValidationPromptManager
from src.subnet.validator.llm.base_llm import BaseLLM
from loguru import logger


class PromptGenerator(BasePromptGenerator):
    PROMPT_TEMPLATES = [
        "What is the total amount of the transaction with txid {txid} in block {block}?",
        "List all transactions in block {block} and their respective amounts.",
        "Calculate the gas fees for all transactions in block {block}.",
        "Retrieve the details of the transaction with txid {txid} in block {block}.",
        "Provide the total number of transactions in block {block} and identify the largest transaction by gas fees.",
        "Determine the gas fees for the transaction with txid {txid} in block {block}.",
        "Identify all addresses involved in the transaction with txid {txid} in block {block}."
    ]

    def __init__(self, settings, llm: BaseLLM):
        super().__init__(settings)
        #self.node = EthereumNode()  # Ethereum-specific node (commented as per your instruction)
        self.llm = llm  # LLM instance passed to use for prompt generation
        self.network = 'ethereum'  # Store the network as a member variable

    async def generate_and_store(self, validation_prompt_manager: ValidationPromptManager, threshold: int):
        # Retrieve block details
        last_block_height = self.node.get_current_block_height() - 6
        random_block_height = random.randint(0, last_block_height)
        tx_id, block_data = self.node.get_random_txid_from_block(random_block_height)
        logger.debug(f"Random Txid: {tx_id}")

        # Randomly select a prompt template
        selected_template = random.choice(self.PROMPT_TEMPLATES)

        # Use LLM to build the final prompt
        prompt = self.llm.build_prompt_from_txid_and_block(tx_id, random_block_height, self.network, selected_template)
        logger.debug(f"Generated Challenge Prompt: {prompt}")

        # Check if the current prompt count has exceeded the threshold
        current_prompt_count = await validation_prompt_manager.get_prompt_count(self.network)
        if current_prompt_count >= threshold:
            await validation_prompt_manager.try_delete_oldest_prompt(self.network)

        # Store the prompt and block data in the database
        await validation_prompt_manager.store_prompt(prompt, block_data, self.network)
        logger.info(f"Ethereum prompt stored in the database successfully.")
