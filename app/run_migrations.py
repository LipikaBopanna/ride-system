# app/run_migrations.py
import time
import logging
from sqlalchemy.exc import OperationalError
from app.common.db import engine, Base
# Import all models so Base knows about them!
from app.common import models 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables(retries=10, delay=3):
    """
    Tries to connect to the database and create all tables.
    Retries on failure to handle the DB not being ready yet.
    """
    logger.info("--- Database Migrator: Starting ---")
    for i in range(retries):
        try:
            logger.info(f"--- Database Migrator: Attempt {i+1}/{retries} to connect... ---")
            # This line creates all tables defined in your models.py
            Base.metadata.create_all(bind=engine)
            logger.info("--- Database Migrator: All tables created successfully. ---")
            return
        except OperationalError as e:
            logger.warning(f"--- Database Migrator: DB not ready, retrying in {delay}s... ({e}) ---")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"--- Database Migrator: Unexpected error: {e}")
            time.sleep(delay)
    
    logger.error("--- Database Migrator: FAILED to create tables after all retries. ---")
    exit(1) # Exit with an error code

if __name__ == "__main__":
    create_tables()