import asyncio
import os
import re
import time
import logging
from typing import List

import openai
from twitchio.ext import commands
from elevenlabs import set_api_key, generate, play, Voices, User
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants and Configuration

# Twitch channel name (update as needed)
TWITCH_CHANNEL = 'YourTwitchChannelName'

# Choose a directory, otherwise default is "c:\\Temp"
BASE_PATH = os.getenv("BASE_PATH", "c:\\Temp")

DIR_PATH = os.path.abspath(BASE_PATH)
OPENAI_PROMPT_FILE = "prompt.txt"
CHAT_LOG_FILE = "chat.txt"
CHAT_FLAG = False  # Set to True to enable chat logging

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
PROMPT_TEMPLATE = (
    'Here is the latest message from Twitch chat: "{message}". '
    "Phonetically space out their username then acknowledge them and respond "
    f"to their message in 1 or 2 sentences. Speak naturally as {TWITCH_CHANNEL}. "
    "Don't forget the sass."
)

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_INDEX = 40  # Update as per available voices
MODEL_VERSION = "eleven_monolingual_v1"

# Twitch Configuration
TWITCH_CHANNELS = [TWITCH_CHANNEL]  # Use the Twitch channel constant
TWITCH_OAUTH_TOKEN = os.getenv("TWITCH_OAUTH_TOKEN")
TWITCH_BOT_NICK = os.getenv("TWITCH_BOT_NICK", "Bot")  # Bot's nickname

# Bit Donation Settings
BIT_THRESHOLD = 20  # Bits required to trigger AI response
TIMEOUT_DURATION = 15  # Seconds to prevent frequent AI responses

# Banned Words Configuration
BANNED_WORDS: List[str] = []  # Populate with words to filter out
BANNED_WORDS.sort(key=len, reverse=True)  # Sort by length for efficient filtering

# Global State
LAST_AI_COMMAND_TIME = 0  # Timestamp of the last AI command

# Initialize OpenAI API
openai.api_key = OPENAI_API_KEY

# Initialize ElevenLabs API
set_api_key(ELEVENLABS_API_KEY)
voices = Voices.from_api()
try:
    voicing = voices[VOICE_INDEX]
    voicing.settings.stability = 0.28
    voicing.settings.similarity_boost = 0.98
except IndexError:
    logger.error(f"Voice index {VOICE_INDEX} is out of range. Please check available voices.")
    raise

user = User.from_api()

def filter_message(text: str) -> str:
    """
    Filters the incoming message by removing cheer prefixes and banned words.
    Limits the message length to 130 characters.
    """
    # Remove cheer prefixes like cheer1000, etc.
    text = re.sub(r'cheer\d+\s+', '', text, flags=re.I)
    # Remove banned words
    for word in BANNED_WORDS:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub('*' * len(word), text)
    # Truncate to 130 characters
    return text[:130]

def read_system_prompt() -> str:
    """
    Reads the system prompt from the prompt file.
    If the file doesn't exist, returns a default error message.
    """
    prompt_path = os.path.join(DIR_PATH, OPENAI_PROMPT_FILE)
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        logger.error(f"Prompt file not found at {prompt_path}.")
        return "TELL EVERYBODY THE PROMPT IS BROKEN"

class TwitchBot(commands.Bot):
    """
    Twitch Bot class that handles events and interactions.
    """

    def __init__(self):
        super().__init__(
            token=TWITCH_OAUTH_TOKEN,
            prefix='!',
            nick=TWITCH_BOT_NICK,
            initial_channels=TWITCH_CHANNELS
        )
        self.should_stop = False
        logger.info("TwitchBot initialized.")

    async def event_ready(self):
        """
        Called once when the bot is ready.
        """
        logger.info(f'Ready | {self.nick}')

    async def event_message(self, message):
        """
        Handles incoming messages from Twitch chat.
        """
        global LAST_AI_COMMAND_TIME

        # Ignore messages from the bot itself to prevent loops
        if message.echo:
            return

        # Initialize cheered bits for this message
        cheered_bits = 0
        processed_content = message.content

        # Regex pattern to match various cheer emotes with bits
        cheer_pattern = re.compile(
            r'(BibleThump\d+|cheerwhal\d+|Corgo\d+|uni\d+|ShowLove\d+|Party\d+|'
            r'SeemsGood\d+|Pride\d+|Kappa\d+|cheer\d+|FrankerZ\d+|HeyGuys\d+|'
            r'DansGame\d+|EleGiggle\d+|TriHard\d+|Kreygasm\d+|4Head\d+|SwiftRage\d+|'
            r'NotLikeThis\d+|FailFish\d+|VoHiYo\d+|PJSalt\d+|MrDestructoid\d+|'
            r'bday\d+|RIPCheer\d+|Shamrock\d+)', re.IGNORECASE
        )

        cheered_matches = cheer_pattern.findall(processed_content)
        if cheered_matches:
            # Sum up all bits from the matched cheers
            cheered_bits = sum(int(re.search(r'\d+', match).group()) for match in cheered_matches)
            logger.debug(f'Cheered Bits: {cheered_bits}')

            # Remove the cheer prefixes from the message
            processed_content = cheer_pattern.sub('', processed_content).strip()
            logger.debug(f'Processed Content after removing cheers: "{processed_content}"')

        # Log cheered bits if any
        if cheered_bits > 0:
            logger.info(f'Cheered Bits: {cheered_bits}')

        # Optional: Log chat messages to a file
        if CHAT_FLAG:
            await self.log_chat(message.author.name, message.content)

        # Throttle AI responses based on TIMEOUT_DURATION
        current_time = time.time()
        if current_time - LAST_AI_COMMAND_TIME > TIMEOUT_DURATION:
            LAST_AI_COMMAND_TIME = current_time

            # Filter the message content
            filtered_message = filter_message(f"{message.author.name}: {processed_content}")
            logger.debug(f'Filtered Message: "{filtered_message}"')

            # Trigger AI response if bit threshold is met
            if cheered_bits >= BIT_THRESHOLD:
                await self.generate_and_send_response(filtered_message)

    async def log_chat(self, username: str, message: str):
        """
        Logs chat messages to a specified file.
        """
        chat_log_path = os.path.join(DIR_PATH, CHAT_LOG_FILE)
        try:
            async with asyncio.Lock():
                with open(chat_log_path, 'a', encoding='utf-8') as file:
                    file.write(f"{username}: {message}\n")
            logger.debug(f'Logged chat message from {username}.')
        except Exception as e:
            logger.error(f"Failed to log chat message: {e}")

    async def generate_and_send_response(self, filtered_message: str):
        """
        Generates a response using OpenAI and sends it as audio in the Twitch chat.
        """
        try:
            response_text = await generate_twitch_channel_talk(filtered_message, OPENAI_MODEL)
            if response_text:
                await self.send_audio(response_text)
        except Exception as e:
            logger.error(f"Error in generate_and_send_response: {e}")

    async def send_audio(self, text: str):
        """
        Generates and plays audio from the given text using ElevenLabs.
        """
        try:
            audio = generate(text=text, voice=voicing, model=MODEL_VERSION)
            play(audio)
            logger.info("Audio played successfully.")
        except Exception as e:
            logger.error(f"Failed to generate or play audio: {e}")

async def generate_twitch_channel_talk(latest_message: str, model: str) -> str:
    """
    Interacts with OpenAI's API to generate a response based on the latest Twitch message.
    """
    try:
        system_prompt = read_system_prompt()
        prompt = PROMPT_TEMPLATE.format(message=latest_message)
        logger.debug(f'Prompt sent to OpenAI: "{prompt}"')

        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract and truncate the response
        ai_response = response.choices[0].message['content'].strip()[:360]
        logger.info(f"AI Response: {ai_response}")
        return ai_response

    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in generate_twitch_channel_talk: {e}")
    return ""

async def main():
    """
    Main entry point for the Twitch bot.
    """
    bot = TwitchBot()
    logger.info("Starting Twitch bot...")
    await bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user.")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
