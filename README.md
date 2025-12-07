# Oicana Example FastAPI

Small example Python web service with [FastAPI](https://fastapi.tiangolo.com/) that uses Oicana for PDF templating.

## Getting Started

1. Install dependencies: `uv sync`
2. Start the service: `uv run python main.py` or `uv run uvicorn main:app --host 127.0.0.1 --port 3003`
3. Visit http://127.0.0.1:3003/docs for the Swagger documentation

## Licensing

The code of this example project is licensed under the [MIT license](LICENSE).

But please be aware that the dependency `oicana` [is licensed under PolyForm Noncommercial License 1.0.0][oicana-license].


[oicana-license]: https://github.com/oicana/oicana?tab=readme-ov-file#licensing
