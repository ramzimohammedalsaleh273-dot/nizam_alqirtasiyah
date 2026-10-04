from app.core.logging_setup import setup_logging

logger = setup_logging()
logger.info("بدء تشغيل نظام القرطاسية")


def initialize_operational_layer():
    """تهيئة البنية التشغيلية قبل فتح الواجهة، بدون حذف بيانات."""
    from app.database.connection import get_session
    from app.services.enterprise_completion_service import EnterpriseCompletionService

    with get_session() as session:
        EnterpriseCompletionService.ensure(session)
        EnterpriseCompletionService.sync_inventory_mirror(session)
        session.commit()


from app.ui import main_window as _main_window
from app.ui.modern_dashboard import install as install_modern_shell

# استبدال الغلاف المرئي القديم بغلاف حديث، مع إبقاء وظائف الوحدات والخدمات الحالية.
install_modern_shell(_main_window.MainWindow)
run = _main_window.run

if __name__ == "__main__":
    initialize_operational_layer()
    run()
