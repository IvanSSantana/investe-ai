from typing import List
from docling_core.types.doc.document import DoclingDocument
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

tokenizer = HuggingFaceTokenizer(
    tokenizer=AutoTokenizer.from_pretrained("intfloat/multilingual-e5-large"),
    max_tokens=6000
)

chunker = HybridChunker(
    tokenizer=tokenizer,
    merge_peers=True  
)
