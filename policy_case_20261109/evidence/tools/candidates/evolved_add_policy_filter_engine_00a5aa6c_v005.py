def run(payload: dict) -> dict:
    """
    Process evidence and entries to identify entities with their provenance.
    
    Validates that all entries reference existing evidence IDs and contain
    exact contiguous quotes in the evidence text. Groups eligible entries by
    group_id, ensuring consistent names within groups. Filters out ineligible
    entries and aggregates evidence IDs preserving order and deduplication.
    
    In policy mode, evaluates signed-relation policy conditions over scoped facts.
    Policy objects require scope, all_of, any_of, none_of lists with valid relation/polarity pairs.
    Entries must have non-blank relation/scope and polarity (positive/negative/unknown).
    
    Args:
        payload: Dictionary with 'evidence' (list of {evidence_id, text}) and 'entries'
                 (list of {name, group_id, evidence_id, quote, eligible, relation, polarity, scope})
                 Optional 'policy' object for scoped signed-relation filtering.
                 
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
    
    # Check for policy mode
    has_policy = 'policy' in payload
    if has_policy:
        policy = payload['policy']
        if not isinstance(policy, dict):
            raise ValueError("Policy must be a dictionary")
        
        scope = policy.get('scope')
        all_of = policy.get('all_of')
        any_of = policy.get('any_of')
        none_of = policy.get('none_of')
        
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError("Policy scope must be a non-empty string")
        if not isinstance(all_of, list):
            raise ValueError("Policy all_of must be a list")
        if not isinstance(any_of, list):
            raise ValueError("Policy any_of must be a list")
        if not isinstance(none_of, list):
            raise ValueError("Policy none_of must be a list")
        
        # Validate policy items
        for lst_name, lst in [('all_of', all_of), ('any_of', any_of), ('none_of', none_of)]:
            for i, item in enumerate(lst):
                if not isinstance(item, dict):
                    raise ValueError(f"Policy {lst_name} item {i} must be a dictionary")
                relation = item.get('relation')
                polarity = item.get('polarity')
                if not isinstance(relation, str) or not relation.strip():
                    raise ValueError(f"Policy {lst_name} item {i} relation must be a non-empty string")
                if not isinstance(polarity, str) or polarity not in ('positive', 'negative'):
                    raise ValueError(f"Policy {lst_name} item {i} polarity must be 'positive' or 'negative'")
    
    # Validate entries and collect valid ones
    valid_entries = []
    entry_lookup = {}  # group_id -> list of (entry, name) for legacy mode
    policy_entry_lookup = {}  # (scope, group_id) -> list of (entry, name) for policy mode
    
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
        
        # Validate policy fields if policy present
        if has_policy:
            scope = entry.get('scope')
            relation = entry.get('relation')
            polarity = entry.get('polarity')
            
            if not isinstance(scope, str) or not scope.strip():
                raise ValueError("Entry scope must be a non-empty string")
            if not isinstance(relation, str) or not relation.strip():
                raise ValueError("Entry relation must be a non-empty string")
            if not isinstance(polarity, str) or polarity not in ('positive', 'negative', 'unknown'):
                raise ValueError("Entry polarity must be 'positive', 'negative', or 'unknown'")
        
        # Store valid entry
        valid_entries.append(entry)
        
        # Track by group for name consistency check
        if not has_policy:
            if group_id not in entry_lookup:
                entry_lookup[group_id] = []
            entry_lookup[group_id].append((entry, name))
        else:
            scope = entry.get('scope')
            key = (scope, group_id)
            if key not in policy_entry_lookup:
                policy_entry_lookup[key] = []
            policy_entry_lookup[key].append((entry, name))
    
    # Legacy mode: Validate consistent names within groups
    if not has_policy:
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
    
    # Policy mode execution
    # Filter entries by scope and eligibility
    filtered_entries = []
    for entry in valid_entries:
        if entry['eligible'] and entry.get('scope') == policy['scope']:
            filtered_entries.append(entry)
    
    # Group by (scope, group_id) and validate name consistency
    grouped_entries = {}
    for entry in filtered_entries:
        scope = entry['scope']
        group_id = entry['group_id']
        key = (scope, group_id)
        if key not in grouped_entries:
            grouped_entries[key] = []
        grouped_entries[key].append(entry)
    
    # Validate name consistency within groups
    for key, entries_and_names in policy_entry_lookup.items():
        names = [name for _, name in entries_and_names]
        if len(set(names)) > 1:
            raise ValueError(f"Inconsistent names in group {key}: {set(names)}")
    
    # Process each group according to policy logic
    passing_groups = []
    
    for (scope, group_id), entries in grouped_entries.items():
        # Get canonical name from first entry
        name = entries[0]['name']
        
        # Collect established facts (positive or negative polarity)
        established_facts = set()
        for entry in entries:
            if entry['polarity'] in ('positive', 'negative'):
                established_facts.add((entry['relation'], entry['polarity']))
        
        # Check policy conditions
        all_of_list = {(item['relation'], item['polarity']) for item in policy['all_of']}
        any_of_list = {(item['relation'], item['polarity']) for item in policy['any_of']}
        none_of_list = {(item['relation'], item['polarity']) for item in policy['none_of']}
        
        # A group must have at least one established fact to be considered
        if not established_facts and (all_of_list or any_of_list):
            continue  # Group fails because it has no facts to satisfy requirements
        
        # Check all_of: All required facts must be present
        if not all_of_list.issubset(established_facts):
            continue  # Group fails all_of requirement
        
        # Check any_of: At least one required fact must be present (or empty list)
        if any_of_list and not any_of_list.intersection(established_facts):
            continue  # Group fails any_of requirement
        
        # Check none_of: No prohibited facts must be present
        if none_of_list.intersection(established_facts):
            continue  # Group fails none_of requirement
        
        # Group passes all policy checks
        passing_groups.append((name, entries))
    
    # Build result entities with evidence IDs from matching records
    entities = []
    seen_groups = set()
    
    for name, entries in passing_groups:
        # Get group key to ensure we're using the right one
        group_key = (policy['scope'], entries[0]['group_id'])
        
        # Collect established facts that match policy criteria
        matching_facts = set()
        if policy['all_of'] or policy['any_of']:
            all_of_set = {(item['relation'], item['polarity']) for item in policy['all_of']}
            any_of_set = {(item['relation'], item['polarity']) for item in policy['any_of']}
            
            # If both lists are empty, we use all established facts
            if not all_of_set and not any_of_set:
                matching_facts = {(entry['relation'], entry['polarity']) for entry in entries 
                                  if entry['polarity'] in ('positive', 'negative')}
            else:
                # Use all_of OR any_of criteria
                if all_of_set:
                    matching_facts.update(all_of_set)
                if any_of_set:
                    matching_facts.update(any_of_set)
        else:
            # Both lists empty, use all established facts
            matching_facts = {(entry['relation'], entry['polarity']) for entry in entries 
                              if entry['polarity'] in ('positive', 'negative')}
        
        # Collect evidence IDs from records that match criteria
        evidence_ids = []
        seen_evidence = set()
        
        for entry in entries:
            fact_key = (entry['relation'], entry['polarity'])
            if fact_key in matching_facts or not matching_facts:  # If no criteria, include all
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
