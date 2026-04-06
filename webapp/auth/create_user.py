#!/usr/bin/env python3
"""
Create a user in the SQLite users database.

Usage (run from project root):
  python3 webapp/auth/create_user.py --username admin --password secret --role admin
  python3 webapp/auth/create_user.py --username lecturer --password secret --role lecturer --modules AAA,BBB
"""
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from werkzeug.security import generate_password_hash

from webapp.auth.db import create_user, get_user_by_username, init_db


def main():
    parser = argparse.ArgumentParser(description="Create a user account.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role",     default="lecturer", choices=["admin", "lecturer"])
    parser.add_argument(
        "--modules",
        default="",
        help="Comma-separated module codes for lecturers, e.g. AAA,BBB. Empty means all modules.",
    )
    args = parser.parse_args()

    init_db()

    existing, _ = get_user_by_username(args.username)
    if existing:
        print(f"ERROR: Username '{args.username}' already exists.")
        sys.exit(1)

    modules = [m.strip() for m in args.modules.split(",") if m.strip()] if args.modules else []
    pw_hash = generate_password_hash(args.password)

    create_user(args.username, pw_hash, args.role, modules)

    print(f"Created user '{args.username}'  role={args.role}  modules={modules or 'all'}")


if __name__ == "__main__":
    main()