"""Fail when credential inputs, generated headers, or firmware artifacts enter the tree."""
import re
from pathlib import Path


root = Path(__file__).resolve().parents[1]
forbidden_names = {"private_crt.h", "public_identity.h", "key.pem", "serial.txt", "sig.bin"}
forbidden_suffixes = {".hex", ".eep", ".elf", ".bin", ".map"}
allowed = {root / "tests" / "stubs" / "public_identity.h"}
violations = []
for path in root.rglob("*"):
    if not path.is_file() or ".git" in path.parts or path in allowed:
        continue
    if path.name.lower() in forbidden_names or path.suffix.lower() in forbidden_suffixes:
        violations.append(str(path.relative_to(root)))
    if path.suffix.lower() in {".h", ".cpp", ".ino", ".py", ".md", ".txt"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"BEGIN (?:RSA )?PRIVATE KEY", text):
            violations.append(str(path.relative_to(root)) + " (private key marker)")

if violations:
    raise SystemExit("Credential-safe release check failed:\n" + "\n".join(sorted(set(violations))))
print("PASS: no credential inputs, generated headers, or firmware artifacts found")

