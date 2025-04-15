import pandoc
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)


def parse_latex_to_markdown(path: str) -> str:
    """
    Parse LaTeX content to Markdown using Pandoc.
    If a directory is provided, it will first find the main tex file in that directory.

    Args:
        path (str): Path to either a .tex file or a directory containing tex files

    Returns:
        str: Markdown content

    Raises:
        FileNotFoundError: If no main tex file is found in the directory
        pandoc.PandocError: If Pandoc conversion fails
        OSError: If changing directory or file access fails
    """
    # Check if input is a directory
    if os.path.isdir(path):
        logger.debug(f"Finding main tex file in directory: {path}")
        file_path = find_main_tex_file(path)
        if file_path is None:
            logger.error(f"No main tex file found in directory: {path}")
            raise FileNotFoundError(f"No main tex file found in directory: {path}")
        logger.info(f"Found main tex file: {file_path}")
    else:
        file_path = path
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            raise FileNotFoundError(f"File does not exist: {file_path}")

    # Get absolute path and directory of the input file
    abs_path = os.path.abspath(file_path)
    working_dir = os.path.dirname(abs_path)

    # Store current directory
    original_dir = os.getcwd()

    try:
        # Change to the LaTeX file's directory
        logger.debug(f"Changing to directory: {working_dir}")
        os.chdir(working_dir)

        # Convert LaTeX to Markdown using the file name only
        try:
            logger.debug(f"Converting {os.path.basename(abs_path)} from LaTeX to Markdown")
            doc = pandoc.read(file=os.path.basename(abs_path), format="latex")
            markdown_content = pandoc.write(doc, format="markdown")
            logger.info(f"Successfully converted {os.path.basename(abs_path)} to Markdown")
            return markdown_content
        except Exception as e:
            logger.error(f"Pandoc conversion failed: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Error during LaTeX to Markdown conversion: {str(e)}")
        raise
    finally:
        # Always change back to original directory
        logger.debug(f"Changing back to original directory: {original_dir}")
        os.chdir(original_dir)


def find_main_tex_file(directory: str) -> str:
    """
    Find the main .tex file in the given directory by looking for \begin{document}.
    Searches through the current directory and all subdirectories.

    Args:
        directory (str): The directory to search in

    Returns:
        str: Path to the main tex file, or None if not found

    Note:
        The function identifies the main tex file by searching for '\begin{document}'
        in the file content, which is a standard indicator of the main LaTeX document.
    """
    logger.debug(f"Searching for main tex file in {directory}")
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".tex"):
                file_path = os.path.join(root, file)
                try:
                    logger.debug(f"Checking file: {file_path}")
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if r"\begin{document}" in content:
                            logger.info(f"Found main tex file: {file_path}")
                            return file_path
                except UnicodeDecodeError:
                    logger.warning(f"Unicode decode error in file: {file_path}")
                    continue
                except IOError as e:
                    logger.warning(f"IO error reading file {file_path}: {str(e)}")
                    continue
    logger.warning(f"No main tex file found in directory: {directory}")
    return None


if __name__ == "__main__":
    # Configure logging for script execution
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Example usage
    folder_path = "../retriever/arxiv/Papers/1706.03762v7.Attention_Is_All_You_Need"  # Replace with your LaTeX file path
    try:
        file_path = find_main_tex_file(folder_path)
        if file_path:
            markdown_content = parse_latex_to_markdown(file_path)
            print(f"Successfully converted LaTeX to Markdown, length: {len(markdown_content)}")
            # Uncomment to save to file
            # with open("./output.md", "w") as f:
            #    f.write(markdown_content)
        else:
            print(f"No main tex file found in {folder_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
