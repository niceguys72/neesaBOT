import discord
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('TOKEN')
TARGET_USER_ID_STR = os.getenv('TARGET_ID')
TARGET_USER_ID = int(TARGET_USER_ID_STR)
DELAY_BEFORE_PLAY = 3
LOOP_INTERVAL = 300  # 5 mins
print(f"Loaded TARGET_USER_ID: {TARGET_USER_ID}")
print(f"Token loaded (length: {len(TOKEN)})")
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True  # Needed for fetch_member
client = discord.Client(intents=intents)

vc = None
playback_task = None

async def start_playback(voice_client: discord.VoiceClient):
    try:
        await asyncio.sleep(DELAY_BEFORE_PLAY)
        while True:
            source = discord.FFmpegPCMAudio("./audio.mp3")

            voice_client.play(
                source,
                after=lambda e: print(f'Player error: {e}') if e else None
            )

            while voice_client.is_playing():
                await asyncio.sleep(1)

            await asyncio.sleep(LOOP_INTERVAL)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Playback error: {e}")

@client.event
async def on_voice_state_update(member, before, after):
    global vc
    global playback_task

    if member.id == TARGET_USER_ID:
        if after.channel and not before.channel:  # Target joined a VC
            if vc:
                await vc.disconnect()
            vc = await after.channel.connect()
            if playback_task:
                playback_task.cancel()
            playback_task = asyncio.create_task(start_playback(vc))
        elif not after.channel and before.channel:  # Target left VC
            if vc:
                vc.stop()
                if playback_task:
                    playback_task.cancel()
                await vc.disconnect()
                vc = None
        elif before.channel != after.channel and after.channel:  # Target switched VC
            if vc:
                await vc.move_to(after.channel)
            else:
                vc = await after.channel.connect()
                if playback_task:
                    playback_task.cancel()
                playback_task = asyncio.create_task(start_playback(vc))
    elif member == client.user:
        if not after.channel and before.channel:  # Bot was disconnected
            guild = before.channel.guild
            try:
                target_member = await guild.fetch_member(TARGET_USER_ID)
                if target_member.voice and target_member.voice.channel:
                    if vc:
                        await vc.disconnect()
                    vc = await target_member.voice.channel.connect()
                    if playback_task:
                        playback_task.cancel()
                    playback_task = asyncio.create_task(start_playback(vc))
            except Exception as e:
                print(f"Reconnect error: {e}")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

client.run(TOKEN)