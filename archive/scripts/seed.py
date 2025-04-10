"""
This script is intended solely for inserting papers in a simple manner. It uses the database
module's functions to properly handle file uploads, hash calculation, and database insertion.
"""

import os
import sys
from modules.database.database import paper_insert, DatabaseError, DuplicatePaperError


def main():
    if len(sys.argv) != 3:
        print("Usage: python seed.py <title> <pdf_path>")
        sys.exit(1)

    title = sys.argv[1]
    pdf_path = sys.argv[2]

    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} does not exist")
        sys.exit(1)

    try:
        paper_id = paper_insert(pdf_path, title, "Sample Author")
        print(f"Successfully inserted paper: {title} with ID: {paper_id}")
    except DuplicatePaperError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except DatabaseError as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
