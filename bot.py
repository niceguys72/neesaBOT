import discord
import asyncio
import os
import shutil
from dotenv import load_dotenv

# Load environment
load_dotenv()
TOKEN = os.getenv('TOKEN')
TARGET_USER_ID = int(os.getenv('TARGET_ID'))

# Playback settings
DELAY_BEFORE_PLAY = 3
LOOP_INTERVAL = 300  # 5 mins
AUDIO_FILE_PATH = "./audio.wav"
source = discord.FFmpegPCMAudio(
    AUDIO_FILE_PATH,
    executable="/root/.nix-profile/bin/ffmpeg",
    before_options="-nostdin",
    options="-vn"
)

print(f"Loaded TARGET_USER_ID: {TARGET_USER_ID}")
print(f"Token loaded (length: {len(TOKEN)})")

# Discord client
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
client = discord.Client(intents=intents)

# Globals for voice client and playback
vc: discord.VoiceClient | None = None
playback_task: asyncio.Task | None = None


async def start_playback(voice_client: discord.VoiceClient):
    """Loop audio playback for a voice client."""
    try:
        await asyncio.sleep(DELAY_BEFORE_PLAY)
        while True:
            voice_client.play(
                source,
                after=lambda e: print(f"Player error: {e}") if e else None
            )

            # Wait for current track to finish
            while voice_client.is_playing():
                await asyncio.sleep(1)

            await asyncio.sleep(LOOP_INTERVAL)

    except asyncio.CancelledError:
        # Stop audio cleanly when task is cancelled
        if voice_client.is_playing():
            voice_client.stop()
        raise
    except Exception as e:
        print(f"Playback error: {e}")


async def stop_playback():
    """Stop playback task and disconnect voice client cleanly."""
    global vc, playback_task

    if playback_task:
        playback_task.cancel()
        try:
            await playback_task
        except asyncio.CancelledError:
            pass
        playback_task = None

    if vc:
        if vc.is_playing():
            vc.stop()
        await vc.disconnect()
        vc = None


async def connect_and_start(channel: discord.VoiceChannel):
    """Connect to VC and start playback."""
    global vc, playback_task

    # Stop any existing playback first
    await stop_playback()

    # Connect and start looping playback
    vc = await channel.connect()
    playback_task = asyncio.create_task(start_playback(vc))


@client.event
async def on_voice_state_update(member, before, after):
    """Detect when the target user joins, leaves, or switches channels."""
    if member.id != TARGET_USER_ID:
        return

    # Target joined VC
    if after.channel and not before.channel:
        await connect_and_start(after.channel)

    # Target left VC
    elif not after.channel and before.channel:
        await stop_playback()

    # Target switched VC
    elif before.channel != after.channel and after.channel:
        await connect_and_start(after.channel)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    print("FFmpeg path:", shutil.which("ffmpeg"))
    print("Audio exists:", os.path.exists(AUDIO_FILE_PATH))
    print("Audio absolute path:", os.path.abspath(AUDIO_FILE_PATH))

client.run(TOKEN)
