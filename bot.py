import os
import asyncio
import subprocess
from asyncio import Queue
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FREE_LIMIT = 30
PREMIUM_LIMIT = 100

app = Client(
    "BulkRenameBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_files = {}
user_names = {}
user_thumb = {}
premium_users = set()

video_queue = Queue()
is_processing = False


def attach_cover(video, thumb, output):
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video,
        "-i", thumb,
        "-map", "0",
        "-map", "1",
        "-c", "copy",
        "-disposition:v:1", "attached_pic",
        output
    ]
    subprocess.run(cmd)


@app.on_message(filters.command("start"))
async def start(_, m: Message):

    await m.reply(
        "🚀 BULK VIDEO RENAMER BOT\n\n"
        "1. Send videos\n"
        "2. Send thumbnail (optional)\n"
        "3. Type /done\n"
        "4. Send new names"
    )


@app.on_message(filters.video)
async def collect_video(_, m: Message):

    uid = m.from_user.id

    user_files.setdefault(uid, [])

    limit = PREMIUM_LIMIT if uid in premium_users else FREE_LIMIT

    if len(user_files[uid]) >= limit:
        return await m.reply("❌ Limit reached")

    user_files[uid].append(m)

    await m.reply(f"Video Added {len(user_files[uid])}/{limit}")


@app.on_message(filters.photo)
async def thumb(_, m: Message):

    uid = m.from_user.id

    user_thumb[uid] = await m.download(file_name=f"{uid}.jpg")

    await m.reply("Thumbnail Saved")


@app.on_message(filters.command("done"))
async def done(_, m: Message):

    uid = m.from_user.id

    if uid not in user_files:
        return await m.reply("No videos found")

    user_names[uid] = []

    await m.reply("Send name for file 1")


@app.on_message(filters.text & ~filters.command(["start", "done"]))
async def names(_, m: Message):

    uid = m.from_user.id

    if uid not in user_files:
        return

    user_names.setdefault(uid, [])

    user_names[uid].append(m.text)

    total = len(user_files[uid])

    if len(user_names[uid]) < total:

        await m.reply(f"Send name {len(user_names[uid])+1}/{total}")

    else:

        await m.reply("Processing...")

        for i in range(total):
            await video_queue.put((uid, i))

        asyncio.create_task(process_queue())


async def process_queue():

    global is_processing

    if is_processing:
        return

    is_processing = True

    while not video_queue.empty():

        uid, idx = await video_queue.get()

        await process_single(uid, idx)

    is_processing = False


async def process_single(uid, idx):

    msg = user_files[uid][idx]

    name = user_names[uid][idx] + ".mp4"

    raw = await msg.download(file_name=f"{DOWNLOAD_DIR}/{uid}_{idx}.mp4")

    final = raw

    if uid in user_thumb:

        final = f"{DOWNLOAD_DIR}/{uid}_{idx}_final.mp4"

        attach_cover(raw, user_thumb[uid], final)

    await app.send_video(

        uid,
        final,
        file_name=name,
        caption=f"Renamed: {name}"

    )


print("BOT STARTED")

app.run()
