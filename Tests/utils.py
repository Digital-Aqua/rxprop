from asyncio import sleep


async def flush_event_loop():
    # Typically takes two passes to flush our events.
    # But we'll only fail if it takes more than 10 passes.
    for _ in range(10):
        await sleep(0)
