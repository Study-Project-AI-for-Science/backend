import pytest

from modules.ollama.database import (
    _send_request_to_ollama,
    _extract_text_from_pdf,
    get_paper_embeddings,

)
