"""Fail a release build when the tag and manifest version differ."""

import json
import sys
from pathlib import Path

expected = sys.argv[1] if len(sys.argv) == 2 else None
manifest = json.loads(Path("custom_components/madrid_air_quality/manifest.json").read_text())
actual = manifest["version"]
if not expected or expected != actual:
    raise SystemExit(f"release tag {expected!r} does not match manifest version {actual!r}")
print(f"validated v{actual}")
