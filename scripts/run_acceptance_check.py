from app.services.system_validation_service import SystemValidationService


def main():
    result = SystemValidationService.run()
    print("=" * 72)
    print("فحص قبول نظام القرطاسية")
    print("=" * 72)
    for item in result["checks"]:
        mark = "PASS" if item["ok"] else "FAIL"
        print(f"[{mark}] {item['name']}: {item['detail']}")
    print("=" * 72)
    print("الحالة النهائية:", "PASS" if result["healthy"] else "FAIL")
    return 0 if result["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
