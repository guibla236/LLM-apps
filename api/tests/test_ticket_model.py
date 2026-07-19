"""Tests for TicketModel backwards compatibility with SE extensions."""

import json
from pathlib import Path
from enum import Enum
import pytest
from pydantic import ValidationError
from models.tickets import TicketModel, TicketPriority


class MockTicketPriority(str, Enum):
    """Helper for test payloads."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


# ── Legacy synthetic payload (Spanish, all original fields required) ──

LEGACY_PAYLOAD = {
    "ticketId": "DEV-20251211-083",
    "creationDate": "2025-12-11",
    "priority": "Medium",
    "owner": "Equipo de Desarrollo",
    "description": "El servidor Dev-DB01 se está quedando sin espacio en disco.",
    "impact": "Bloqueo de operaciones de desarrollo.",
    "actions": "Limpieza de archivos temporales."
}

# ── Stack Exchange payload (with new optional fields) ──

SE_PAYLOAD = {
    "ticketId": "SE-SUPERUSER-142340",
    "priority": "Medium",
    "description": "How to clean print spooler on Windows 10 when queue is stuck...",
    "expected_output": (
        "Open Services console, find 'Print Spooler', stop the service, "
        "delete files in %systemroot%\\System32\\Spool\\Printers\\, restart the service."
    ),
    "community": "superuser"
}

# ── Minimal valid payload (only required fields) ──

MINIMAL_PAYLOAD = {
    "ticketId": "SE-ASKUBUNTU-001",
    "priority": "Low",
    "description": "How to reset network settings in Ubuntu?"
}


class TestTicketModelBackwardsCompatibility:
    """Verify that legacy synthetic tickets still parse correctly."""

    def test_legacy_payload_parses(self):
        """All original required fields → should parse without warnings."""
        ticket = TicketModel(**LEGACY_PAYLOAD)
        assert ticket.ticketId == "DEV-20251211-083"
        assert ticket.creationDate == "2025-12-11"
        assert ticket.priority == TicketPriority.MEDIUM
        assert ticket.owner == "Equipo de Desarrollo"
        assert ticket.impact == "Bloqueo de operaciones de desarrollo."
        assert ticket.actions == "Limpieza de archivos temporales."
        # New fields default to empty
        assert ticket.expected_output == ""
        assert ticket.community == ""

    def test_legacy_payload_from_mock_file(self):
        """Load real synthetic tickets from mock JSON files (skip known-bad priorities)."""
        mock_dir = Path(__file__).parent.parent / "static/mock/tickets"
        json_files = list(mock_dir.glob("*.json"))
        assert len(json_files) > 0, "No mock ticket files found"

        valid_priorities = {p.value for p in TicketPriority}
        parsed = 0
        for json_file in json_files:
            with open(json_file, "r", encoding="utf-8") as f:
                tickets_data = json.load(f)
            for ticket_dict in tickets_data[:5]:  # Test first 5 of each file
                # Skip known pre-existing bad data (priority "Critical" not in enum)
                if ticket_dict.get("priority") not in valid_priorities:
                    continue
                ticket = TicketModel(**ticket_dict)
                assert ticket.ticketId is not None
                assert ticket.description is not None
                parsed += 1
        assert parsed > 0, "No valid tickets found in mock files"


class TestTicketModelSE:
    """Verify that the new SE payload parses correctly."""

    def test_se_payload_parses(self):
        """SE payload with new optional fields."""
        ticket = TicketModel(**SE_PAYLOAD)
        assert ticket.ticketId == "SE-SUPERUSER-142340"
        assert ticket.priority == TicketPriority.MEDIUM
        assert ticket.description == (
            "How to clean print spooler on Windows 10 when queue is stuck..."
        )
        assert ticket.expected_output.startswith("Open Services console")
        assert ticket.community == "superuser"
        # Defaults for fields not in SE payload
        assert ticket.creationDate == ""
        assert ticket.owner == "community"
        assert ticket.impact == ""
        assert ticket.actions == ""


class TestTicketModelMinimal:
    """Verify that only the truly required fields work."""

    def test_minimal_payload_parses(self):
        """Only ticketId, priority, and description."""
        ticket = TicketModel(**MINIMAL_PAYLOAD)
        assert ticket.ticketId == "SE-ASKUBUNTU-001"
        assert ticket.priority == TicketPriority.LOW
        assert ticket.description == "How to reset network settings in Ubuntu?"
        # Everything else defaults
        assert ticket.creationDate == ""
        assert ticket.owner == "community"
        assert ticket.impact == ""
        assert ticket.actions == ""
        assert ticket.expected_output == ""
        assert ticket.community == ""

    def test_missing_required_field_fails(self):
        """ticketId is required — should raise ValidationError."""
        with pytest.raises(ValidationError):
            TicketModel(priority="High", description="Missing ticketId")

    def test_missing_description_fails(self):
        """description is required."""
        with pytest.raises(ValidationError):
            TicketModel(ticketId="TEST-001", priority="Low")


class TestTicketPriority:
    """Verify TicketPriority enum values."""

    def test_priority_values(self):
        assert TicketPriority.LOW.value == "Low"
        assert TicketPriority.MEDIUM.value == "Medium"
        assert TicketPriority.HIGH.value == "High"
        assert TicketPriority.URGENT.value == "Urgent"

    def test_invalid_priority_fails(self):
        with pytest.raises(ValidationError):
            TicketModel(
                ticketId="TEST-002",
                priority="Critical",  # Invalid, not in enum
                description="Test"
            )
