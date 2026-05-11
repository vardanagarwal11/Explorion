import asyncio
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from jobs.worker import process_universal_job
from db.connection import init_db
import time

async def main():
    await init_db()
    
    # Generate unique job id
    job_id = f"job_{int(time.time())}"
    
    print(f"Starting pipeline test for 1706.03762 with job id: {job_id}")
    
    await process_universal_job(
        job_id=job_id,
        content_id="1706.03762",
        content_type="research_paper",
        video_mode="standard",
        narration_style="educational" # Valid enum value
    )

if __name__ == "__main__":
    asyncio.run(main())
