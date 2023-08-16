import asyncio
import os
import openai
import re
from twitchio.ext import commands
import time
from elevenlabs import set_api_key, generate, play, Voices, User


# Directory Path for dynamically-updating OpenAI prompt and Twitch chat log
dir_path = os.path.join(os.environ.get("BASE_PATH", "c:\\Temp"))
OPENAI_PROMPT = "prompt.txt" #OpenAI prompt file name
CHAT_FLAG = False #Keep a Twitch chat log?
CHAT_LOG_TXT = "chat.txt" #Chat log file name

# OpenAI API Key and settings
openai.api_key = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-3.5-turbo"
PROMPT_TEMPLATE = "Here is the latest message from Twitch chat: \" {message} \" Phonetically space out their username then acknowledge them and respond to their message in 1 or 2 sentences. Speak naturally as TWITCH_CHANNEL/Jay. Don't forget the sass."

# ElevenLabs API Key and settings
set_api_key(os.environ.get("ELEVENLABS_API_KEY"))

voices = Voices.from_api()

#Reference ElevenLabs API Docs to determine voice index based off premade voices and custom voices
VOICE_INDEX = 40

voicing = voices[VOICE_INDEX]
voicing.settings.stability = 0.28
voicing.settings.similarity_boost = 0.98
MODEL_VERSION = "eleven_monolingual_v1"
user = User.from_api()

TWITCH_CHANNEL = ['Twitch Channel Name Here']

BIT_THRESHOLD = 20  # Default bit donation threshold to activate (API pricing varies, especially on length. I estimated about 10-15 cents per message on Chat-GPT 3.5-turbo on the ElevenLabs Creator plan)


#Banned words array
banned_words = []
banned_words.sort(key=len, reverse=True)

TIMEOUT_DURATION = 15  # Default timeout duration

CHEERED_BITS = 0  # Initialize to 0

global LAST_AI_COMMAND_TIME
LAST_AI_COMMAND_TIME = 0  # Track the last time the !ai command was used.


def filter_message(text):
    text = re.sub(r'cheer[0-9]+\s+', '', text, flags=re.I)
    for word in banned_words:
        text = text.lower().replace(word.lower(), '' * len(word))
    text = text[:130]
    return text

def read_system_prompt():
    #
    try:
        with open(os.path.join(dir_path, OPENAI_PROMPT), 'a', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        print("Error: Prompt File not found.")
        return "TELL EVERYBODY THE PROMPT IS BROKEN"

class Bot(commands.Bot):
    def __init__(self):
        #Initialize Twitch Bot (Currently this is via un-secured oauth)
        super().__init__(token='oauth:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx', prefix='!', nick='Bot', initial_channels=TWITCH_CHANNEL)
        self.should_stop = False

    async def event_ready(self):
        print(f'Ready | {self.nick}')

    async def event_message(self, message):
        global LAST_AI_COMMAND_TIME
        CHEERED_BITS = 0  # Initialize to 0
        processed_content = message.content
        #Current bit donation prefixes
        cheered_matches = re.findall(r'BibleThump\d+|cheerwhal\d+|Corgo\d+|uni\d+|ShowLove\d+|Party\d+|SeemsGood\d+|Pride\d+|Kappa\d+|cheer\d+|FrankerZ\d+|HeyGuys\d+|DansGame\d+|EleGiggle\d+|TriHard\d+|Kreygasm\d+|4Head\d+|SwiftRage\d+|NotLikeThis\d+|FailFish\d+|VoHiYo\d+|PJSalt\d+|MrDestructoid\d+|bday\d+|RIPCheer\d+|Shamrock\d+', processed_content, re.IGNORECASE)
        if cheered_matches:
            CHEERED_BITS = sum([int(re.search(r"\d+", match).group()) for match in cheered_matches])
            # Remove the prefix
            processed_content = re.sub(r'BibleThump\d+|cheerwhal\d+|Corgo\d+|uni\d+|ShowLove\d+|Party\d+|SeemsGood\d+|Pride\d+|Kappa\d+|cheer\d+|FrankerZ\d+|HeyGuys\d+|DansGame\d+|EleGiggle\d+|TriHard\d+|Kreygasm\d+|4Head\d+|SwiftRage\d+|NotLikeThis\d+|FailFish\d+|VoHiYo\d+|PJSalt\d+|MrDestructoid\d+|bday\d+|RIPCheer\d+|Shamrock\d+', '', processed_content).strip()

        # Debugging statements
        #print(f'chat: {processed_content}')
        if CHEERED_BITS > 0:
            print(f'Bits: {CHEERED_BITS}')

        #print(f'Bit threshold value: {BIT_THRESHOLD}')

        # Process the !ai message irrespective of CHEERED_BITS threshold
        if time.time() - LAST_AI_COMMAND_TIME > TIMEOUT_DURATION:
            LAST_AI_COMMAND_TIME = time.time()

        # Remove the !ai prefix and filter the message
        filtered_message = filter_message(f"{message.author.name}: {processed_content.strip()}")

        #
        if CHEERED_BITS >= BIT_THRESHOLD:
            await generate_TWITCH_CHANNEL_talk(self, filtered_message, OPENAI_MODEL)

        if message.echo:
            return

        if CHAT_FLAG == True:
            with open(os.path.join(dir_path, CHAT_LOG_TXT), 'a', encoding='utf-8') as chat_log:
                chat_log.write(f"{message.author.name}: {message.content}\n")

    async def send_audio(self, data):
        #print("THE DATA IS: ", data)
        #print("model voice ai: ", MODEL_VERSION)
        #print(voicing)
        audio = generate(text=data, voice=voicing, model=MODEL_VERSION)
        play(audio)



async def generate_TWITCH_CHANNEL_talk(bot, latest_message, modeler):
    #print("Talking...")
    try:
        #print("Current OpenAI Model: ", modeler)
        print({latest_message})
        base_prompt = f"{PROMPT_TEMPLATE.format(message=latest_message)}"

        max_length = 3400
        prompt = base_prompt[:max_length]

        #print(read_system_prompt())
        response = openai.ChatCompletion.create(
            model=modeler,
            messages=[
                {
                    "role": "system",
                    "content": read_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        TWITCH_CHANNEL_talk = response.choices[0].message['content'][:360]
        print(TWITCH_CHANNEL_talk)
        print(f"\nCharacter Count: ",user.subscription.character_count)
        print(f"Character Limit: ",user.subscription.character_limit)
        await bot.send_audio(TWITCH_CHANNEL_talk)

    except Exception as e:
        print(f"Error generating TWITCH_CHANNEL talk: {e}")

async def main():
    # Prompt the user for input at the beginning
    user_choice = input("Press Enter to run the program OR type 't' then press Enter to Type a simulation message: ")
    if user_choice.lower() == 't':
        test_message()
    print("Loading...")
    bot = Bot()
    print("If it takes too long, try restarting.")
    await bot.start()

def test_message():
        while True:
            # Print the extracted values
            user = User.from_api()
            print(f"Character Count: ",user.subscription.character_count)
            print(f"Character Limit: ",user.subscription.character_limit)
            testMessage = input("Enter test message: ")
            generate_TWITCH_CHANNEL_talk_test(testMessage, OPENAI_MODEL)

def generate_TWITCH_CHANNEL_talk_test(data, modeler):
    #print("Talking...")

    #Modify Base Prompt as you like
    base_prompt = f"{PROMPT_TEMPLATE.format(message=data)}"
    max_length = 3400
    prompt = base_prompt[:max_length]

    response = openai.ChatCompletion.create(
        model=modeler,
        messages=[
            {
                "role": "system",
                "content": read_system_prompt()
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    TWITCH_CHANNEL_talk = response.choices[0].message['content'][:360]
    print(TWITCH_CHANNEL_talk)
    print(f"Character Count: ",user.subscription.character_count)
    print(f"Character Limit: ",user.subscription.character_limit)
    send_audio(TWITCH_CHANNEL_talk)

def send_audio(data):
        #print("THE DATA IS: ", data)
        #print("model voice ai: ", MODEL_VERSION)
        #print(voicing)
        audio = generate(text=data, voice=voicing, model=MODEL_VERSION)
        play(audio)

asyncio.run(main())
