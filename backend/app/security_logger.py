import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    filename="security.log",
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("security")