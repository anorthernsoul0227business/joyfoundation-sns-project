import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app


def main() -> None:
    try:
        schema = app.openapi()
        output_path = ROOT_DIR / "openapi.json"
        output_path.write_text(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"OpenAPI schema written to {output_path}")
    except Exception as exc:
        print(f"Failed to generate OpenAPI schema: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
