import json
from pathlib import Path

from app.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "openapi.json"


def main():
    specification = app.openapi()
    OUTPUT_PATH.write_text(
        json.dumps(specification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI {specification['openapi']} salvo em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
