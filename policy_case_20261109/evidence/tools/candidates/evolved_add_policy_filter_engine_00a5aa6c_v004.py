def run(payload: dict) -> dict:
    """
    Process evidence and entries to identify entities with their provenance.
    
    Validates that all entries reference existing evidence IDs and contain
    exact contiguous quotes in the evidence text. Groups eligible entries by
    group_id, ensuring consistent names within groups. Filters out ineligible
    entries and aggregates evidence IDs preserving order and deduplication.
    
    Args:
        payload: Dictionary with 'evidence' (list of {evidence_id, text}) and 'entries'
                 (list of {name, group_id, evidence_id, quote, eligible})
                 
    Returns:
        Dictionary with 'entities' (list of {name, evidence_ids}) and
        'unique_entity_count' (int)
        
    Raises:
        ValueError: If inputs are invalid or inconsistent
    """
    # Validate input structure
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")
    
    evidence_list = payload.get('evidence')
    entries_list = payload.get('entries')
    
    if not isinstance(evidence_list, list):
        raise ValueError("Evidence must be a list")
    if not isinstance(entries_list, list):
        raise ValueError("Entries must be a list")
    
    # Build evidence lookup with uniqueness check
    evidence_dict = {}
    seen_evidence_ids = set()
    
    for ev in evidence_list:
        if not isinstance(ev, dict):
            raise ValueError("Evidence items must be dictionaries")
        ev_id = ev.get('evidence_id')
        ev_text = ev.get('text')
        if not isinstance(ev_id, str) or not ev_id.strip():
            raise ValueError("Evidence ID must be a non-empty string")
        if ev_id in seen_evidence_ids:
            raise ValueError(f"Duplicate evidence ID found: {ev_id}")
        seen_evidence_ids.add(ev_id)
        if not isinstance(ev_text, str):
            raise ValueError("Evidence text must be a string")
        evidence_dict[ev_id] = ev_text
    
    # Validate entries and collect valid ones
    valid_entries = []
    entry_lookup = {}  # group_id -> list of (entry, name)
    
    for entry in entries_list:
        if not isinstance(entry, dict):
            raise ValueError("Entry items must be dictionaries")
        
        name = entry.get('name')
        group_id = entry.get('group_id')
        evidence_id = entry.get('evidence_id')
        quote = entry.get('quote')
        eligible = entry.get('eligible')
        
        # Validate required fields
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Entry name must be a non-empty string")
        if not isinstance(group_id, str) or not group_id.strip():
            raise ValueError("Entry group_id must be a non-empty string")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("Entry evidence_id must be a non-empty string")
        if not isinstance(quote, str) or not quote.strip():
            raise ValueError("Entry quote must be a non-empty string")
        if not isinstance(eligible, bool):
            raise ValueError("Entry eligible must be a boolean")
        
        # Check evidence exists
        if evidence_id not in evidence_dict:
            raise ValueError(f"Unknown evidence ID: {evidence_id}")
        
        # Check quote exists in evidence text
        evidence_text = evidence_dict[evidence_id]
        if quote not in evidence_text:
            raise ValueError(f"Quote not found in evidence text: {quote}")
        
        # Store valid entry
        valid_entries.append(entry)
        
        # Track by group for name consistency check
        if group_id not in entry_lookup:
            entry_lookup[group_id] = []
        entry_lookup[group_id].append((entry, name))
    
    # Validate consistent names within groups
    for group_id, entries_and_names in entry_lookup.items():
        names = [name for _, name in entries_and_names]
        if len(set(names)) > 1:
            raise ValueError(f"Inconsistent names in group {group_id}: {set(names)}")
    
    # Filter eligible entries
    eligible_entries = [e for e in valid_entries if e['eligible']]
    
    # Group by group_id and preserve first encounter order
    grouped_entries = {}
    for entry in eligible_entries:
        group_id = entry['group_id']
        if group_id not in grouped_entries:
            grouped_entries[group_id] = []
        grouped_entries[group_id].append(entry)
    
    # Build result entities
    entities = []
    seen_groups = set()
    
    for group_id, entries in grouped_entries.items():
        if group_id in seen_groups:
            continue
        seen_groups.add(group_id)
        
        # Get canonical name from first entry
        name = entries[0]['name']
        
        # Collect unique evidence IDs preserving order
        evidence_ids = []
        seen_evidence = set()
        
        for entry in entries:
            ev_id = entry['evidence_id']
            if ev_id not in seen_evidence:
                evidence_ids.append(ev_id)
                seen_evidence.add(ev_id)
        
        entities.append({
            'name': name,
            'evidence_ids': evidence_ids
        })
    
    return {
        'entities': entities,
        'unique_entity_count': len(entities)
    }
