"""Synthetic healthcare data generators using Faker.

Generates realistic (but fake) data for:
- Members (patients with eligibility info)
- Providers (physicians with NPI and specialty)
- Payers (insurance companies with plan types)
- Claims (headers + line items with ICD-10/CPT codes)
- ADT events (HL7-style admit/discharge/transfer messages)

All data is synthetic. No real PHI is used or generated.
"""

import hashlib
import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

from src.ingestion.reference_data import (
    ADT_EVENT_TYPES,
    ADT_EVENT_WEIGHTS,
    CLAIM_STATUS_WEIGHTS,
    CLAIM_STATUSES,
    CPT_CODES,
    DENIAL_REASONS,
    ICD10_CODES,
    PLAN_TYPES,
    SPECIALTIES,
    US_STATES,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)
fake = Faker()
Faker.seed(42)
random.seed(42)


def _generate_npi() -> str:
    """Generate a realistic 10-digit NPI number."""
    return f"1{random.randint(100000000, 999999999)}"


def _generate_member_id() -> str:
    """Generate a member ID in a realistic format."""
    return f"MBR{random.randint(100000, 999999)}"


def _hash_pii(value: str) -> str:
    """SHA-256 hash for demonstrating PHI masking patterns."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Member Generator
# ---------------------------------------------------------------------------

def generate_members(count: int) -> list[dict[str, Any]]:
    """Generate synthetic member (patient) records.

    Fields mirror a typical eligibility file:
    member_id, ssn, first_name, last_name, date_of_birth, gender,
    address, city, state, zip_code, phone, email, plan_type,
    payer_id, effective_date, termination_date
    """
    logger.info(f"Generating {count:,} members...")
    members = []

    for _ in range(count):
        gender = random.choice(["M", "F"])
        first_name = fake.first_name_male() if gender == "M" else fake.first_name_female()
        last_name = fake.last_name()
        dob = fake.date_of_birth(minimum_age=18, maximum_age=85)
        effective = fake.date_between(start_date="-3y", end_date="-6m")

        # ~15% of members have terminated coverage
        term_date = None
        if random.random() < 0.15:
            term_date = fake.date_between(start_date=effective, end_date="today")

        members.append({
            "member_id": _generate_member_id(),
            "ssn": fake.ssn(),
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": dob.isoformat(),
            "gender": gender,
            "address": fake.street_address(),
            "city": fake.city(),
            "state": random.choice(US_STATES),
            "zip_code": fake.zipcode(),
            "phone": fake.phone_number(),
            "email": fake.email(),
            "plan_type": random.choice(PLAN_TYPES),
            "payer_id": None,  # linked after payer generation
            "effective_date": effective.isoformat(),
            "termination_date": term_date.isoformat() if term_date else None,
            "created_at": datetime.utcnow().isoformat(),
        })

    logger.info(f"Generated {len(members):,} members")
    return members


# ---------------------------------------------------------------------------
# Provider Generator
# ---------------------------------------------------------------------------

def generate_providers(count: int) -> list[dict[str, Any]]:
    """Generate synthetic provider records.

    Fields: provider_id, npi, first_name, last_name, specialty,
    facility_name, address, city, state, zip_code, tax_id
    """
    logger.info(f"Generating {count:,} providers...")
    providers = []

    for _ in range(count):
        providers.append({
            "provider_id": str(uuid.uuid4()),
            "npi": _generate_npi(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "specialty": random.choice(SPECIALTIES),
            "facility_name": f"{fake.last_name()} {random.choice(['Medical Center', 'Health System', 'Clinic', 'Hospital', 'Health Group'])}",
            "address": fake.street_address(),
            "city": fake.city(),
            "state": random.choice(US_STATES),
            "zip_code": fake.zipcode(),
            "tax_id": fake.bothify("##-#######"),
            "is_active": random.random() > 0.05,  # 95% active
            "created_at": datetime.utcnow().isoformat(),
        })

    logger.info(f"Generated {len(providers):,} providers")
    return providers


# ---------------------------------------------------------------------------
# Payer Generator
# ---------------------------------------------------------------------------

def generate_payers(count: int) -> list[dict[str, Any]]:
    """Generate synthetic payer (insurance company) records."""
    logger.info(f"Generating {count:,} payers...")
    payer_names = [
        "Blue Cross Blue Shield", "Aetna", "UnitedHealthcare", "Cigna",
        "Humana", "Kaiser Permanente", "Anthem", "Centene", "Molina Healthcare",
        "WellCare", "Magellan Health", "Highmark", "Health Net",
        "AmeriHealth", "CareSource", "Priority Health", "Medica",
        "SelectHealth", "Geisinger Health Plan", "EmblemHealth",
        "UPMC Health Plan", "Oscar Health", "Devoted Health",
        "Clover Health", "Alignment Healthcare", "Bright Health",
        "Quartz Health Solutions", "Tufts Health Plan",
        "Harvard Pilgrim", "Fallon Health",
    ]

    payers = []
    for i in range(min(count, len(payer_names))):
        payers.append({
            "payer_id": f"PAY{i + 1:04d}",
            "payer_name": payer_names[i],
            "payer_type": random.choice(["Commercial", "Medicare", "Medicaid", "Medicare Advantage"]),
            "plan_types_offered": random.sample(PLAN_TYPES, k=random.randint(2, 4)),
            "state": random.choice(US_STATES),
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        })

    logger.info(f"Generated {len(payers):,} payers")
    return payers


# ---------------------------------------------------------------------------
# Claims Generator
# ---------------------------------------------------------------------------

def generate_claims(
    count: int,
    member_ids: list[str],
    provider_ids: list[str],
    payer_ids: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate synthetic claims with header + line items.

    Returns:
        Tuple of (claim_headers, claim_lines)
    """
    logger.info(f"Generating {count:,} claims...")
    headers = []
    lines = []

    for _ in range(count):
        claim_id = str(uuid.uuid4())
        service_date = fake.date_between(start_date="-2y", end_date="today")
        status = random.choices(CLAIM_STATUSES, weights=CLAIM_STATUS_WEIGHTS, k=1)[0]
        num_lines = random.choices([1, 2, 3, 4], weights=[0.45, 0.30, 0.15, 0.10], k=1)[0]

        # Pick diagnosis
        primary_dx = random.choice(ICD10_CODES)

        # Denial reason only if denied
        denial_reason = None
        if status == "denied":
            denial_reason = random.choice(DENIAL_REASONS)

        total_amount = 0.0
        claim_lines = []
        for line_num in range(1, num_lines + 1):
            procedure = random.choice(CPT_CODES)
            line_amount = round(random.uniform(25.0, 2500.0), 2)
            allowed_amount = round(line_amount * random.uniform(0.6, 1.0), 2)
            paid_amount = round(allowed_amount * random.uniform(0.7, 1.0), 2) if status != "denied" else 0.0
            total_amount += line_amount

            claim_lines.append({
                "claim_line_id": str(uuid.uuid4()),
                "claim_id": claim_id,
                "line_number": line_num,
                "cpt_code": procedure["code"],
                "cpt_description": procedure["description"],
                "icd10_code": primary_dx["code"],
                "icd10_description": primary_dx["description"],
                "line_charge_amount": line_amount,
                "allowed_amount": allowed_amount,
                "paid_amount": round(paid_amount, 2),
                "units": random.randint(1, 4),
                "service_date": service_date.isoformat(),
            })

        headers.append({
            "claim_id": claim_id,
            "member_id": random.choice(member_ids),
            "provider_id": random.choice(provider_ids),
            "payer_id": random.choice(payer_ids),
            "claim_type": random.choice(["professional", "institutional"]),
            "service_date": service_date.isoformat(),
            "submission_date": (service_date + timedelta(days=random.randint(1, 14))).isoformat(),
            "status": status,
            "denial_reason": denial_reason,
            "primary_diagnosis": primary_dx["code"],
            "total_charge_amount": round(total_amount, 2),
            "total_paid_amount": round(sum(cl["paid_amount"] for cl in claim_lines), 2),
            "num_lines": num_lines,
            "created_at": datetime.utcnow().isoformat(),
        })
        lines.extend(claim_lines)

    logger.info(f"Generated {len(headers):,} claim headers and {len(lines):,} claim lines")
    return headers, lines


# ---------------------------------------------------------------------------
# ADT Event Generator
# ---------------------------------------------------------------------------

def generate_adt_events(
    count: int,
    member_ids: list[str],
    provider_ids: list[str],
) -> list[dict[str, Any]]:
    """Generate synthetic HL7-style ADT events.

    ADT = Admit/Discharge/Transfer — the core real-time events
    in hospital information systems.
    """
    logger.info(f"Generating {count:,} ADT events...")
    events = []

    for _ in range(count):
        event_type = random.choices(ADT_EVENT_TYPES, weights=ADT_EVENT_WEIGHTS, k=1)[0]
        event_time = fake.date_time_between(start_date="-1y", end_date="now")

        # Simulate HL7-style message structure
        events.append({
            "event_id": str(uuid.uuid4()),
            "event_type": event_type["code"],
            "event_description": event_type["description"],
            "member_id": random.choice(member_ids),
            "provider_id": random.choice(provider_ids),
            "facility_name": f"{fake.last_name()} Hospital",
            "department": random.choice([
                "Emergency", "ICU", "Medical/Surgical", "Cardiology",
                "Orthopedics", "Oncology", "Pediatrics", "OB/GYN",
            ]),
            "room_number": f"{random.randint(1, 8)}{random.randint(0, 9)}{random.randint(0, 9)}",
            "admit_reason": random.choice(ICD10_CODES)["description"],
            "event_timestamp": event_time.isoformat(),
            "message_control_id": f"MSG{random.randint(10000000, 99999999)}",
            "sending_facility": f"HIS-{random.randint(100, 999)}",
        })

    logger.info(f"Generated {len(events):,} ADT events")
    return events
