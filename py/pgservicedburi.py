#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pgserviceparser",
# ]
# ///
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import quote, urlencode

import pgserviceparser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a pg_service.conf entry into a DATABASE_URI string."
    )
    parser.add_argument(
        "service_name",
        help="pg_service.conf service name (what you'd put after service=)",
    )
    parser.add_argument(
        "--config-file",
        dest="config_file",
        type=Path,
        help="Optional explicit path to pg_service.conf",
    )
    return parser.parse_args()


def config_to_uri(config: dict[str, str]) -> str:
    """Convert a pgserviceparser config dict to a DATABASE_URI string."""

    # Mandatory bits for a usable URI.
    dbname = config.get("dbname")
    if not dbname:
        raise ValueError("Service config is missing required 'dbname'.")

    user = config.get("user")
    password = config.get("password")
    host = config.get("host", "")
    port = config.get("port")

    auth = ""
    if user:
        auth = quote(user, safe="")
        if password:
            auth += f":{quote(password, safe='')}"
        auth += "@"

    host_part = ""
    if host:
        wrapped_host = host
        if ":" in host and not host.startswith("["):
            wrapped_host = f"[{host}]"  # IPv6 literal
        host_part = wrapped_host
        if port:
            host_part += f":{port}"
    elif port:
        host_part = f":{port}"

    netloc = f"{auth}{host_part}" if (auth or host_part) else auth
    path = f"/{quote(dbname, safe='')}"

    query_parts = {
        key: value
        for key, value in config.items()
        if key not in {"user", "password", "host", "port", "dbname"}
        and value not in (None, "")
    }
    query = urlencode(sorted(query_parts.items()), doseq=True) if query_parts else ""

    uri = f"postgresql://{netloc}{path}" if netloc else f"postgresql:///{quote(dbname, safe='')}"
    if query:
        uri += f"?{query}"
    return uri


def main() -> int:
    args = parse_args()
    try:
        config = pgserviceparser.service_config(
            args.service_name, args.config_file
        )
    except pgserviceparser.ServiceNotFound as exc:
        print(f"Service '{args.service_name}' was not found: {exc}", file=sys.stderr)
        return 2
    except pgserviceparser.ServiceFileNotFound as exc:
        print(f"Could not locate pg_service.conf: {exc}", file=sys.stderr)
        return 3

    try:
        uri = config_to_uri(config)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 4

    print(uri)
    return 0


if __name__ == "__main__":
    sys.exit(main())
