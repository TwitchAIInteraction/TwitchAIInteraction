Combining the brains of OpenAI's Chat-GPT and ElevenLabs AI Voice capabilities, allow Twitch chat to interact with an AI chatbot during streams.

An interactive Twitch chatbot powered by OpenAI and ElevenLabs. This bot reads Twitch chat messages, processes them with OpenAI's GPT-3 model, and responds using ElevenLabs' voice synthesis.

Features:
Interactive Responses: Uses OpenAI's GPT-3 model to generate relevant responses to chat messages.
Voice Synthesis: Utilizes ElevenLabs' API to convert text responses into voice.
Customizable Prompts: Dynamic prompts allow for personalized and varied responses.
Banned Words Filtering: Filters out banned words from chat messages for a more controlled interaction.

Setup:
Environment Variables: Set up the necessary environment variables (OPENAI_API_KEY, ELEVENLABS_API_KEY, and BASE_PATH for dynamic prompt text file modifications and optional chat log).
Python Dependencies: Ensure all required Python libraries are installed.
Run: Execute the main script to initiate the bot.
