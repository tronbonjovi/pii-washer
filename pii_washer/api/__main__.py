import argparse

import uvicorn

from .config import DEFAULT_PORT


def main():
    parser = argparse.ArgumentParser(description="PII Washer API Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()
    uvicorn.run("pii_washer.api.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
