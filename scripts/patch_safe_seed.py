from pathlib import Path
p=Path("scripts/safe_operational_seed.py")
s=p.read_text(encoding="utf-8")
s=s.replace('verb="INSERT OR IGNORE" if ignore else "INSERT"\n    sql=f\'INSERT {verb} INTO "{table}"', 'verb="INSERT OR IGNORE" if ignore else "INSERT"\n    sql=f\'{verb} INTO "{table}"')
p.write_text(s,encoding="utf-8")
print("PATCH: SUCCESS")
