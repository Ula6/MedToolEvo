import unicodedata
import re

def run(payload: dict):
    # Validate input structure
    if not isinstance(payload, dict):
        raise ValueError("Input must be a dictionary")
    
    if "sources" not in payload or "queries" not in payload:
        raise ValueError("Missing 'sources' or 'queries' in input")
    
    sources = payload["sources"]
    queries = payload["queries"]
    
    if not isinstance(sources, list) or not isinstance(queries, list):
        raise ValueError("'sources' and 'queries' must be lists")
    
    # Validate sources
    source_ids = []
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            raise ValueError("Each source must be a dictionary")
        if "source_id" not in s or "text" not in s:
            raise ValueError("Each source must have 'source_id' and 'text'")
        if not isinstance(s["source_id"], str) or len(s["source_id"]) == 0:
            raise ValueError("Source IDs must be non-empty strings")
        if not isinstance(s["text"], str):
            raise ValueError("Source text must be a string")
        if s["source_id"] in source_ids:
            raise ValueError("Duplicate source IDs found")
        source_ids.append(s["source_id"])
    
    # Validate queries
    query_ids = []
    for i, q in enumerate(queries):
        if not isinstance(q, dict):
            raise ValueError("Each query must be a dictionary")
        if "query_id" not in q or "text" not in q:
            raise ValueError("Each query must have 'query_id' and 'text'")
        if not isinstance(q["query_id"], str) or len(q["query_id"]) == 0:
            raise ValueError("Query IDs must be non-empty strings")
        if not isinstance(q["text"], str) or len(q["text"].strip()) == 0:
            raise ValueError("Query texts cannot be empty or whitespace-only")
        if q["query_id"] in query_ids:
            raise ValueError("Duplicate query IDs found")
        query_ids.append(q["query_id"])
    
    # Define normalization function
    def normalize_text(text):
        normalized_chars = []
        for char in text:
            norm_char = unicodedata.normalize('NFKC', char).casefold()
            normalized_chars.append(norm_char)
        normalized = ''.join(normalized_chars)
        # Collapse whitespace runs to single ASCII space
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    # Preprocess sources
    source_data = []
    for s in sources:
        original_text = s["text"]
        normalized_text = normalize_text(original_text)
        source_data.append({
            "source_id": s["source_id"],
            "original_text": original_text,
            "normalized_text": normalized_text
        })
    
    # Preprocess queries
    query_data = []
    for q in queries:
        original_query = q["text"]
        normalized_query = normalize_text(original_query)
        query_data.append({
            "query_id": q["query_id"],
            "original_query": original_query,
            "normalized_query": normalized_query
        })
    
    # Search and map
    results = []
    unsupported_query_ids = []
    
    for q in query_data:
        query_id = q["query_id"]
        normalized_query = q["normalized_query"]
        matches = []
        seen_spans = set()
        
        for s in source_data:
            source_id = s["source_id"]
            original_text = s["original_text"]
            normalized_text = s["normalized_text"]
            
            # Find all overlapping occurrences of the normalized query
            start_indices = []
            search_start = 0
            while True:
                pos = normalized_text.find(normalized_query, search_start)
                if pos == -1:
                    break
                start_indices.append(pos)
                search_start = pos + 1  # Allow overlaps
            
            for start_pos in start_indices:
                # Map back to original Unicode code-point span
                # We need to find the actual start and end indices in original text
                # such that normalized(original_text[start:end]) == normalized_query
                
                # Count characters until we reach start_pos in normalized string
                char_count = 0
                norm_pos = 0
                while norm_pos < start_pos:
                    if char_count >= len(original_text):
                        break
                    char = original_text[char_count]
                    norm_char = unicodedata.normalize('NFKC', char).casefold()
                    norm_len = len(norm_char)
                    if norm_pos + norm_len > start_pos:
                        # This is a partial match; we need to find full character boundaries
                        break
                    norm_pos += norm_len
                    char_count += 1
                
                orig_start = char_count
                
                # Now determine the end position by expanding until normalized substring matches query
                end_char_count = orig_start
                current_norm_pos = 0
                while current_norm_pos < len(normalized_query):
                    if end_char_count >= len(original_text):
                        break
                    char = original_text[end_char_count]
                    norm_char = unicodedata.normalize('NFKC', char).casefold()
                    norm_len = len(norm_char)
                    # Check if adding this character would exceed the query length
                    if current_norm_pos + norm_len > len(normalized_query):
                        break
                    current_norm_pos += norm_len
                    end_char_count += 1
                
                # Verify that we have a complete match by checking normalized substring
                test_span = original_text[orig_start:end_char_count]
                test_normalized = normalize_text(test_span)
                
                if test_normalized == normalized_query:
                    # Check for duplicate spans
                    span_key = (source_id, orig_start, end_char_count)
                    if span_key not in seen_spans:
                        seen_spans.add(span_key)
                        matches.append({
                            "source_id": source_id,
                            "start": orig_start,
                            "end": end_char_count,
                            "quote": test_span
                        })
        
        # Sort matches by source input order then ascending start index
        matches.sort(key=lambda x: (source_ids.index(x["source_id"]), x["start"]))
        
        results.append({
            "query_id": query_id,
            "matches": matches
        })
        
        if not matches:
            unsupported_query_ids.append(query_id)
    
    # Construct output
    output = {
        "queries": results,
        "unsupported_query_ids": unsupported_query_ids
    }
    
    return output
