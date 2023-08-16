**(WIP†)**

Combining the brains of OpenAI's Chat-GPT and ElevenLabs AI Voice capabilities, allow Twitch chat to interact with an AI chatbot during streams.

An interactive Twitch chatbot powered by OpenAI and ElevenLabs. This bot reads Twitch chat messages, processes them with OpenAI's Chat-GPT, and responds using ElevenLabs' voice synthesis.

![image](https://github.com/itsDevinReed/TwitchAIInteraction/assets/55592830/4f7c04b1-411c-4882-8431-ee421c171698)


**Features:**
Interactive Responses: Uses OpenAI's Chat-GPT models to generate relevant responses to chat messages.
Voice Synthesis: Utilizes ElevenLabs' API to convert text responses into voice.
Customizable Prompts: Dynamic prompts allow for personalized and varied responses.
Banned Words Filtering: Filters out banned words from chat messages for a more controlled interaction.

**Setup:**
Text Files: Create a prompt text file for Chat-GPT to dynamically update with during each chat interaction, optionally create a text file for chat log to be written to
Environment Variables: Set up the necessary environment variables (OPENAI_API_KEY, ELEVENLABS_API_KEY, and BASE_PATH for dynamic prompt text file modifications and optional chat log).
Python Dependencies: Ensure all required Python libraries are installed.
Run: Execute the main script to initiate the bot.

*†This version has been stripped of private info used in a working project, and modified to fit cleaner coding practices. Therefore it requires experienced user input and potentially troubleshooting.*
