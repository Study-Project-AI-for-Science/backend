import argparse
import json
import sys
import os

# Add the parent directory (backend) to the Python path
# to allow importing modules from sibling directories (like modules/ollama)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    # Assuming ollama_client.py is in the same directory or accessible via PYTHONPATH
    from modules.ollama import ollama_client
    from modules.ollama.pdf_extractor import extract_pdf_content  # Import for extract_text
except ImportError as e:
    print(json.dumps({"error": f"Failed to import required modules: {e}"}), file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Call Ollama client functions.")
    parser.add_argument(
        "--function",
        required=True,
        choices=["get_paper_info", "get_paper_embeddings", "get_query_embeddings", "extract_text"],
        help="The function to call.",
    )
    parser.add_argument("--file_path", help="Path to the PDF file.")
    parser.add_argument("--query_string", help="The query string for embedding.")

    args = parser.parse_args()

    try:
        result = None
        if args.function == "get_paper_info":
            if not args.file_path:
                raise ValueError("--file_path is required for get_paper_info")
            result = ollama_client.get_paper_info(args.file_path)
        elif args.function == "get_paper_embeddings":
            if not args.file_path:
                raise ValueError("--file_path is required for get_paper_embeddings")
            result = ollama_client.get_paper_embeddings(args.file_path)
        elif args.function == "get_query_embeddings":
            if not args.query_string:
                raise ValueError("--query_string is required for get_query_embeddings")
            result = ollama_client.get_query_embeddings(args.query_string)
        elif args.function == "extract_text":
            if not args.file_path:
                raise ValueError("--file_path is required for extract_text")
            # Assuming extract_pdf_content returns the text directly
            result = extract_pdf_content(args.file_path)  # Use the imported function

        # Print the result as JSON to stdout
        if result is not None:
            print(json.dumps(result))
        else:
            # Handle cases where the function might return None successfully
            print(json.dumps(None))

    except FileNotFoundError:
        print(json.dumps({"error": f"File not found: {args.file_path}"}), file=sys.stderr)
        sys.exit(1)
    except ollama_client.TokenizerNotAvailableError as e:
        print(json.dumps({"error": f"Tokenizer error: {e}"}), file=sys.stderr)
        sys.exit(1)
    except ollama_client.OllamaInitializationError as e:
        print(json.dumps({"error": f"Ollama initialization error: {e}"}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Catch any other exceptions from the called functions
        print(json.dumps({"error": f"An error occurred in function '{args.function}': {e}", "type": type(e).__name__}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
