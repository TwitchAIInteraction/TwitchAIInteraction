import asyncio
import os
import re
import sys
import time
import logging
from typing import List
import functools

import openai
from openai import OpenAIError, AsyncOpenAI  # OpenAIError: For handling API exceptions; AsyncOpenAI: Asynchronous client for non-blocking operations.
from twitchio.ext import commands  # TwitchIO framework for bot commands and event handling.
from elevenlabs.client import ElevenLabs  # ElevenLabs client for voice synthesis.
from elevenlabs import play  # Function to play audio generated by ElevenLabs.
from dotenv import load_dotenv  # Loads environment variables from a .env file.

# =========================
# Module-Level Constants
# =========================

# Pre-compile the regex pattern for cheer emotes
CHEER_PATTERN = re.compile(
    r'(BibleThump\d+|cheerwhal\d+|Corgo\d+|uni\d+|ShowLove\d+|Party\d+|'
    r'SeemsGood\d+|Pride\d+|Kappa\d+|cheer\d+|FrankerZ\d+|HeyGuys\d+|'
    r'DansGame\d+|EleGiggle\d+|TriHard\d+|Kreygasm\d+|4Head\d+|SwiftRage\d+|'
    r'NotLikeThis\d+|FailFish\d+|VoHiYo\d+|PJSalt\d+|MrDestructoid\d+|'
    r'bday\d+|RIPCheer\d+|Shamrock\d)', re.IGNORECASE
)

# =========================
# Configuration and Logging
# =========================

# Configure the logging module to output informational and error messages.
logging.basicConfig(
    level=logging.INFO,  # Use INFO level for production; switch to DEBUG for more granular logs during development.
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler()  # Outputs log messages to the standard output stream.
    ]
)
logger = logging.getLogger(__name__)

# Define the configuration file path for environment variables.
CONFIG_FILE = '.env'

# =====================
# Utility Functions
# =====================

def prompt_yes_no(question: str) -> bool:
    """
    Prompt the user with a yes/no question until a valid response is received.

    Args:
        question (str): The question to present to the user.
    
    Returns:
        bool: True if the user answers 'yes', False if 'no'.
    """
    while True:
        response = input(f"{question} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please respond with 'y' or 'n'.")

def setup_configuration():
    """
    Collects configuration inputs from the user and writes them to the .env file.
    This interactive setup prompts for Twitch, OpenAI, ElevenLabs, and file system parameters,
    then saves them in a plaintext configuration file for subsequent runs.
    """
    config = {}
    print("=== Twitch Bot Configuration Setup ===")

    # Collect Twitch-related configuration details.
    config['TWITCH_CHANNEL'] = input("Enter your Twitch channel name: ").strip()
    config['TWITCH_OAUTH_TOKEN'] = input("Enter your Twitch OAuth token: ").strip()
    config['TWITCH_BOT_NICK'] = input("Enter your Twitch bot nickname (default: Bot): ").strip() or "Bot"

    # Collect API keys for OpenAI and ElevenLabs.
    config['OPENAI_API_KEY'] = input("Enter your OpenAI API key: ").strip()
    config['ELEVENLABS_API_KEY'] = input("Enter your ElevenLabs API key: ").strip()

    # Collect ElevenLabs voice configuration.
    voice_id_input = input("Enter ElevenLabs voice ID (default: use 'default_voice'): ").strip()
    config['VOICE_ID'] = voice_id_input if voice_id_input else "default_voice"
    config['MODEL_VERSION'] = input("Enter ElevenLabs model version (default: eleven_multilingual_v2): ").strip() or "eleven_multilingual_v2"

    # Collect file system configuration for prompt and chat logs.
    base_path_input = input("Enter base directory path (default: c:\\Temp): ").strip()
    config['BASE_PATH'] = base_path_input if base_path_input else "c:\\Temp"
    config['OPENAI_PROMPT_FILE'] = input("Enter OpenAI prompt filename (default: prompt.txt): ").strip() or "prompt.txt"
    config['CHAT_LOG_FILE'] = input("Enter chat log filename (default: chat.txt): ").strip() or "chat.txt"

    # Bot behavior settings: bits threshold and timeout duration.
    bit_threshold_input = input("Enter bits threshold to trigger AI response (default: 20): ").strip()
    config['BIT_THRESHOLD'] = bit_threshold_input if bit_threshold_input else "20"

    timeout_duration_input = input("Enter timeout duration in seconds (default: 15): ").strip()
    config['TIMEOUT_DURATION'] = timeout_duration_input if timeout_duration_input else "15"

    # Option for enabling chat logging.
    chat_flag_input = input("Enable chat logging? (y/n, default: n): ").strip().lower()
    config['CHAT_FLAG'] = "True" if chat_flag_input in ['y', 'yes'] else "False"

    # Collect banned words to filter from chat messages.
    print("Enter banned words separated by commas (leave empty for none):")
    banned_words_input = input().strip()
    config['BANNED_WORDS'] = banned_words_input if banned_words_input else ""

    # Optional: Custom prompt template for generating AI responses.
    prompt_template_input = input("Enter prompt template (leave empty to use default): ").strip()
    if prompt_template_input:
        config['PROMPT_TEMPLATE'] = prompt_template_input

    # Write the collected configuration to the .env file.
    try:
        with open(CONFIG_FILE, 'w') as env_file:
            for key, value in config.items():
                # Save each configuration variable as a key-value pair.
                env_file.write(f"{key}='{value}'\n")
        print(f"Configuration saved to {CONFIG_FILE}.\n")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        sys.exit(1)

def load_configuration():
    """
    Loads configuration variables from the .env file and environment.
    Performs type conversions and provides default values where necessary.

    Returns:
        dict: A dictionary containing all configuration variables.
    """
    load_dotenv(CONFIG_FILE)

    # Retrieve Twitch and API configuration from environment variables.
    config = {}
    config['TWITCH_CHANNEL'] = os.getenv('TWITCH_CHANNEL')
    config['TWITCH_OAUTH_TOKEN'] = os.getenv('TWITCH_OAUTH_TOKEN')
    config['TWITCH_BOT_NICK'] = os.getenv('TWITCH_BOT_NICK', 'Bot')

    config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    config['ELEVENLABS_API_KEY'] = os.getenv('ELEVENLABS_API_KEY')

    # Retrieve ElevenLabs configuration with defaults.
    config['VOICE_ID'] = os.getenv('VOICE_ID', 'default_voice')
    config['MODEL_VERSION'] = os.getenv('MODEL_VERSION', 'eleven_multilingual_v2')

    # Retrieve file system paths and file names.
    config['BASE_PATH'] = os.getenv('BASE_PATH', 'c:\\Temp')
    config['OPENAI_PROMPT_FILE'] = os.getenv('OPENAI_PROMPT_FILE', 'prompt.txt')
    config['CHAT_LOG_FILE'] = os.getenv('CHAT_LOG_FILE', 'chat.txt')

    # Convert BIT_THRESHOLD to an integer value; fallback to default if conversion fails.
    try:
        config['BIT_THRESHOLD'] = int(os.getenv('BIT_THRESHOLD', '20'))
    except ValueError:
        logger.error("Invalid BIT_THRESHOLD. It should be an integer.")
        config['BIT_THRESHOLD'] = 20  # Default value

    # Convert TIMEOUT_DURATION to an integer value; fallback to default if conversion fails.
    try:
        config['TIMEOUT_DURATION'] = int(os.getenv('TIMEOUT_DURATION', '15'))
    except ValueError:
        logger.error("Invalid TIMEOUT_DURATION. It should be an integer.")
        config['TIMEOUT_DURATION'] = 15  # Default value

    # Convert CHAT_FLAG string to a boolean.
    config['CHAT_FLAG'] = os.getenv('CHAT_FLAG', 'False') == 'True'

    # Parse banned words into a list for filtering.
    banned_words_str = os.getenv('BANNED_WORDS', '')
    config['BANNED_WORDS'] = [word.strip() for word in banned_words_str.split(',')] if banned_words_str else []

    # Set a default prompt template if one is not provided.
    config['PROMPT_TEMPLATE'] = os.getenv('PROMPT_TEMPLATE',
        f'Here is the latest message from Twitch chat: "{{message}}". '
        f'Phonetically space out their username then acknowledge them and respond '
        f'to their message in 1 or 2 sentences. Speak naturally as {config["TWITCH_CHANNEL"]}. '
        "Don't forget the sass."
    )

    # Set the default OpenAI model.
    config['OPENAI_MODEL'] = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    return config

def filter_message(text: str, banned_words: List[str]) -> str:
    """
    Filters and sanitizes an incoming message by removing cheer prefixes and banned words,
    then truncates the result to a maximum of 130 characters.

    Args:
        text (str): The original message text.
        banned_words (List[str]): A list of words to be censored.
    
    Returns:
        str: The sanitized and truncated message.
    """
    # Remove cheer prefixes (e.g., cheer1000) from the message.
    text = re.sub(r'cheer\d+\s+', '', text, flags=re.I)
    # Iterate over banned words, replacing each occurrence with asterisks.
    for word in banned_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub('*' * len(word), text)
    # Truncate the filtered message to 130 characters.
    return text[:130]

def read_system_prompt(DIR_PATH: str, OPENAI_PROMPT_FILE: str) -> str:
    """
    Reads the system prompt from a specified file.
    If the file does not exist, logs an error and returns a default error message.

    Args:
        DIR_PATH (str): The directory where the prompt file is located.
        OPENAI_PROMPT_FILE (str): The name of the prompt file.
    
    Returns:
        str: The content of the prompt file, or an error message if the file is not found.
    """
    prompt_path = os.path.join(DIR_PATH, OPENAI_PROMPT_FILE)
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        logger.error(f"Prompt file not found at {prompt_path}.")
        return "TELL EVERYBODY THE PROMPT IS BROKEN"

# =====================
# Twitch Bot Class
# =====================

class TwitchBot(commands.Bot):
    """
    A Twitch bot class that integrates Twitch chat interactions with AI-generated responses and voice synthesis.
    Inherits from twitchio.ext.commands.Bot for handling Twitch events.
    """

    def __init__(self, selected_voice, eleven_client, openai_client, config):
        """
        Initialize the TwitchBot with necessary API clients, configuration, and selected voice for ElevenLabs.

        Args:
            selected_voice: The voice object selected from ElevenLabs for voice synthesis.
            eleven_client (ElevenLabs): Instance of the ElevenLabs API client.
            openai_client (AsyncOpenAI): Instance of the asynchronous OpenAI API client.
            config (dict): Dictionary containing configuration parameters.
        """
        super().__init__(
            token=config['TWITCH_OAUTH_TOKEN'],
            prefix='!',
            nick=config['TWITCH_BOT_NICK'],
            initial_channels=[config['TWITCH_CHANNEL']]
        )
        self.selected_voice = selected_voice
        self.eleven_client = eleven_client
        self.openai_client = openai_client
        self.config = config
        self.last_ai_command_time = 0  # Timestamp to throttle AI response generation.
        logger.info("TwitchBot initialized.")

    async def event_ready(self):
        """
        Called once the bot has successfully connected to Twitch.
        Logs a readiness message including the bot's nickname.
        """
        logger.info(f'Ready | {self.nick}')

    async def event_message(self, message):
        """
        Handles incoming messages from Twitch chat.
        Processes cheered bits and triggers AI responses based on configured thresholds.
        """
        # Ignore messages from the bot itself to prevent loops.
        if message.echo:
            return

        cheered_bits = 0
        processed_content = message.content

        # Use the pre-compiled CHEER_PATTERN instead of compiling it every time.
        cheered_matches = CHEER_PATTERN.findall(processed_content)
        if cheered_matches:
            # Sum up all bits from the matched cheers.
            cheered_bits = sum(int(re.search(r'\d+', match).group()) for match in cheered_matches)
            logger.info(f'Cheered Bits: {cheered_bits}')

            # Remove the cheer prefixes from the message.
            processed_content = CHEER_PATTERN.sub('', processed_content).strip()
            logger.debug(f'Processed Content after removing cheers: "{processed_content}"')

        if cheered_bits > 0:
            logger.info(f'Cheered Bits: {cheered_bits}')

        # Optionally log the chat message to a file if enabled in the configuration.
        if self.config['CHAT_FLAG']:
            await self.log_chat(message.author.name, message.content)

        # Throttle AI responses to avoid rapid-fire interactions using a timeout duration.
        current_time = time.time()
        if current_time - self.last_ai_command_time > self.config['TIMEOUT_DURATION']:
            self.last_ai_command_time = current_time  # Update the timestamp.

            # Filter the incoming message using banned words and formatting.
            filtered_message = filter_message(
                f"{message.author.name}: {processed_content}",
                self.config['BANNED_WORDS']
            )
            logger.debug(f'Filtered Message: "{filtered_message}"')

            # Trigger AI response generation if the cheered bits exceed the threshold.
            if cheered_bits >= self.config['BIT_THRESHOLD']:
                logger.info("Bit threshold met. Initiating AI response generation.")
                await self.generate_and_send_response(filtered_message)
            else:
                logger.info("Bit threshold not met. No action taken.")

    async def log_chat(self, username: str, message: str):
        """
        Logs the provided chat message to a designated file.
        Uses an asyncio Lock to avoid race conditions during file access.

        Args:
            username (str): The name of the user sending the chat message.
            message (str): The content of the chat message.
        """
        chat_log_path = os.path.join(self.config['BASE_PATH'], self.config['CHAT_LOG_FILE'])
        try:
            async with asyncio.Lock():
                with open(chat_log_path, 'a', encoding='utf-8') as file:
                    file.write(f"{username}: {message}\n")
            logger.info(f'Logged chat message from {username}.')
        except Exception as e:
            logger.error(f"Failed to log chat message: {e}")

    async def generate_and_send_response(self, filtered_message: str):
        """
        Generates an AI response based on the filtered chat message and sends it as audio.
        Interacts with the OpenAI API and uses ElevenLabs for voice synthesis.

        Args:
            filtered_message (str): The sanitized message to base the AI response on.
        """
        try:
            logger.info(f"Generating AI response for message: {filtered_message}")
            response_text = await generate_twitch_channel_talk(filtered_message, self.openai_client, self.config)
            logger.info(f"AI response obtained: {response_text}")
            if response_text:
                logger.info("Sending audio response.")
                await self.send_audio(response_text)
            else:
                logger.warning("No AI response generated; skipping audio playback.")
        except Exception as e:
            logger.error(f"Error in generate_and_send_response: {e}")

    async def send_audio(self, text: str):
        """
        Generates audio from text using ElevenLabs and plays it.
        Executes the synchronous ElevenLabs API call in an executor to prevent blocking the event loop.

        Args:
            text (str): The text content to be converted into audio.
        """
        try:
            logger.info(f"Generating audio for text: {text}")
            # Execute the ElevenLabs synchronous API call in an executor.
            audio = await asyncio.get_event_loop().run_in_executor(
                None,
                functools.partial(
                    self.eleven_client.generate,
                    text=text,
                    voice=self.selected_voice.voice_id,
                    model=self.config['MODEL_VERSION']
                )
            )
            play(audio)  # Play the generated audio.
            logger.info("Audio played successfully.")
        except Exception as e:
            logger.error(f"Failed to generate or play audio: {e}")

# =====================
# OpenAI Interaction
# =====================

async def generate_twitch_channel_talk(latest_message: str, openai_client: AsyncOpenAI, config: dict) -> str:
    """
    Generates an AI response using OpenAI's chat completion endpoint.
    Constructs the conversation context with a system prompt and a formatted user prompt.

    Args:
        latest_message (str): The latest Twitch chat message.
        openai_client (AsyncOpenAI): The asynchronous OpenAI API client.
        config (dict): The configuration dictionary with prompt and model settings.
    
    Returns:
        str: The generated AI response truncated to 360 characters.
    """
    try:
        system_prompt = read_system_prompt(config['BASE_PATH'], config['OPENAI_PROMPT_FILE'])
        prompt = config['PROMPT_TEMPLATE'].format(message=latest_message)
        logger.debug(f'Prompt sent to OpenAI: "{prompt}"')

        response = await openai_client.chat.completions.create(
            model=config['OPENAI_MODEL'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        # Retrieve and truncate the AI response to a maximum of 360 characters.
        ai_response = response.choices[0].message.content.strip()[:360]
        logger.info(f"AI Response: {ai_response}")
        return ai_response

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in generate_twitch_channel_talk: {e}")
    return ""

# =====================
# ElevenLabs Voice Fetch
# =====================

async def fetch_voices(eleven_client: ElevenLabs, VOICE_ID: str):
    """
    Retrieves the available voices from ElevenLabs and selects the desired voice.
    If the specified VOICE_ID is 'default_voice', the first available voice is chosen.

    Args:
        eleven_client (ElevenLabs): The ElevenLabs API client instance.
        VOICE_ID (str): The identifier for the desired voice.
    
    Returns:
        The selected voice object.
    
    Exits:
        Terminates the program if no voices are available or if the specified VOICE_ID is invalid.
    """
    try:
        # Run the synchronous API call in an executor to avoid blocking.
        voices_response = await asyncio.get_event_loop().run_in_executor(
            None, eleven_client.voices.get_all
        )

        if VOICE_ID == "default_voice":
            # Use the first voice as the default if none is specifically provided.
            if voices_response.voices:
                selected_voice = voices_response.voices[0]
                logger.info(f"Using default voice: {selected_voice.name} (ID: {selected_voice.voice_id})")
            else:
                logger.error("No voices available in ElevenLabs.")
                sys.exit(1)
        else:
            # Locate the voice matching the provided VOICE_ID.
            selected_voice = next((voice for voice in voices_response.voices if voice.voice_id == VOICE_ID), None)
            if not selected_voice:
                logger.error(f"Voice ID '{VOICE_ID}' not found. Please check available voices.")
                sys.exit(1)
            logger.info(f"Using voice: {selected_voice.name} (ID: {selected_voice.voice_id})")
        return selected_voice
    except Exception as e:
        logger.error(f"Failed to fetch voices from ElevenLabs: {e}")
        sys.exit(1)

# =====================
# Main Execution
# =====================

async def main():
    """
    The main entry point of the application.
    Handles configuration setup, initialization of API clients, and starts the Twitch bot.
    """
    # Load existing configuration or initiate a new setup if the .env file is not found or user opts out.
    if os.path.exists(CONFIG_FILE):
        print(f"Configuration file '{CONFIG_FILE}' found.")
        if prompt_yes_no("Do you want to use the existing configuration?"):
            config = load_configuration()
        else:
            setup_configuration()
            config = load_configuration()
    else:
        setup_configuration()
        config = load_configuration()

    # Initialize the asynchronous OpenAI API client.
    openai_client = AsyncOpenAI(api_key=config['OPENAI_API_KEY'])

    # Initialize the ElevenLabs API client.
    eleven_client = ElevenLabs(api_key=config['ELEVENLABS_API_KEY'])

    # Retrieve and select the desired voice from ElevenLabs.
    selected_voice = await fetch_voices(eleven_client, config['VOICE_ID'])

    # Instantiate and start the Twitch bot.
    bot = TwitchBot(selected_voice, eleven_client, openai_client, config)
    logger.info("Starting Twitch bot...")
    await bot.start()

if __name__ == "__main__":
    # Custom exception handler to catch and log any unhandled exceptions in the event loop.
    def handle_exception(loop, context):
        msg = context.get("exception", context["message"])
        logger.error(f"Caught exception: {msg}")

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user.")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
