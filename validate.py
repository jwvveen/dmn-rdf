"""Validate DMN models: SHACL shapes plus the computed decision table checks.

    python validate.py                       # the example model
    python validate.py model.dmn other.ttl   # DMN XML (converted first) or RDF
    python validate.py --lang nl model.dmn   # messages in en, nl, de or fr

The work is done in scripts/valideer.py; see there.
"""
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "scripts"))
import valideer  # noqa: E402

if __name__ == "__main__":
    if not [a for a in sys.argv[1:] if not a.startswith("--") and a not in ("nl", "en", "de", "fr")]:
        sys.argv.append(str(HIER / "example.dmn"))
    raise SystemExit(valideer.main())
