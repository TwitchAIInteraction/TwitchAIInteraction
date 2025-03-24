Combining the OpenAI's GPT-4o-mini NLP and ElevenLabs AI Voice capabilities, allow Twitch chat to interact with an AI chatbot during streams.†

An interactive Twitch chatbot powered by OpenAI and ElevenLabs. This bot reads Twitch chat messages, processes them with OpenAI's Chat-GPT, and responds using ElevenLabs' voice synthesis.

![Diagram](https://github.com/user-attachments/assets/b7e006ce-b148-443c-b9f9-2693810dae7d)


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


**(WIP†)**
This is the template upon which I make customized versions of the app for Twitch streamers. 
If you are interested in having a customized version designed for your channel (including more advanced functionality) feel free to reach out to me.
