from typing import Optional, List, Dict, Any

def mask_enrollment(enrollment_no: Optional[str], alias: Optional[str] = None) -> str:
    """
    Masks a 10-digit enrollment number according to FLASHNOVA privacy requirements.
    Example: 1234567890 -> 1234******
    If alias is provided: 1234****** (#1)
    """
    if not enrollment_no:
        return "UNKNOWN"
    
    clean_no = str(enrollment_no).strip()
    if len(clean_no) == 10 and clean_no.isdigit():
        masked = f"{clean_no[:4]}******"
    else:
        # Fallback for unexpected formats
        visible_len = min(4, len(clean_no))
        masked = clean_no[:visible_len] + "*" * (len(clean_no) - visible_len)
        
    if alias:
        return f"{masked} ({alias})"
    return masked

def generate_masked_aliases(student_enrollments: List[str]) -> Dict[str, str]:
    """
    Given a list of 10-digit enrollment numbers, assigns a unique masked identifier.
    If multiple students share the same first 4 digits, an alias suffix (#1, #2) is added.
    """
    prefix_counts = {}
    for enr in student_enrollments:
        if enr:
            prefix = enr[:4]
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
            
    prefix_seen = {}
    mapping = {}
    for enr in student_enrollments:
        if not enr:
            continue
        prefix = enr[:4]
        if prefix_counts.get(prefix, 0) > 1:
            idx = prefix_seen.get(prefix, 0) + 1
            prefix_seen[prefix] = idx
            mapping[enr] = mask_enrollment(enr, alias=f"#{idx}")
        else:
            mapping[enr] = mask_enrollment(enr)
    return mapping

def sanitize_teacher_record(record: Dict[str, Any], masked_identifier: str) -> Dict[str, Any]:
    """
    Strips all student names, emails, internal user IDs, and leaves only the masked identifier.
    """
    cleaned = dict(record)
    cleaned.pop("student_name", None)
    cleaned.pop("name", None)
    cleaned.pop("email", None)
    cleaned.pop("user_id", None)
    cleaned.pop("raw_enrollment_no", None)
    cleaned["masked_enrollment"] = masked_identifier
    return cleaned
