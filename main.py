
from app.core.logging_setup import setup_logging

logger = setup_logging()
logger.info("بدء تشغيل نظام القرطاسية")

from app.ui.main_window import run

if __name__ == "__main__":
    run()
