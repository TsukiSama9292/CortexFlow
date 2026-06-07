import asyncio
from cortexflow.core.pipeline import Pipeline

async def main():
    print("CortexFlow Worker starting...")
    # Placeholder for worker loop
    while True:
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
