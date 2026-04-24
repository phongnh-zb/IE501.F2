#!/usr/bin/env python3
"""
Create a user in the SQLite users database.

Usage (run from project root):
  python3 webapp/auth/create_user.py \
    --username 24410335 \
    --password secret \
    --role lecturer \
    --full-name "Phong Nguyen" \
    --email "24410335@ms.uit.edu.vn" \
    --modules AAA,BBB,CCC,DDD,EEE,FFF,GGG
"""
import argparse
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from werkzeug.security import generate_password_hash

from webapp.auth.db import create_user, get_user_by_email, get_user_by_username, init_db


def _valid_email(value):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid email address.")
    return value


def main():
    parser = argparse.ArgumentParser(description="Create a user account.")
    parser.add_argument("--username",  required=True,
                        help="Login username (unique)")
    parser.add_argument("--password",  required=True,
                        help="Login password")
    parser.add_argument("--role",      default="lecturer", choices=["admin", "lecturer"],
                        help="Account role: admin or lecturer (default: lecturer)")
    parser.add_argument("--full-name", required=True, dest="full_name",
                        help="Full display name, e.g. 'Phong Nguyen'")
    parser.add_argument("--email",     required=True, type=_valid_email,
                        help="Institutional email address")
    parser.add_argument("--modules",   default="",
                        help="Comma-separated module codes for lecturers, e.g. AAA,BBB,CCC. "
                             "Empty means access to all modules.")
    args = parser.parse_args()

    init_db()

    existing, _ = get_user_by_username(args.username)
    if existing:
        print(f"ERROR: Username '{args.username}' already exists.")
        sys.exit(1)
        
    existing, _ = get_user_by_email(args.email)
    if existing:
        print(f"ERROR: Email '{args.email}' already exists.")
        sys.exit(1)

    modules = [m.strip() for m in args.modules.split(",") if m.strip()] if args.modules else []
    pw_hash = generate_password_hash(args.password)

    try:
        create_user(
            username      = args.username,
            password_hash = pw_hash,
            role          = args.role,
            modules       = modules,
            full_name     = args.full_name,
            email         = args.email,
            created_by    = "cli",
        )
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(
        f"Created: '{args.username}' ({args.full_name})"
        f"  role={args.role}"
        f"  modules={modules or 'all'}"
        f"  full_name={args.full_name}"
        f"  email={args.email}"
    )


if __name__ == "__main__":
    main()