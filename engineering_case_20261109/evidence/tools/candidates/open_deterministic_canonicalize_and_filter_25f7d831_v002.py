import json
from typing import Dict, List, Any

def run(payload: dict) -> dict:
    """
    Canonicalizes and filters entity records based on provided maps and keywords.
    
    This function processes a list of entity records, mapping aliases to canonical names,
    filtering based on action and exclusion keywords, and merging evidence IDs and qualifiers
    for entities with the same canonical name. It ensures deterministic output according to
    the specification's invariants and edge cases.
    
    Limitations:
        - Relies entirely on provided canonicalization map and keyword lists.
        - Cannot infer relationships not explicitly stated in input records.
        - Output order is preserved from input records, but grouped by canonical name.
    """
    # Validate input structure
    required_fields = ["records", "canonicalization_map", "action_keywords", "exclusion_keywords"]
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Missing required field: {field}")
    
    records = payload["records"]
    canonicalization_map = payload["canonicalization_map"]
    action_keywords = payload["action_keywords"]
    exclusion_keywords = payload["exclusion_keywords"]
    
    # Validate types
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    if not isinstance(canonicalization_map, dict):
        raise ValueError("canonicalization_map must be a dictionary")
    if not isinstance(action_keywords, list):
        raise ValueError("action_keywords must be a list")
    if not isinstance(exclusion_keywords, list):
        raise ValueError("exclusion_keywords must be a list")
    
    # Initialize result structure
    canonical_entities_dict: Dict[str, Any] = {}
    
    for record in records:
        # Validate record structure
        required_record_fields = ["name", "relation", "evidence_id"]
        for field in required_record_fields:
            if field not in record:
                raise ValueError(f"Record missing required field: {field}")
        
        name = record["name"]
        aliases = record.get("aliases", [])
        relation = record["relation"]
        evidence_id = record["evidence_id"]
        qualifiers = record.get("qualifiers", [])
        
        # Determine canonical name
        canonical_name = None
        if name in canonicalization_map:
            canonical_name = canonicalization_map[name]
        else:
            # Check aliases for canonical mapping
            for alias in aliases:
                if alias in canonicalization_map:
                    canonical_name = canonicalization_map[alias]
                    break
            
            # If no mapping found, use lowercased and stripped name as key
            if canonical_name is None:
                canonical_name = name.lower().strip()
        
        # Check for action keywords in relation
        has_action_keyword = any(keyword.lower() in relation.lower() for keyword in action_keywords)
        
        # Check for exclusion keywords in relation
        has_exclusion_keyword = any(keyword.lower() in relation.lower() for keyword in exclusion_keywords)
        
        # Apply filtering logic: skip if no action keywords found
        if not has_action_keyword:
            continue
        
        # If we reach here, the record should be included (has action keywords)
        if canonical_name not in canonical_entities_dict:
            canonical_entities_dict[canonical_name] = {
                "canonical_name": canonical_name,
                "aliases": set(),
                "merged_evidence_ids": [],
                "primary_relation": None,
                "merged_qualifiers": []
            }
        
        entity = canonical_entities_dict[canonical_name]
        
        # Merge aliases (deduplicated) - only from the aliases field
        for alias in aliases:
            entity["aliases"].add(alias)
        
        # Append evidence ID
        entity["merged_evidence_ids"].append(evidence_id)
        
        # Append qualifiers
        entity["merged_qualifiers"].extend(qualifiers)
        
        # Store first valid relation as primary_relation
        if entity["primary_relation"] is None:
            entity["primary_relation"] = relation
    
    # Convert set of aliases to list for output
    result_list = []
    for entity in canonical_entities_dict.values():
        entity["aliases"] = list(entity["aliases"])
        result_list.append(entity)
    
    return {"canonical_entities": result_list}
