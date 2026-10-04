from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE_DIR))

from app.services.dashboard.dashboard_service import DashboardService


def main():
    service = DashboardService()
    data = service.summary()

    print("=" * 70)
    print("اختبار خدمة لوحة التحكم")
    print("=" * 70)

    for key, value in data.items():
        print(f"{key}: {value}")

    print("=" * 70)
    print("نجح الاختبار")
    print("=" * 70)


if __name__ == "__main__":
    main()
