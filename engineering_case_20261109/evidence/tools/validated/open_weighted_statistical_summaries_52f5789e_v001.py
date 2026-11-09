import math

def run(payload: dict):
    """
    Compute weighted statistical summaries for positive numerical values with weights.
    
    Validates input according to specification and computes:
    - Weighted mean
    - Weighted population variance
    - Weighted population standard deviation
    - Weighted geometric mean
    
    All outputs are rounded to exactly 6 decimal places.
    
    Limitations: This function performs deterministic arithmetic operations only.
                 It does not perform clinical inference or model-based analysis.
    """
    # Validate input structure
    if 'rows' not in payload:
        raise ValueError("Missing required key 'rows'")
    
    rows = payload['rows']
    
    if not isinstance(rows, list):
        raise ValueError("'rows' must be an array")
        
    if len(rows) == 0:
        raise ValueError("Input 'rows' array cannot be empty")
    
    # Validate each row
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Row {i} must be an object")
            
        if 'value' not in row or 'weight' not in row:
            raise ValueError(f"Row {i} must contain 'value' and 'weight' keys")
            
        if len(row) != 2:
            raise ValueError(f"Row {i} must not contain extra keys")
            
        value = row['value']
        weight = row['weight']
        
        # Validate value
        if not isinstance(value, (int, float)):
            raise ValueError(f"Row {i} 'value' must be a number")
        if not math.isfinite(value):
            raise ValueError(f"Row {i} 'value' must be finite")
        if value <= 0:
            raise ValueError(f"Row {i} 'value' must be strictly positive")
            
        # Validate weight
        if not isinstance(weight, (int, float)):
            raise ValueError(f"Row {i} 'weight' must be a number")
        if not math.isfinite(weight):
            raise ValueError(f"Row {i} 'weight' must be finite")
        if weight < 0:
            raise ValueError(f"Row {i} 'weight' must be non-negative")
    
    # Compute total weight
    total_weight = sum(row['weight'] for row in rows)
    
    if total_weight == 0:
        raise ValueError("Sum of weights must be strictly positive")
        
    # Compute weighted mean
    weighted_sum = sum(row['weight'] * row['value'] for row in rows)
    weighted_mean = weighted_sum / total_weight
    
    # Compute weighted variance
    variance_numerator = sum(row['weight'] * (row['value'] - weighted_mean) ** 2 for row in rows)
    weighted_variance = variance_numerator / total_weight
    
    # Compute weighted standard deviation
    weighted_sd = math.sqrt(weighted_variance)
    
    # Compute weighted geometric mean
    log_sum = sum(row['weight'] * math.log(row['value']) for row in rows)
    weighted_geometric_mean = math.exp(log_sum / total_weight)
    
    # Round to 6 decimal places
    weighted_mean = round(weighted_mean, 6)
    weighted_variance = round(weighted_variance, 6)
    weighted_sd = round(weighted_sd, 6)
    weighted_geometric_mean = round(weighted_geometric_mean, 6)
    
    return {
        "weighted_mean": weighted_mean,
        "weighted_population_variance": weighted_variance,
        "weighted_population_sd": weighted_sd,
        "weighted_geometric_mean": weighted_geometric_mean
    }
