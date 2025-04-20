import argparse
import json
import sys
import os
import logging

# Add the grandparent directory (backend) to the Python path
# to allow importing modules like modules.latex_parser
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

# Configure logging for the script itself
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    from modules.latex_parser import latex_content_parser
    from modules.latex_parser import reference_parser

    # Ensure pandoc is available
    import pandoc
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    print(json.dumps({"error": f"Failed to import required modules: {e}"}), file=sys.stderr)
    sys.exit(1)
except FileNotFoundError as e:
    # Pandoc might raise FileNotFoundError if the executable isn't found
    logger.error(f"Pandoc executable not found: {e}")
    print(json.dumps({"error": f"Pandoc executable not found. Please ensure Pandoc is installed and in your PATH. Error: {e}"}), file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Call LaTeX parser functions.")
    parser.add_argument("--function", required=True, choices=["parse_latex_to_markdown", "extract_references"], help="The function to call.")
    parser.add_argument("--path", help="Path to the .tex file or directory for parsing to Markdown.")
    parser.add_argument("--source_dir", help="Path to the source directory for extracting references.")

    args = parser.parse_args()

    try:
        result = None
        if args.function == "parse_latex_to_markdown":
            if not args.path:
                raise ValueError("--path is required for parse_latex_to_markdown")
            logger.info(f"Calling parse_latex_to_markdown with path: {args.path}")
            result = latex_content_parser.parse_latex_to_markdown(args.path)
        elif args.function == "extract_references":
            if not args.source_dir:
                raise ValueError("--source_dir is required for extract_references")
            logger.info(f"Calling extract_references with source_dir: {args.source_dir}")
            result = reference_parser.extract_references(args.source_dir)

        # Print the result as JSON to stdout
        # For markdown, just print the string; for references, dump the list/dict
        if args.function == "parse_latex_to_markdown":
            print(json.dumps({"markdown": result}))  # Wrap markdown in a JSON object
        else:
            print(json.dumps(result))

    except FileNotFoundError as e:
        logger.error(f"File not found error during {args.function}: {e}")
        print(json.dumps({"error": f"File or directory not found: {e}", "type": "FileNotFoundError"}), file=sys.stderr)
        sys.exit(1)
    except pandoc.PandocError as e:
        logger.error(f"Pandoc conversion error: {e}")
        print(json.dumps({"error": f"Pandoc conversion failed: {e}", "type": "PandocError"}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.exception(f"An unexpected error occurred in function '{args.function}'")
        print(json.dumps({"error": f"An error occurred in function '{args.function}': {e}", "type": type(e).__name__}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
