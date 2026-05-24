"""Tests for src.ingestion.generators — synthetic data generation."""

import json

import pytest

from src.ingestion.generators import (
    generate_adt_events,
    generate_claims,
    generate_members,
    generate_payers,
    generate_providers,
)


class TestGenerateMembers:
    """Tests for member data generation."""

    @pytest.fixture
    def members(self):
        return generate_members(10)

    def test_generates_correct_count(self, members):
        assert len(members) == 10

    def test_member_has_required_fields(self, members):
        required = {
            "member_id",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "ssn",
            "address",
            "city",
            "state",
            "zip_code",
            "phone",
            "email",
            "plan_type",
            "effective_date",
        }
        for member in members:
            assert required.issubset(
                set(member.keys())
            ), f"Missing fields: {required - set(member.keys())}"

    def test_member_id_format(self, members):
        for member in members:
            assert member["member_id"].startswith("MBR")
            assert len(member["member_id"]) == 9

    def test_gender_values(self, members):
        for member in members:
            assert member["gender"] in ("M", "F")

    def test_state_is_two_letters(self, members):
        for member in members:
            assert len(member["state"]) == 2

    def test_unique_member_ids(self, members):
        ids = [m["member_id"] for m in members]
        assert len(ids) == len(set(ids))

    def test_ssn_format(self, members):
        for member in members:
            ssn = member["ssn"]
            assert len(ssn) == 11  # XXX-XX-XXXX
            assert ssn[3] == "-" and ssn[6] == "-"


class TestGenerateProviders:
    """Tests for provider data generation."""

    @pytest.fixture
    def providers(self):
        return generate_providers(5)

    def test_generates_correct_count(self, providers):
        assert len(providers) == 5

    def test_provider_has_required_fields(self, providers):
        required = {"provider_id", "npi", "first_name", "last_name", "specialty"}
        for provider in providers:
            assert required.issubset(set(provider.keys()))

    def test_npi_is_10_digits(self, providers):
        for provider in providers:
            npi = provider["npi"]
            assert len(npi) == 10
            assert npi.isdigit()
            assert npi.startswith("1")


class TestGeneratePayers:
    """Tests for payer data generation."""

    @pytest.fixture
    def payers(self):
        return generate_payers(3)

    def test_generates_correct_count(self, payers):
        assert len(payers) == 3

    def test_payer_has_required_fields(self, payers):
        required = {"payer_id", "payer_name", "payer_type"}
        for payer in payers:
            assert required.issubset(set(payer.keys()))

    def test_payer_id_format(self, payers):
        for payer in payers:
            assert payer["payer_id"].startswith("PAY")


class TestGenerateClaims:
    """Tests for claims data generation."""

    @pytest.fixture
    def members(self):
        return generate_members(5)

    @pytest.fixture
    def providers(self):
        return generate_providers(3)

    @pytest.fixture
    def payers(self):
        return generate_payers(2)

    @pytest.fixture
    def claims_result(self, members, providers, payers):
        return generate_claims(
            20,
            [m["member_id"] for m in members],
            [p["provider_id"] for p in providers],
            [p["payer_id"] for p in payers],
        )

    def test_returns_headers_and_lines(self, claims_result):
        headers, lines = claims_result
        assert len(headers) == 20
        assert len(lines) > 0  # Each claim has at least 1 line

    def test_claim_header_fields(self, claims_result):
        headers, _ = claims_result
        required = {"claim_id", "member_id", "provider_id", "payer_id", "status"}
        for header in headers:
            assert required.issubset(set(header.keys()))

    def test_claim_line_references_header(self, claims_result):
        headers, lines = claims_result
        header_ids = {h["claim_id"] for h in headers}
        for line in lines:
            assert line["claim_id"] in header_ids

    def test_claim_status_is_valid(self, claims_result):
        headers, _ = claims_result
        valid = {"approved", "denied", "pending", "partially_approved", "under_review"}
        for header in headers:
            assert header["status"] in valid

    def test_line_amounts_are_positive(self, claims_result):
        _, lines = claims_result
        for line in lines:
            assert line["line_charge_amount"] > 0


class TestGenerateADTEvents:
    """Tests for ADT event generation."""

    @pytest.fixture
    def members(self):
        return generate_members(5)

    @pytest.fixture
    def providers(self):
        return generate_providers(3)

    @pytest.fixture
    def events(self, members, providers):
        return generate_adt_events(
            15,
            [m["member_id"] for m in members],
            [p["provider_id"] for p in providers],
        )

    def test_generates_correct_count(self, events):
        assert len(events) == 15

    def test_event_has_required_fields(self, events):
        required = {"event_id", "event_type", "member_id", "event_timestamp"}
        for event in events:
            assert required.issubset(set(event.keys()))

    def test_event_type_is_valid(self, events):
        valid_types = {"A01", "A02", "A03", "A04", "A08"}
        for event in events:
            assert event["event_type"] in valid_types

    def test_events_are_json_serializable(self, events):
        for event in events:
            # Should not raise
            json.dumps(event, default=str)
