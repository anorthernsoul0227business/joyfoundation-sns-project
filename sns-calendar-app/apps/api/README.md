# API

FastAPI の最小骨格です。現時点では `/health` エンドポイントと OpenAPI 出力スクリプトのみを含みます。

```bash
poetry install
poetry run uvicorn app.main:app --reload
poetry run pytest
```

