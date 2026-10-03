"""Entry point: `review-responder` (or `python -m review_responder`)."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="review-responder", description="Run the Review Responder web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes.")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("google-auth", help="Sign in to Google Business Profile (one time).")
    args = parser.parse_args()

    if args.command == "google-auth":
        from .google_business import GoogleError, authorize

        try:
            authorize()
        except GoogleError as e:
            sys.exit(f"error: {e}")
        print("Google sign-in saved. Restart the app to use live reviews.")
        return

    import uvicorn

    print(f"Review Responder running at http://{args.host}:{args.port}")
    uvicorn.run("review_responder.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
