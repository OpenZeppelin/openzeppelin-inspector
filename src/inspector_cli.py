import sys
from inspector.main import main
import asyncio

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
