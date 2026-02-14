"""One-shot Telegram auth helper for Razvedka.

Usage:
  Step 1: Run WITHOUT TELEGRAM_CODE to trigger code send:
    docker service create ... -e TELEGRAM_STEP=request ...
  Step 2: Run WITH TELEGRAM_CODE=<received_code>:
    docker service create ... -e TELEGRAM_STEP=verify -e TELEGRAM_CODE=12345 ...
"""
import asyncio
import os
import sys


def read_secret(name):
    path = f"/run/secrets/{name}"
    try:
        return open(path).read().strip()
    except FileNotFoundError:
        return None


async def main():
    from telethon import TelegramClient

    api_id = read_secret("telegram_api_id")
    api_hash = read_secret("telegram_api_hash")
    phone = read_secret("telegram_phone")

    if not all([api_id, api_hash, phone]):
        print("ERROR: Missing secrets (telegram_api_id, telegram_api_hash, telegram_phone)")
        sys.exit(1)

    step = os.environ.get("TELEGRAM_STEP", "request")
    client = TelegramClient("/data/razvedka", int(api_id), api_hash)

    if step == "request":
        # Step 1: Connect and request auth code
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"ALREADY AUTHORIZED as {me.first_name} (id={me.id})")
            print("Session is valid - no re-auth needed!")
            await client.disconnect()
            return
        # Send code request
        result = await client.send_code_request(phone)
        print(f"CODE SENT to {phone} via Telegram")
        print(f"Phone code hash: {result.phone_code_hash}")
        print("Now run step 2 with TELEGRAM_CODE=<code> and TELEGRAM_HASH=<hash>")
        await client.disconnect()

    elif step == "verify":
        code = os.environ.get("TELEGRAM_CODE", "")
        phone_hash = os.environ.get("TELEGRAM_HASH", "")
        if not code:
            print("ERROR: TELEGRAM_CODE not set")
            sys.exit(1)
        if not phone_hash:
            print("ERROR: TELEGRAM_HASH not set")
            sys.exit(1)
        await client.connect()
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_hash)
        me = await client.get_me()
        print(f"SUCCESS! Authenticated as {me.first_name} (id={me.id})")
        print("Session saved to /data/razvedka.session")
        await client.disconnect()

    else:
        print(f"Unknown TELEGRAM_STEP: {step}")
        sys.exit(1)


asyncio.run(main())
