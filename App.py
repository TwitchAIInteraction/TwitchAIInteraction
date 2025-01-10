import asyncio
import os
import re
import time
import logging
from typing import List
import functools

import openai
from openai import OpenAIError, AsyncOpenAI  # Import OpenAIError for exception handling, AsyncOpenAI client for asynchronous operations
from twitchio.ext import commands
from elevenlabs.client import ElevenLabs
from elevenlabs import play
from dotenv import load_dotenv

import sys

# =========================
# Configuration and Logging
# =========================

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO,  # Set to INFO for production; change to DEBUG for development
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Path to the configuration file
CONFIG_FILE = '.env'

# =====================
# Utility Functions
# =====================

def prompt_yes_no(question: str) -> bool:
    """
    Prompts the user with a yes/no question, returns as bool
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
    Handles user input for configuration variables and saves them to the .env file.
    This function is intended for initial setup and interactive configuration.
    """
    config = {}
    print("=== Twitch Bot Configuration Setup ===")

    # Twitch Configuration
    config['TWITCH_CHANNEL'] = input("Enter your Twitch channel name: ").strip()
    config['TWITCH_OAUTH_TOKEN'] = input("Enter your Twitch OAuth token: ").strip()
    config['TWITCH_BOT_NICK'] = input("Enter your Twitch bot nickname (default: Bot): ").strip() or "Bot"

    # API Keys
    config['OPENAI_API_KEY'] = input("Enter your OpenAI API key: ").strip()
    config['ELEVENLABS_API_KEY'] = input("Enter your ElevenLabs API key: ").strip()

    # ElevenLabs Configuration
    voice_id_input = input("Enter ElevenLabs voice ID (default: use 'default_voice'): ").strip()
    config['VOICE_ID'] = voice_id_input if voice_id_input else "default_voice"
    config['MODEL_VERSION'] = input("Enter ElevenLabs model version (default: eleven_multilingual_v2): ").strip() or "eleven_multilingual_v2"

    # File System Configuration
    base_path_input = input("Enter base directory path (default: c:\\Temp): ").strip()
    config['BASE_PATH'] = base_path_input if base_path_input else "c:\\Temp"
    config['OPENAI_PROMPT_FILE'] = input("Enter OpenAI prompt filename (default: prompt.txt): ").strip() or "prompt.txt"
    config['CHAT_LOG_FILE'] = input("Enter chat log filename (default: chat.txt): ").strip() or "chat.txt"

    # Bot Behavior Settings
    bit_threshold_input = input("Enter bits threshold to trigger AI response (default: 20): ").strip()
    config['BIT_THRESHOLD'] = bit_threshold_input if bit_threshold_input else "20"

    timeout_duration_input = input("Enter timeout duration in seconds (default: 15): ").strip()
    config['TIMEOUT_DURATION'] = timeout_duration_input if timeout_duration_input else "15"

    chat_flag_input = input("Enable chat logging? (y/n, default: n): ").strip().lower()
    config['CHAT_FLAG'] = "True" if chat_flag_input in ['y', 'yes'] else "False"

    # Banned Words
    print("Enter banned words separated by commas (leave empty for none):")
    banned_words_input = input().strip()
    config['BANNED_WORDS'] = banned_words_input if banned_words_input else ""

    # Optional: Prompt Template
    prompt_template_input = input("Enter prompt template (leave empty to use default): ").strip()
    if prompt_template_input:
        config['PROMPT_TEMPLATE'] = prompt_template_input

    # Save configurations to .env
    try:
        with open(CONFIG_FILE, 'w') as env_file:
            for key, value in config.items():
                if key == 'BANNED_WORDS':
                    # Save as comma-separated string for lists
                    env_file.write(f"{key}='{value}'\n")
                else:
                    env_file.write(f"{key}='{value}'\n")
        print(f"Configuration saved to {CONFIG_FILE}.\n")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        sys.exit(1)

def load_configuration():
    """
    Loads configuration from the .env file and converts types as necessary.
    Environment variables are prioritized over .env settings.

    Returns:
        dict: A dictionary containing all configuration variables.
    """
    load_dotenv(CONFIG_FILE)

    # Retrieve and convert configuration variables
    config = {}
    config['TWITCH_CHANNEL'] = os.getenv('TWITCH_CHANNEL')
    config['TWITCH_OAUTH_TOKEN'] = os.getenv('TWITCH_OAUTH_TOKEN')
    config['TWITCH_BOT_NICK'] = os.getenv('TWITCH_BOT_NICK', 'Bot')

    config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    config['ELEVENLABS_API_KEY'] = os.getenv('ELEVENLABS_API_KEY')

    config['VOICE_ID'] = os.getenv('VOICE_ID', 'default_voice')
    config['MODEL_VERSION'] = os.getenv('MODEL_VERSION', 'eleven_multilingual_v2')

    config['BASE_PATH'] = os.getenv('BASE_PATH', 'c:\\Temp')
    config['OPENAI_PROMPT_FILE'] = os.getenv('OPENAI_PROMPT_FILE', 'prompt.txt')
    config['CHAT_LOG_FILE'] = os.getenv('CHAT_LOG_FILE', 'chat.txt')

    # Convert BIT_THRESHOLD to integer
    try:
        config['BIT_THRESHOLD'] = int(os.getenv('BIT_THRESHOLD', '20'))
    except ValueError:
        logger.error("Invalid BIT_THRESHOLD. It should be an integer.")
        config['BIT_THRESHOLD'] = 20  # Default value

    # Convert TIMEOUT_DURATION to integer
    try:
        config['TIMEOUT_DURATION'] = int(os.getenv('TIMEOUT_DURATION', '15'))
    except ValueError:
        logger.error("Invalid TIMEOUT_DURATION. It should be an integer.")
        config['TIMEOUT_DURATION'] = 15  # Default value

    # Convert CHAT_FLAG to boolean
    config['CHAT_FLAG'] = os.getenv('CHAT_FLAG', 'False') == 'True'

    # Parse BANNED_WORDS into a list
    banned_words_str = os.getenv('BANNED_WORDS', '')
    config['BANNED_WORDS'] = [word.strip() for word in banned_words_str.split(',')] if banned_words_str else []

    # Set default PROMPT_TEMPLATE if not provided
    config['PROMPT_TEMPLATE'] = os.getenv('PROMPT_TEMPLATE',
        f'Here is the latest message from Twitch chat: "{{message}}". '
        f'Phonetically space out their username then acknowledge them and respond '
        f'to their message in 1 or 2 sentences. Speak naturally as {config["TWITCH_CHANNEL"]}. '
        "Don't forget the sass."
    )

    # Set default OpenAI model if not specified
    config['OPENAI_MODEL'] = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    return config

def filter_message(text: str, banned_words: List[str]) -> str:
    """
    Filters the incoming message by removing cheer prefixes and banned words.
    Limits the message length to 130 characters.

    Args:
        text (str): The original message text.
        banned_words (List[str]): A list of words to be censored.

    Returns:
        str: The filtered and truncated message.
    """
    # Remove cheer prefixes like cheer1000, etc.
    text = re.sub(r'cheer\d+\s+', '', text, flags=re.I)
    # Remove banned words by replacing them with asterisks
    for word in banned_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub('*' * len(word), text)
    # Truncate to 130 characters
    return text[:130]

def read_system_prompt(DIR_PATH: str, OPENAI_PROMPT_FILE: str) -> str:
    """
    Reads the system prompt from the specified prompt file.
    If the file doesn't exist, returns a default error message.

    Args:
        DIR_PATH (str): The directory path where the prompt file is located.
        OPENAI_PROMPT_FILE (str): The name of the prompt file.

    Returns:
        str: The content of the prompt file or a default error message.
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
    Twitch Bot class that handles events and interactions.
    Inherits from twitchio.ext.commands.Bot.
    """

    def __init__(self, selected_voice, eleven_client, openai_client, config):
        """
        Initializes the TwitchBot with the provided configurations and API clients.

        Args:
            selected_voice: The selected voice object from ElevenLabs.
            eleven_client (ElevenLabs): The ElevenLabs API client.
            openai_client (AsyncOpenAI): The OpenAI API client.
            config (dict): The configuration dictionary.
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
        self.last_ai_command_time = 0  # Initialize the timestamp for throttling AI responses
        logger.info("TwitchBot initialized.")

    async def event_ready(self):
        """
        Called once when the bot is ready.
        Logs the bot's readiness.
        """
        logger.info(f'Ready | {self.nick}')

    async def event_message(self, message):
        """
        Handles incoming messages from Twitch chat.
        Processes cheered bits and triggers AI responses based on configured thresholds.

        Args:
            message: The incoming Twitch chat message.
        """
        # Ignore messages from the bot itself to prevent loops
        if message.echo:
            return

        cheered_bits = 0
        processed_content = message.content

        # Regex pattern to match various cheer emotes with bits
        cheer_pattern = re.compile(
            r'(BibleThump\d+|cheerwhal\d+|Corgo\d+|uni\d+|ShowLove\d+|Party\d+|'
            r'SeemsGood\d+|Pride\d+|Kappa\d+|cheer\d+|FrankerZ\d+|HeyGuys\d+|'
            r'DansGame\d+|EleGiggle\d+|TriHard\d+|Kreygasm\d+|4Head\d+|SwiftRage\d+|'
            r'NotLikeThis\d+|FailFish\d+|VoHiYo\d+|PJSalt\d+|MrDestructoid\d+|'
            r'bday\d+|RIPCheer\d+|Shamrock\d)', re.IGNORECASE
        )

        cheered_matches = cheer_pattern.findall(processed_content)
        if cheered_matches:
            # Sum up all bits from the matched cheers
            cheered_bits = sum(int(re.search(r'\d+', match).group()) for match in cheered_matches)
            logger.info(f'Cheered Bits: {cheered_bits}')

            # Remove the cheer prefixes from the message
            processed_content = cheer_pattern.sub('', processed_content).strip()
            logger.debug(f'Processed Content after removing cheers: "{processed_content}"')

        # Log cheered bits if any
        if cheered_bits > 0:
            logger.info(f'Cheered Bits: {cheered_bits}')

        # Optionally log chat messages to a file
        if self.config['CHAT_FLAG']:
            await self.log_chat(message.author.name, message.content)

        # Throttle AI responses based on TIMEOUT_DURATION to prevent spamming
        current_time = time.time()
        if current_time - self.last_ai_command_time > self.config['TIMEOUT_DURATION']:
            self.last_ai_command_time = current_time  # Update the timestamp

            # Filter the message content
            filtered_message = filter_message(
                f"{message.author.name}: {processed_content}",
                self.config['BANNED_WORDS']
            )
            logger.debug(f'Filtered Message: "{filtered_message}"')

            # Trigger AI response if bit threshold is met
            if cheered_bits >= self.config['BIT_THRESHOLD']:
                logger.info("Bit threshold met. Initiating AI response generation.")
                await self.generate_and_send_response(filtered_message)
            else:
                logger.info("Bit threshold not met. No action taken.")

    async def log_chat(self, username: str, message: str):
        """
        Logs chat messages to a specified file.

        Args:
            username (str): The name of the user who sent the message.
            message (str): The content of the message.
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
        Generates a response using OpenAI and sends it as audio in the Twitch chat.

        Args:
            filtered_message (str): The filtered chat message to generate a response for.
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
        Generates and plays audio from the given text using ElevenLabs.

        Args:
            text (str): The text to convert to audio.
        """
        try:
            logger.info(f"Generating audio for text: {text}")
            # Since ElevenLabs SDK methods are synchronous, run them in an executor
            audio = await asyncio.get_event_loop().run_in_executor(
                None,
                functools.partial(
                    self.eleven_client.generate,
                    text=text,
                    voice=self.selected_voice.voice_id,
                    model=self.config['MODEL_VERSION']
                )
            )
            play(audio)  # Play the generated audio
            logger.info("Audio played successfully.")
        except Exception as e:
            logger.error(f"Failed to generate or play audio: {e}")

# =====================
# OpenAI Interaction
# =====================

async def generate_twitch_channel_talk(latest_message: str, openai_client: AsyncOpenAI, config: dict) -> str:
    """
    Interacts with OpenAI's API to generate a response based on the latest Twitch message.

    Args:
        latest_message (str): The latest message from Twitch chat.
        openai_client (AsyncOpenAI): The OpenAI API client.
        config (dict): The configuration dictionary.

    Returns:
        str: The AI-generated response, truncated to 360 characters.
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

        # Access the content attribute correctly
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
    Fetches available voices from ElevenLabs and selects the desired voice.

    Args:
        eleven_client (ElevenLabs): The ElevenLabs API client.
        VOICE_ID (str): The ID of the desired voice.

    Returns:
        The selected voice object.

    Exits:
        If no voices are available or the specified VOICE_ID is not found.
    """
    try:
        # Since ElevenLabs SDK methods are synchronous, run them in an executor
        voices_response = await asyncio.get_event_loop().run_in_executor(
            None, eleven_client.voices.get_all
        )

        if VOICE_ID == "default_voice":
            # Select the first voice as default if 'default_voice' is used
            if voices_response.voices:
                selected_voice = voices_response.voices[0]
                logger.info(f"Using default voice: {selected_voice.name} (ID: {selected_voice.voice_id})")
            else:
                logger.error("No voices available in ElevenLabs.")
                sys.exit(1)
        else:
            # Find the voice with the specified VOICE_ID
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
    Main entry point for the Twitch bot.
    Handles configuration loading, API client initialization, and bot startup.
    """
    # Load or set up configuration
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

    # Initialize OpenAI API
    openai_client = AsyncOpenAI(api_key=config['OPENAI_API_KEY'])  # Instantiate AsyncOpenAI client

    # Initialize ElevenLabs API
    eleven_client = ElevenLabs(api_key=config['ELEVENLABS_API_KEY'])

    # Fetch voices and select the desired one
    selected_voice = await fetch_voices(eleven_client, config['VOICE_ID'])

    # Instantiate and start the Twitch bot
    bot = TwitchBot(selected_voice, eleven_client, openai_client, config)
    logger.info("Starting Twitch bot...")
    await bot.start()

if __name__ == "__main__":
    # Set a custom exception handler to log unhandled exceptions
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
