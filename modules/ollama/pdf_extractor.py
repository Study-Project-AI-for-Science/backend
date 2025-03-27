import json
import os
from collections import defaultdict  
from unstructured.partition.pdf import partition_pdf


def extract_pdf_content(pdf_path, max_context_length=512):
    """
    Extracts structured content (titles + associated elements) from a PDF file.

    Args:
        pdf_path (str): path to the PDF file
        max_context_length(int): max context length of respective embedding model 
    Returns:
    content(list): a list of extracted chunks where each chunks is a dict. The chunks content can be accessed under argument "content"

    """
    print(f"Processing PDF: {pdf_path}")

    # Parse the PDF into elements using unstructured
    chunks = partition_pdf(
        filename=pdf_path,
        strategy="hi_res",
        extract_images_in_pdf=False,
        chunking_strategy="by_title",
        max_characters=max_context_length,
    )

    content = []
    current_chapter = None
    prev_title = None

    # extract metadata from each chunk from Unstructured object
    for index, chunk in enumerate(chunks):
        if hasattr(chunk, "metadata") and hasattr(chunk.metadata, "orig_elements"):
            for element in chunk.metadata.orig_elements:
                element_type = type(element).__name__
                element_text = getattr(element, "text", None)

                element_data = {
                    "page_number": getattr(chunk.metadata, "page_number", None),
                    "type": element_type,
                    "content": element_text,
                    "chunk_position": index,
                    "current_chapter": current_chapter,
                }

                # Handle titles
                if element_type == "Title":
                    element_data["prev_title"] = prev_title
                    prev_title = element_text
                    current_chapter = element_text  # Update chapter marker

                content.append(element_data)

    # Set next_title for all titles
    title_elements = [item for item in content if item["type"] == "Title"]
    for i in range(len(title_elements) - 1):
        title_elements[i]["next_title"] = title_elements[i + 1]["content"]

    if title_elements:
        title_elements[-1]["next_title"] = ""
        
    # Debugging
    # print(f" Total elements extracted: {len(content)}")
    # print(f" Titles found: {len(title_elements)}")
    # for t in title_elements:
    #    print(f"  - Title: {t['content'][:60]!r} | Prev: {t.get('prev_title')!r} | Next: {t.get('next_title')!r}")

    # Group and count by chapter
    # chapter_counts = defaultdict(int)
    # for c in content:
    #     chapter_counts[c["current_chapter"]] += 1

    # print("\n Element count by chapter:")
    # for chapter, count in chapter_counts.items():
    #    print(f"  - {repr(chapter)[:60]}: {count} elements")

    # Print a few sample non-title entries
    # print("\n Sample non-title elements:")
    # for item in content:
    #     if item["type"] != "Title":
    #         print(f"  [{item['type']}] Pg {item['page_number']} | In: {repr(item['current_chapter'])[:40]}")
    #         print(f"    {item['content'][:100]!r}")
    #         break  # just show one

    return content

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF using the unstructured library.

    Args:
        pdf_path (str): Path to the PDF file.
        output_file (str, optional): Path to save the extracted text. If None, text is not saved.

    Returns:
        str: Extracted text from the PDF.
    """
    elements = partition_pdf(filename=pdf_path)
    extracted_text = "\n".join(str(element) for element in elements)

    return extracted_text
