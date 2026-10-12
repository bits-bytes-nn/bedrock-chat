import logging
import os

# Modules log through child loggers of "app", so the level is configured once here.
logging.getLogger(__name__).setLevel(os.environ.get("LOG_LEVEL", "INFO"))
