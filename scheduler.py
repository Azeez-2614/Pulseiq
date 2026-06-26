import logging
import sys
import requests
from apscheduler.schedulers.blocking import BlockingScheduler

# Import config for scheduler settings
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

scheduler = BlockingScheduler()

API_TRIGGER_URL = "http://localhost:8000/pipeline/trigger"

def trigger_pipeline_job():
    logging.info("Triggering data pipeline execution via API background task...")
    try:
        response = requests.post(API_TRIGGER_URL, timeout=10)
        if response.status_code == 200:
            logging.info(f"Pipeline successfully triggered: {response.json()}")
        else:
            logging.warning(f"Pipeline trigger returned status code {response.status_code}: {response.text}")
    except Exception as e:
        logging.error(f"Failed to connect to API to trigger pipeline: {e}")

if __name__ == "__main__":
    interval = config.PIPELINE_INTERVAL_MINUTES
    logging.info(f"Starting scheduler. Triggering API pipeline every {interval} minutes.")
    
    # Run once immediately on startup
    trigger_pipeline_job()
    
    scheduler.add_job(trigger_pipeline_job, "interval", minutes=interval)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stopped.")
