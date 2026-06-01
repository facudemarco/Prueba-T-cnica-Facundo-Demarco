import re

# Dictionary of common ligatures to expand
LIGATURES = {
    '\ufb00': 'ff',
    '\ufb01': 'fi',
    '\ufb02': 'fl',
    '\ufb03': 'ffi',
    '\ufb04': 'ffl',
    '\ufb05': 'ft',
    '\ufb06': 'st',
}

def replace_ligatures(text):
    """Replaces Unicode ligatures with their standard character combinations."""
    for ligature, replacement in LIGATURES.items():
        text = text.replace(ligature, replacement)
    return text

def clean_text(text):
    """Performs deep cleaning of raw text.
    
    - Replaces ligatures.
    - Normalizes smart quotes and dash variants.
    - Removes non-printable control characters.
    - Standardizes spaces and newlines.
    """
    if not text:
        return ""
        
    # Replace ligatures
    text = replace_ligatures(text)
    
    # Normalize quotes and dashes
    text = re.sub(r'[“”]', '"', text)
    text = re.sub(r'[‘’]', "'", text)
    text = re.sub(r'[—–−]', '-', text)
    
    # Remove control characters (except newline, carriage return, and tab)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Normalize whitespace inside lines
    lines = []
    for line in text.split('\n'):
        # Strip trailing/leading spaces but keep the line structure
        cleaned_line = re.sub(r'[ \t]+', ' ', line).strip()
        lines.append(cleaned_line)
        
    # Reconstruct text
    text = '\n'.join(lines)
    
    # Remove excessive blank lines (keep at most one consecutive blank line)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def split_into_sentences(text):
    """Splits Spanish text into sentences using simple regex, keeping abbreviations in mind."""
    # Common abbreviations in Spanish technical documents
    sentence_end = re.compile(
        r'(?<!\bej)(?<!\bpág)(?<!\bmín)(?<!\bmáx)(?<!\bvol)(?<!\bNiv)(?<!\bvs)(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚñ])'
    )
    return [s.strip() for s in sentence_end.split(text) if s.strip()]

def chunk_text(text, max_chunk_size=700, overlap=100):
    """Splits a document's clean text into semantic chunks.
    
    Tries to split by paragraphs first, then sentences, ensuring each chunk is 
    under `max_chunk_size` and overlaps with the previous chunk by `overlap` characters.
    """
    if not text:
        return []
        
    # Normalize text first
    text = clean_text(text)
    
    # If the total text is smaller than the chunk size, return it as a single chunk
    if len(text) <= max_chunk_size:
        return [text]
        
    # Split by paragraphs
    paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # If a single paragraph is too large, split it by sentences
        if len(para) > max_chunk_size:
            # Add what we have in current_chunk first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
                
            sentences = split_into_sentences(para)
            for sent in sentences:
                if len(sent) > max_chunk_size:
                    # Sentence itself is huge, force split it by words/chars
                    words = sent.split(' ')
                    temp_chunk = []
                    temp_len = 0
                    for word in words:
                        if temp_len + len(word) + 1 > max_chunk_size:
                            chunks.append(" ".join(temp_chunk))
                            # Keep overlap
                            overlap_words = []
                            overlap_len = 0
                            for w in reversed(temp_chunk):
                                if overlap_len + len(w) + 1 <= overlap:
                                    overlap_words.insert(0, w)
                                    overlap_len += len(w) + 1
                                else:
                                    break
                            temp_chunk = overlap_words + [word]
                            temp_len = sum(len(w) + 1 for w in temp_chunk)
                        else:
                            temp_chunk.append(word)
                            temp_len += len(word) + 1
                    if temp_chunk:
                        current_chunk = [" ".join(temp_chunk)]
                        current_length = temp_len
                else:
                    if current_length + len(sent) + 2 > max_chunk_size:
                        chunks.append("\n\n".join(current_chunk))
                        # Create overlap
                        overlap_sents = []
                        overlap_len = 0
                        for s in reversed(current_chunk):
                            if overlap_len + len(s) + 2 <= overlap:
                                overlap_sents.insert(0, s)
                                overlap_len += len(s) + 2
                            else:
                                break
                        current_chunk = overlap_sents + [sent]
                        current_length = sum(len(s) + 2 for s in current_chunk)
                    else:
                        current_chunk.append(sent)
                        current_length += len(sent) + 2
        else:
            # Paragraph fits, check if it can be added to the current chunk
            if current_length + len(para) + 2 > max_chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                # Create overlap using the last few lines or items
                overlap_items = []
                overlap_len = 0
                for item in reversed(current_chunk):
                    if overlap_len + len(item) + 2 <= overlap:
                        overlap_items.insert(0, item)
                        overlap_len += len(item) + 2
                    else:
                        break
                current_chunk = overlap_items + [para]
                current_length = sum(len(item) + 2 for item in current_chunk)
            else:
                current_chunk.append(para)
                current_length += len(para) + 2
                
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

def clean_and_chunk_documents(documents, max_chunk_size=1000, overlap=150):
    """Processes list of documents, cleans them, chunks them, and enriches chunks with context prefixes and metadata."""
    processed_chunks = []
    
    for doc in documents:
        raw_content = doc["content"]
        meta = doc["metadata"]
        
        # Clean text
        cleaned_text = clean_text(raw_content)
        if not cleaned_text:
            continue
            
        # Chunk text
        chunks = chunk_text(cleaned_text, max_chunk_size=max_chunk_size, overlap=overlap)
        
        for idx, chunk in enumerate(chunks):
            # Prepend source file info inside the text for better retrieval context
            filename = meta.get("filename", "desconocido")
            page_info = f" | Página: {meta['page']}" if "page" in meta else ""
            item_info = f" | ID: {meta['item_id']}" if "item_id" in meta else ""
            
            context_prefix = f"[Origen: {filename}{page_info}{item_info}]\n"
            full_chunk_text = context_prefix + chunk
            
            # Create a clean metadata dict
            chunk_metadata = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    chunk_metadata[k] = v
                elif isinstance(v, list):
                    chunk_metadata[k] = ", ".join(str(x) for x in v)
            
            chunk_metadata["chunk_index"] = idx
            
            processed_chunks.append({
                "content": full_chunk_text,
                "metadata": chunk_metadata
            })
            
    return processed_chunks
