import argparse
import json
import sys
import os
import datetime

# Add the grandparent directory (backend) to the Python path
# to allow importing modules like modules.retriever.arxiv.arxiv_retriever
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

try:
    from modules.retriever.arxiv import arxiv_retriever
except ImportError as e:
    print(json.dumps({"error": f"Failed to import arxiv_retriever module: {e}"}), file=sys.stderr)
    sys.exit(1)


def json_serial(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def main():
    parser = argparse.ArgumentParser(description="Call arXiv retriever functions.")
    # Add 'download_arxiv_id' to choices
    parser.add_argument('--function', required=True, choices=['extract_arxiv_ids', 'paper_download_arxiv_id', 'paper_get_metadata'], help='The function to call.')
    parser.add_argument("--text", help="Input text for extract_arxiv_ids.")
    parser.add_argument("--arxiv_id", help="ArXiv ID for downloading.")
    parser.add_argument("--output_dir", help="Output directory for downloads.")
    parser.add_argument("--file_path", help="File path for metadata extraction.")

    args = parser.parse_args()

    try:
        result = None
        if args.function == 'extract_arxiv_ids':
            if not args.text:
                raise ValueError("--text is required for extract_arxiv_ids")
            result = arxiv_retriever.extract_arxiv_ids(args.text)
        elif args.function == 'paper_download_arxiv_id':
            if not args.arxiv_id or not args.output_dir:
                raise ValueError("--arxiv_id and --output_dir are required for paper_download_arxiv_id")
            result = arxiv_retriever.paper_download_arxiv_id(args.arxiv_id, args.output_dir)
        elif args.function == 'paper_get_metadata':
            if not args.file_path:
                raise ValueError("--file_path is required for paper_get_metadata")
            result = arxiv_retriever.paper_get_metadata(args.file_path)

        # Print the result as JSON to stdout
        print(json.dumps(result, default=json_serial))

    except arxiv_retriever.ArxivPaperNotFoundError as e:
        print(json.dumps({"error": f"ArXiv paper not found: {e}", "type": "ArxivPaperNotFoundError"}), file=sys.stderr)
        sys.exit(1)
    except arxiv_retriever.ArxivDownloadError as e:
        print(json.dumps({"error": f"ArXiv download error: {e}", "type": "ArxivDownloadError"}), file=sys.stderr)
        sys.exit(1)
    except arxiv_retriever.ArxivRetrievalError as e:
        print(json.dumps({"error": f"ArXiv retrieval error: {e}", "type": "ArxivRetrievalError"}), file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(json.dumps({"error": f"File not found: {e}", "type": "FileNotFoundError"}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Catch any other exceptions
        print(json.dumps({"error": f"An error occurred in function '{args.function}': {e}", "type": type(e).__name__}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
