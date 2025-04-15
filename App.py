import asyncio
import os
import re
import sys
import time
import logging
import functools
from typing import List

import openai
from openai.error import OpenAIError  # Import error handling from the OpenAI module.
from twitchio.ext import commands  # TwitchIO framework for bot commands and event handling.
from elevenlabs.client import ElevenLabs  # ElevenLabs API client.
from elevenlabs import play, VoiceSettings  # For playing audio and custom voice settings.
from dotenv import load_dotenv  # Loads environment variables from a .env file.

# =========================
# Module-Level Constants
# =========================

# Pre-compile a regex pattern for additional cheer word cleanup.
CHEER_CLEANUP_PATTERN = re.compile(r'cheer\d+', re.IGNORECASE)

# =========================
# Configuration and Logging
# =========================

logging.basicConfig(
    level=logging.INFO,  # Switch to DEBUG for more granular logs during development.
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
CONFIG_FILE = '.env'

# =====================
# Utility Functions
# =====================

def prompt_yes_no(question: str) -> bool:
    """Prompt the user with a yes/no question until a valid response is received."""
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
    Collect configuration inputs from the user and write them to the .env file.
    This includes Twitch, API keys, and ElevenLabs voice settings.
    """
    config = {}
    print("=== Twitch Bot Configuration Setup ===")

    # Twitch configuration.
    config['TWITCH_CHANNEL'] = input("Enter your Twitch channel name: ").strip()
    config['TWITCH_OAUTH_TOKEN'] = input("Enter your Twitch OAuth token: ").strip()
    config['TWITCH_BOT_NICK'] = input("Enter your Twitch bot nickname (default: Bot): ").strip() or "Bot"

    # API keys.
    config['OPENAI_API_KEY'] = input("Enter your OpenAI API key: ").strip()
    config['ELEVENLABS_API_KEY'] = input("Enter your ElevenLabs API key: ").strip()

    # ElevenLabs voice configuration.
    voice_id_input = input("Enter ElevenLabs voice ID (default: use 'default_voice'): ").strip()
    config['VOICE_ID'] = voice_id_input if voice_id_input else "default_voice"
    # Default to the Flash model for ultra-low latency.
    config['MODEL_VERSION'] = input("Enter ElevenLabs model version (default: eleven_flash_v2_5): ").strip() or "eleven_flash_v2_5"

    # New voice settings.
    config['VOICE_SIMILARITY_BOOST'] = input("Enter voice similarity boost (default: 1.0): ").strip() or "1.0"
    config['VOICE_STABILITY'] = input("Enter voice stability (default: 0.0): ").strip() or "0.0"
    config['VOICE_STYLE'] = input("Enter voice style (default: 0.0): ").strip() or "0.0"
    speaker_boost_input = input("Use speaker boost? (y/n, default: y): ").strip().lower() or "y"
    config['VOICE_USE_SPEAKER_BOOST'] = "True" if speaker_boost_input in ['y', 'yes'] else "False"
    config['VOICE_SPEED'] = input("Enter voice speed (default: 1.0): ").strip() or "1.0"

    # File system configuration.
    base_path_input = input("Enter base directory path (default: c:\\Temp): ").strip()
    config['BASE_PATH'] = base_path_input if base_path_input else "c:\\Temp"
    config['OPENAI_PROMPT_FILE'] = input("Enter OpenAI prompt filename (default: prompt.txt): ").strip() or "prompt.txt"
    config['CHAT_LOG_FILE'] = input("Enter chat log filename (default: chat.txt): ").strip() or "chat.txt"

    # Bot behavior settings.
    bit_threshold_input = input("Enter bits threshold to trigger AI response (default: 20): ").strip()
    config['BIT_THRESHOLD'] = bit_threshold_input if bit_threshold_input else "20"
    timeout_duration_input = input("Enter timeout duration in seconds (default: 15): ").strip()
    config['TIMEOUT_DURATION'] = timeout_duration_input if timeout_duration_input else "15"
    chat_flag_input = input("Enable chat logging? (y/n, default: n): ").strip().lower() or "n"
    config['CHAT_FLAG'] = "True" if chat_flag_input in ['y', 'yes'] else "False"

    # Banned words.
    print("Enter banned words separated by commas (leave empty for none):")
    banned_words_input = input().strip()
    config['BANNED_WORDS'] = banned_words_input if banned_words_input else ""

    # Custom prompt template.
    prompt_template_input = input("Enter prompt template (leave empty to use default): ").strip()
    if prompt_template_input:
        config['PROMPT_TEMPLATE'] = prompt_template_input

    # Write the configuration to the .env file.
    try:
        with open(CONFIG_FILE, 'w') as env_file:
            for key, value in config.items():
                env_file.write(f"{key}='{value}'\n")
        print(f"Configuration saved to {CONFIG_FILE}.\n")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        sys.exit(1)

def load_configuration():
    """
    Loads configuration variables from the .env file with appropriate type conversions,
    including the new voice settings.
    """
    load_dotenv(CONFIG_FILE)
    config = {}
    config['TWITCH_CHANNEL'] = os.getenv('TWITCH_CHANNEL')
    config['TWITCH_OAUTH_TOKEN'] = os.getenv('TWITCH_OAUTH_TOKEN')
    config['TWITCH_BOT_NICK'] = os.getenv('TWITCH_BOT_NICK', 'Bot')

    config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    config['ELEVENLABS_API_KEY'] = os.getenv('ELEVENLABS_API_KEY')

    config['VOICE_ID'] = os.getenv('VOICE_ID', 'default_voice')
    config['MODEL_VERSION'] = os.getenv('MODEL_VERSION', 'eleven_flash_v2_5')

    # Convert new voice settings.
    try:
        config['VOICE_SIMILARITY_BOOST'] = float(os.getenv('VOICE_SIMILARITY_BOOST', '1.0'))
    except ValueError:
        logger.error("Invalid VOICE_SIMILARITY_BOOST, defaulting to 1.0")
        config['VOICE_SIMILARITY_BOOST'] = 1.0
    try:
        config['VOICE_STABILITY'] = float(os.getenv('VOICE_STABILITY', '0.0'))
    except ValueError:
        logger.error("Invalid VOICE_STABILITY, defaulting to 0.0")
        config['VOICE_STABILITY'] = 0.0
    try:
        config['VOICE_STYLE'] = float(os.getenv('VOICE_STYLE', '0.0'))
    except ValueError:
        logger.error("Invalid VOICE_STYLE, defaulting to 0.0")
        config['VOICE_STYLE'] = 0.0
    config['VOICE_USE_SPEAKER_BOOST'] = os.getenv('VOICE_USE_SPEAKER_BOOST', 'True') == 'True'
    try:
        config['VOICE_SPEED'] = float(os.getenv('VOICE_SPEED', '1.0'))
    except ValueError:
        logger.error("Invalid VOICE_SPEED, defaulting to 1.0")
        config['VOICE_SPEED'] = 1.0

    # File system and prompt configuration.
    config['BASE_PATH'] = os.getenv('BASE_PATH', 'c:\\Temp')
    config['OPENAI_PROMPT_FILE'] = os.getenv('OPENAI_PROMPT_FILE', 'prompt.txt')
    config['CHAT_LOG_FILE'] = os.getenv('CHAT_LOG_FILE', 'chat.txt')

    try:
        config['BIT_THRESHOLD'] = int(os.getenv('BIT_THRESHOLD', '20'))
    except ValueError:
        logger.error("Invalid BIT_THRESHOLD; it should be an integer.")
        config['BIT_THRESHOLD'] = 20

    try:
        config['TIMEOUT_DURATION'] = int(os.getenv('TIMEOUT_DURATION', '15'))
    except ValueError:
        logger.error("Invalid TIMEOUT_DURATION; it should be an integer.")
        config['TIMEOUT_DURATION'] = 15

    config['CHAT_FLAG'] = os.getenv('CHAT_FLAG', 'False') == 'True'
    banned_words_str = os.getenv('BANNED_WORDS', '')
    config['BANNED_WORDS'] = [word.strip() for word in banned_words_str.split(',')] if banned_words_str else []

    config['PROMPT_TEMPLATE'] = os.getenv('PROMPT_TEMPLATE',
        f'Here is the latest message from Twitch chat: "{{message}}". '
        f'Phonetically space out their username then acknowledge them and respond '
        f'to their message in 1 or 2 sentences. Speak naturally as {config["TWITCH_CHANNEL"]}. '
        "Don't forget the sass."
    )
    config['OPENAI_MODEL'] = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    return config

def filter_message(text: str, banned_words: List[str]) -> str:
    """
    Filters and sanitizes an incoming message by removing banned words,
    then truncates the result to a maximum of 130 characters.
    """
    for word in banned_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub('*' * len(word), text)
    return text[:130]

def read_system_prompt(DIR_PATH: str, OPENAI_PROMPT_FILE: str) -> str:
    """
    Reads the system prompt from a specified file.
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
    A Twitch bot that interacts with chat by processing messages through OpenAI and using ElevenLabs to generate voice responses.
    """

    def __init__(self, selected_voice, eleven_client, config):
        super().__init__(
            token=config['TWITCH_OAUTH_TOKEN'],
            prefix='!',
            nick=config['TWITCH_BOT_NICK'],
            initial_channels=[config['TWITCH_CHANNEL']]
        )
        self.selected_voice = selected_voice
        self.eleven_client = eleven_client
        self.config = config
        self.last_ai_command_time = 0  # To throttle response generation.
        logger.info("TwitchBot initialized.")

    async def event_ready(self):
        logger.info(f"Ready | {self.nick}")

    async def event_message(self, message):
        # Prevent processing our own messages.
        if message.echo:
            return

        processed_content = message.content

        # Improved: Get bit donation amount from message metadata instead of solely parsing text.
        try:
            cheered_bits = int(message.tags.get("bits", 0)) if message.tags and "bits" in message.tags else 0
        except Exception as e:
            logger.warning(f"Failed to retrieve bits from message tags: {e}")
            cheered_bits = 0

        if cheered_bits > 0:
            logger.info(f"Cheered Bits: {cheered_bits}")
            # Optionally clean up the message content by removing cheer keywords.
            processed_content = CHEER_CLEANUP_PATTERN.sub('', processed_content).strip()

        if self.config['CHAT_FLAG']:
            await self.log_chat(message.author.name, message.content)

        current_time = time.time()
        if current_time - self.last_ai_command_time > self.config['TIMEOUT_DURATION']:
            self.last_ai_command_time = current_time
            filtered_message = filter_message(f"{message.author.name}: {processed_content}", self.config['BANNED_WORDS'])
            logger.debug(f"Filtered Message: '{filtered_message}'")
            if cheered_bits >= self.config['BIT_THRESHOLD']:
                logger.info("Bit threshold met. Initiating AI response generation.")
                await self.generate_and_send_response(filtered_message)
            else:
                logger.info("Bit threshold not met. No action taken.")

        await self.handle_commands(message)

    async def log_chat(self, username: str, message: str):
        chat_log_path = os.path.join(self.config['BASE_PATH'], self.config['CHAT_LOG_FILE'])
        try:
            async with asyncio.Lock():
                with open(chat_log_path, 'a', encoding='utf-8') as file:
                    file.write(f"{username}: {message}\n")
            logger.info(f"Logged chat message from {username}.")
        except Exception as e:
            logger.error(f"Failed to log chat message: {e}")

    async def generate_and_send_response(self, filtered_message: str):
        try:
            logger.info(f"Generating AI response for message: {filtered_message}")
            response_text = await generate_twitch_channel_talk(filtered_message, self.config)
            logger.info(f"AI Response: {response_text}")
            if response_text:
                logger.info("Sending audio response.")
                await self.send_audio(response_text)
            else:
                logger.warning("No AI response generated; skipping audio playback.")
        except Exception as e:
            logger.error(f"Error in generate_and_send_response: {e}")

    async def send_audio(self, text: str):
        """
        Generates audio from text using ElevenLabs. Configured voice settings and model details are applied.
        """
        try:
            logger.info(f"Generating audio for text: {text}")
            # Determine output format based on the model version.
            output_format = "mp3_44100_128" if self.config['MODEL_VERSION'].startswith("eleven_flash") else "mp3_22050_32"

            # Build a VoiceSettings object from the config.
            voice_settings = VoiceSettings(
                stability=self.config['VOICE_STABILITY'],
                similarity_boost=self.config['VOICE_SIMILARITY_BOOST'],
                style=self.config['VOICE_STYLE'],
                use_speaker_boost=self.config['VOICE_USE_SPEAKER_BOOST'],
                speed=self.config['VOICE_SPEED']
            )

            # Execute the synchronous TTS API call in an executor.
            audio = await asyncio.get_event_loop().run_in_executor(
                None,
                functools.partial(
                    self.eleven_client.text_to_speech.convert,
                    text=text,
                    voice_id=self.selected_voice.voice_id,
                    model_id=self.config['MODEL_VERSION'],
                    output_format=output_format,
                    voice_settings=voice_settings
                )
            )
            play(audio)  # Play the generated audio.
            logger.info("Audio played successfully.")
        except Exception as e:
            logger.error(f"Failed to generate or play audio: {e}")

    @commands.command(name="setvoice")
    async def set_voice(self, ctx):
        """
        Chat command to update voice settings in real time.
        Usage: !setvoice <stability> <similarity_boost> <style> <use_speaker_boost> <speed>
        Only the broadcaster is authorized to use this command.
        """
        if ctx.author.name.lower() != self.config['TWITCH_CHANNEL'].lower():
            await ctx.send("You are not authorized to change voice settings.")
            return

        args = ctx.message.content.split()[1:]
        if len(args) != 5:
            await ctx.send("Usage: !setvoice <stability> <similarity_boost> <style> <use_speaker_boost> <speed>")
            return

        try:
            self.config['VOICE_STABILITY'] = float(args[0])
            self.config['VOICE_SIMILARITY_BOOST'] = float(args[1])
            self.config['VOICE_STYLE'] = float(args[2])
            self.config['VOICE_USE_SPEAKER_BOOST'] = args[3].lower() in ['true', 'yes', '1']
            self.config['VOICE_SPEED'] = float(args[4])
            await ctx.send("Voice settings updated successfully.")
            logger.info("Voice settings updated via chat command.")
        except Exception as e:
            await ctx.send(f"Error updating voice settings: {e}")

# =====================
# OpenAI Interaction
# =====================

async def generate_twitch_channel_talk(latest_message: str, config: dict) -> str:
    """
    Generates an AI response using OpenAI's chat completion endpoint.
    """
    try:
        system_prompt = read_system_prompt(config['BASE_PATH'], config['OPENAI_PROMPT_FILE'])
        prompt = config['PROMPT_TEMPLATE'].format(message=latest_message)
        logger.debug(f"Prompt sent to OpenAI: '{prompt}'")

        # Set the API key for OpenAI.
        openai.api_key = config['OPENAI_API_KEY']
        response = await openai.ChatCompletion.acreate(
            model=config['OPENAI_MODEL'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

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
    """
    try:
        voices_response = await asyncio.get_event_loop().run_in_executor(
            None, eleven_client.voices.get_all
        )

        if VOICE_ID == "default_voice":
            if voices_response.voices:
                selected_voice = voices_response.voices[0]
                logger.info(f"Using default voice: {selected_voice.name} (ID: {selected_voice.voice_id})")
            else:
                logger.error("No voices available in ElevenLabs.")
                sys.exit(1)
        else:
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
    Main entry point that handles configuration, API client initialization, and starts the Twitch bot.
    """
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

    # Initialize the OpenAI API key.
    openai.api_key = config['OPENAI_API_KEY']

    eleven_client = ElevenLabs(api_key=config['ELEVENLABS_API_KEY'])
    selected_voice = await fetch_voices(eleven_client, config['VOICE_ID'])

    bot = TwitchBot(selected_voice, eleven_client, config)
    logger.info("Starting Twitch bot...")
    await bot.start()

if __name__ == "__main__":
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
