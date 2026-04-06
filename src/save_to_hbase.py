import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from storage.hbase_writer import main

if __name__ == "__main__":
    main()