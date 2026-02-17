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
FFMPEG_PATH = shutil.which("ffmpeg") or "ffmpeg"

print(f"Loaded TARGET_USER_ID: {TARGET_USER_ID}")
print(f"Token loaded (length: {len(TOKEN)})")

# Discord client
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

# Globals
vc: discord.VoiceClient | None = None
playback_task: asyncio.Task | None = None


async def start_playback(voice_client: discord.VoiceClient):
    """Loop audio playback safely."""
    try:
        await asyncio.sleep(DELAY_BEFORE_PLAY)

        while True:
            if not voice_client.is_connected():
                print("Voice client disconnected. Stopping loop.")
                break

            print("Starting playback...")

            source = discord.FFmpegPCMAudio(
                AUDIO_FILE_PATH,
                executable=FFMPEG_PATH,
                before_options="-nostdin",
                options="-vn"
            )

            voice_client.play(
                source,
                after=lambda e: print(f"Player error: {e}") if e else print("Playback finished")
            )

            while voice_client.is_playing():
                await asyncio.sleep(1)

            print("Waiting for next loop...")
            await asyncio.sleep(LOOP_INTERVAL)

    except asyncio.CancelledError:
        print("Playback task cancelled.")
        if voice_client.is_playing():
            voice_client.stop()
        raise
    except Exception as e:
        print(f"Playback error: {e}")


async def stop_playback():
    """Stop playback and disconnect cleanly."""
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
        if vc.is_connected():
            await vc.disconnect()
        vc = None


async def connect_and_start(channel: discord.VoiceChannel):
    """Connect and start playback safely."""
    global vc, playback_task

    # Prevent duplicate connections
    if vc and vc.is_connected():
        print("Already connected.")
        return

    await stop_playback()

    print("Connecting to voice...")
    vc = await channel.connect(reconnect=True)

    # Ensure not muted/deafened
    await vc.guild.change_voice_state(
        channel=channel,
        self_mute=False,
        self_deaf=False
    )

    playback_task = asyncio.create_task(start_playback(vc))


@client.event
async def on_voice_state_update(member, before, after):
    """Detect target user voice changes."""
    if member.id != TARGET_USER_ID:
        return

    # Joined
    if after.channel and not before.channel:
        print("Target joined voice.")
        await connect_and_start(after.channel)

    # Left
    elif not after.channel and before.channel:
        print("Target left voice.")
        await stop_playback()

    # Switched channels
    elif before.channel != after.channel and after.channel:
        print("Target switched channels.")
        await connect_and_start(after.channel)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    print("FFmpeg path:", shutil.which("ffmpeg"))
    print("Audio exists:", os.path.exists(AUDIO_FILE_PATH))
    print("Audio absolute path:", os.path.abspath(AUDIO_FILE_PATH))


client.run(TOKEN)
