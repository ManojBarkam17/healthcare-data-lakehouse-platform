"""Healthcare reference data: ICD-10 codes, CPT codes, payer plans, etc.

These are realistic subsets used in synthetic data generation.
Production systems would pull from CMS or a terminology service.
"""

# Common ICD-10 diagnosis codes (subset for demo)
ICD10_CODES: list[dict[str, str]] = [
    {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications"},
    {"code": "I10", "description": "Essential hypertension"},
    {"code": "J06.9", "description": "Acute upper respiratory infection, unspecified"},
    {"code": "M54.5", "description": "Low back pain"},
    {"code": "J44.1", "description": "Chronic obstructive pulmonary disease with acute exacerbation"},
    {"code": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery"},
    {"code": "N39.0", "description": "Urinary tract infection, site not specified"},
    {"code": "K21.0", "description": "Gastro-esophageal reflux disease with esophagitis"},
    {"code": "F32.9", "description": "Major depressive disorder, single episode, unspecified"},
    {"code": "J18.9", "description": "Pneumonia, unspecified organism"},
    {"code": "E78.5", "description": "Hyperlipidemia, unspecified"},
    {"code": "G47.33", "description": "Obstructive sleep apnea"},
    {"code": "M79.3", "description": "Panniculitis, unspecified"},
    {"code": "R10.9", "description": "Unspecified abdominal pain"},
    {"code": "Z00.00", "description": "Encounter for general adult medical examination"},
    {"code": "K58.9", "description": "Irritable bowel syndrome without diarrhea"},
    {"code": "J45.909", "description": "Unspecified asthma, uncomplicated"},
    {"code": "E03.9", "description": "Hypothyroidism, unspecified"},
    {"code": "R05.9", "description": "Cough, unspecified"},
    {"code": "M25.511", "description": "Pain in right shoulder"},
]

# Common CPT procedure codes (subset for demo)
CPT_CODES: list[dict[str, str]] = [
    {"code": "99213", "description": "Office visit, established patient, low complexity"},
    {"code": "99214", "description": "Office visit, established patient, moderate complexity"},
    {"code": "99215", "description": "Office visit, established patient, high complexity"},
    {"code": "99203", "description": "Office visit, new patient, low complexity"},
    {"code": "99204", "description": "Office visit, new patient, moderate complexity"},
    {"code": "99281", "description": "Emergency department visit, self-limited problem"},
    {"code": "99283", "description": "Emergency department visit, moderate severity"},
    {"code": "99285", "description": "Emergency department visit, high severity"},
    {"code": "99232", "description": "Subsequent hospital care, moderate complexity"},
    {"code": "99233", "description": "Subsequent hospital care, high complexity"},
    {"code": "36415", "description": "Venipuncture, routine"},
    {"code": "80053", "description": "Comprehensive metabolic panel"},
    {"code": "85025", "description": "Complete blood count with differential"},
    {"code": "71046", "description": "Chest X-ray, 2 views"},
    {"code": "93000", "description": "Electrocardiogram, complete"},
    {"code": "90837", "description": "Psychotherapy, 60 minutes"},
    {"code": "97110", "description": "Therapeutic exercises"},
    {"code": "99395", "description": "Preventive visit, 18-39 years"},
    {"code": "99396", "description": "Preventive visit, 40-64 years"},
    {"code": "20610", "description": "Arthrocentesis, major joint"},
]

# Claim status values
CLAIM_STATUSES: list[str] = [
    "approved",
    "denied",
    "pending",
    "partially_approved",
    "under_review",
]

# Claim status weights (approved is most common)
CLAIM_STATUS_WEIGHTS: list[float] = [0.65, 0.12, 0.10, 0.08, 0.05]

# Denial reason codes
DENIAL_REASONS: list[str] = [
    "missing_prior_auth",
    "out_of_network",
    "not_medically_necessary",
    "duplicate_claim",
    "timely_filing",
    "coordination_of_benefits",
    "invalid_diagnosis_code",
    "member_not_eligible",
]

# Provider specialties
SPECIALTIES: list[str] = [
    "Internal Medicine",
    "Family Medicine",
    "Cardiology",
    "Orthopedics",
    "Dermatology",
    "Psychiatry",
    "Pediatrics",
    "Emergency Medicine",
    "General Surgery",
    "Obstetrics & Gynecology",
    "Neurology",
    "Pulmonology",
    "Gastroenterology",
    "Endocrinology",
    "Oncology",
]

# ADT event types (HL7-style)
ADT_EVENT_TYPES: list[dict[str, str]] = [
    {"code": "A01", "description": "Admit/Visit Notification"},
    {"code": "A02", "description": "Transfer a Patient"},
    {"code": "A03", "description": "Discharge/End Visit"},
    {"code": "A04", "description": "Register a Patient"},
    {"code": "A08", "description": "Update Patient Information"},
]

# ADT event type weights
ADT_EVENT_WEIGHTS: list[float] = [0.30, 0.10, 0.30, 0.20, 0.10]

# US states (subset for realistic addresses)
US_STATES: list[str] = [
    "TX", "CA", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI",
    "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI",
]

# Plan types
PLAN_TYPES: list[str] = ["HMO", "PPO", "EPO", "POS", "HDHP"]
