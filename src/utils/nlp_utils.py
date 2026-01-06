"""NLP utility functions"""

from typing import List, Dict, Any, Optional
from loguru import logger


def extract_entities(text: str, model: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract entities from text using NLP
    
    Args:
        text: Text to process
        model: Optional spaCy model name
        
    Returns:
        List of extracted entities
    """
    try:
        import spacy
        
        if model is None:
            model = "en_core_web_sm"
        
        try:
            nlp = spacy.load(model)
        except OSError:
            logger.warning(f"spaCy model {model} not found. Install with: python -m spacy download {model}")
            return []
        
        doc = nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
        
        return entities
    except ImportError:
        logger.warning("spaCy not available. Install with: pip install spacy")
        return []


def extract_relations(text: str, model: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract relations from text
    
    Args:
        text: Text to process
        model: Optional model name
        
    Returns:
        List of extracted relations
    """
    # Simple implementation - can be enhanced with relation extraction models
    entities = extract_entities(text, model)
    relations = []
    
    # Placeholder: in production, use relation extraction models
    # For now, return empty list
    return relations


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Chunk text into smaller pieces
    
    Args:
        text: Text to chunk
        chunk_size: Size of chunks
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            for punct in [". ", "! ", "? ", "\n\n", "\n"]:
                last_occurrence = text.rfind(punct, start, end)
                if last_occurrence != -1:
                    end = last_occurrence + len(punct)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

