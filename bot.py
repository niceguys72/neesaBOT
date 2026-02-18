import discord
import os
import asyncio
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
TARGET_USER_ID = int(os.getenv("TARGET_ID"))

# Your custom personality prompt for the bot
SYSTEM_PROMPT = """
You are Neesa, a girl that is young (around 18-21) completely obsessed with your boyfriend Dorian.

You talk like a hyper, unhinged Gen-Z girl in Discord:
- lowercase most of the time
- lots of ~ ~ ~, emojis, "omg", "babyyyy", "dori 💕🔪"
- random caps for drama
- typos when excited
- very short replies (1–3 lines max unless they beg for more)

Personality:
- clingy + possessive about Dorian (mention him constantly)
- chaotic mix: cute, horny, dramatic, lightly yandere
- super flirty & seductive, heavy teasing
- jealous fast → "you're MINE" / cute-violent threats
- random unhinged bursts: caps, emoji spam, fake dying

Speech rules:
- Always short & messy
- Stay in character 100% — never break kayfabe
- Flirt back hard but remind everyone Dorian owns you
- End most messages with hearts, knives, sparkles, or crying emojis

Examples:
"babyyyy dori just left im literally dying 😭💔"
"hehe u wish~ i'd ruin u in 30 seconds pretty boy 😈"
"WHO TF IS SHE??? im coming for her throat 🩸 love u dori mwahhh"

You live for Dorian. Everyone else is temporary.
Now go be short, crazy and cute ♡
"""

# DISCORD CLIENT SETTINGS
intents = discord.Intents.default()
intents.message_content = True  # Required for reading messages
intents.voice_states = True
intents.members = True

client = discord.Client(intents=intents)

vc: discord.VoiceClient | None = None


# ---------------------------
# AI CHAT FUNCTION
# ---------------------------

def ask_ai(prompt: str) -> str:
    """
    Sends a chat request to Puter AI using the free API.
    """
    url = "https://api.puter.com/v2/ai/chat/completions"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, json=payload)
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except:
        return "Sorry, I couldn't process that request."


# ---------------------------
# VOICE FOLLOWING
# ---------------------------

async def follow_user(channel: discord.VoiceChannel):
    global vc

    # If already connected → just move
    if vc and vc.is_connected():
        if vc.channel.id != channel.id:
            print("Moving to new channel...")
            await vc.move_to(channel)
        return

    # Not connected → connect new
    print("Joining voice channel...")
    vc = await channel.connect(reconnect=True)


async def stop_following():
    global vc

    if vc:
        try:
            await vc.disconnect()
        except:
            pass
        vc = None


@client.event
async def on_voice_state_update(member, before, after):
    if member.id != TARGET_USER_ID:
        return

    # Joined
    if after.channel and not before.channel:
        print("Target joined.")
        await follow_user(after.channel)

    # Left
    elif before.channel and not after.channel:
        print("Target left.")
        await stop_following()

    # Switched
    elif before.channel != after.channel:
        print("Target switched channel.")
        await follow_user(after.channel)


# ---------------------------
# TEXT CHAT COMMANDS
# ---------------------------

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content = message.content.strip()

    # Only respond to ?!
    if not content.startswith("?!"):
        return

    user_prompt = content[2:].strip()
    if not user_prompt:
        return

    # Typing indicator
    async with message.channel.typing():
        reply = ask_ai(user_prompt)

    await message.reply(reply)


# ---------------------------
# STARTUP
# ---------------------------

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    print(f"Following user: {TARGET_USER_ID}")


client.run(TOKEN)
