"""Tests for src.ingestion.reference_data — healthcare reference datasets."""

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


class TestICD10Codes:
    """Tests for ICD-10 diagnosis code reference data."""

    def test_has_codes(self):
        assert len(ICD10_CODES) >= 10

    def test_code_structure(self):
        for entry in ICD10_CODES:
            assert "code" in entry
            assert "description" in entry
            assert len(entry["code"]) >= 3

    def test_common_codes_present(self):
        codes = {c["code"] for c in ICD10_CODES}
        assert "E11.9" in codes   # Diabetes
        assert "I10" in codes     # Hypertension


class TestCPTCodes:
    """Tests for CPT procedure code reference data."""

    def test_has_codes(self):
        assert len(CPT_CODES) >= 10

    def test_code_structure(self):
        for entry in CPT_CODES:
            assert "code" in entry
            assert "description" in entry
            assert entry["code"].isdigit()
            assert len(entry["code"]) == 5


class TestClaimStatuses:
    """Tests for claim status reference data."""

    def test_all_statuses_present(self):
        expected = {"approved", "denied", "pending", "partially_approved", "under_review"}
        assert set(CLAIM_STATUSES) == expected

    def test_weights_sum_to_one(self):
        assert abs(sum(CLAIM_STATUS_WEIGHTS) - 1.0) < 0.01

    def test_weights_match_statuses(self):
        assert len(CLAIM_STATUS_WEIGHTS) == len(CLAIM_STATUSES)


class TestDenialReasons:
    """Tests for denial reason codes."""

    def test_has_reasons(self):
        assert len(DENIAL_REASONS) >= 5

    def test_reasons_are_strings(self):
        for reason in DENIAL_REASONS:
            assert isinstance(reason, str)
            assert len(reason) > 0


class TestProviderSpecialties:
    """Tests for provider specialty reference data."""

    def test_has_specialties(self):
        assert len(SPECIALTIES) >= 10

    def test_common_specialties_present(self):
        assert "Internal Medicine" in SPECIALTIES
        assert "Cardiology" in SPECIALTIES


class TestADTEventTypes:
    """Tests for ADT event type reference data."""

    def test_has_event_types(self):
        assert len(ADT_EVENT_TYPES) >= 3

    def test_weights_match(self):
        assert len(ADT_EVENT_WEIGHTS) == len(ADT_EVENT_TYPES)

    def test_adt_code_format(self):
        for event_type in ADT_EVENT_TYPES:
            assert "code" in event_type
            assert "description" in event_type
            assert event_type["code"].startswith("A")


class TestPlanTypes:
    """Tests for insurance plan types."""

    def test_has_plan_types(self):
        assert len(PLAN_TYPES) >= 5

    def test_common_plans_present(self):
        assert "HMO" in PLAN_TYPES
        assert "PPO" in PLAN_TYPES


class TestUSStates:
    """Tests for US states reference data."""

    def test_has_states(self):
        assert len(US_STATES) >= 10

    def test_two_letter_codes(self):
        for state in US_STATES:
            assert len(state) == 2
            assert state.isupper()
