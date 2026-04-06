import os
import sys
from contextlib import contextmanager

import happybase

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from configs import config

DEFAULT_TIMEOUT = 10_000   # ms — writes, reads, model results
SCAN_TIMEOUT    = 60_000   # ms — full-table scans (student cache sync)


@contextmanager
def hbase_connection(timeout=DEFAULT_TIMEOUT):
    connection = None
    try:
        connection = happybase.Connection(
            host=config.HBASE_HOST,
            port=config.HBASE_PORT,
            timeout=timeout,
        )
        connection.open()
        yield connection
    finally:
        if connection:
            connection.close()


def ensure_table(connection, table_name, column_families):
    if table_name.encode() not in connection.tables():
        print(f">>> [HBASE] Table '{table_name}' not found — creating...")
        connection.create_table(table_name, {cf: dict() for cf in column_families})
        print(f">>> [HBASE] Table '{table_name}' created.")