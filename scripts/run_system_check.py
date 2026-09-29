from app.services.system_validation_service import SystemValidationService
r=SystemValidationService.run()
for x in r["checks"]:print(("PASS " if x["ok"] else "FAIL ")+x["name"]+" :: "+x["detail"])
raise SystemExit(0 if r["healthy"] else 1)
