"""Sensing / ingestion layer (design.md Section 6).

v1: receipt ingestion (additions are observable at purchase time). The VLM
image->JSON step (Qwen-VL on the Mac Studio via Ollama) is an injectable seam;
this layer turns either a structured line-item list (VLM output) or plain receipt
text into pantry deltas.
"""

from .receipt import (  # noqa: F401
    parse_receipt_text,
    ingest_receipt,
    ReceiptLine,
    ReceiptResult,
)
