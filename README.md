**(WIP†)**

Combining the brains of OpenAI's Chat-GPT and ElevenLabs AI Voice capabilities, allow Twitch chat to interact with an AI chatbot during streams.

An interactive Twitch chatbot powered by OpenAI and ElevenLabs. This bot reads Twitch chat messages, processes them with OpenAI's Chat-GPT, and responds using ElevenLabs' voice synthesis.

<img src="https://github.com/itsDevinReed/TwitchAIInteraction/assets/55592830/888bd6ca-fd14-4477-aab1-ea96d4ed9429" width="600">




**Features:**
Interactive Responses: Uses OpenAI's Chat-GPT models to generate relevant responses to chat messages.
Voice Synthesis: Utilizes ElevenLabs' API to convert text responses into voice.
Customizable Prompts: Dynamic prompts allow for personalized and varied responses.
Banned Words Filtering: Filters out banned words from chat messages for a more controlled interaction.

**Setup:**
Text Files: Create a prompt text file for Chat-GPT to dynamically update with during each chat interaction, optionally create a text file for chat log to be written to
Environment Variables: The app will prompt for necessary variables (API keys, Twitch OAuth Token, directories). WARNING: These are currently stored in plaintext as a configuration file named ".env" in the app directory.
Python Dependencies: Ensure all required Python libraries are installed.
Run: Execute the main script app.py to initiate the bot.
