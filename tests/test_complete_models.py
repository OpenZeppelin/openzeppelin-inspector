import pytest
from pathlib import Path
from inspector.models._complete.detector_response import CompleteDetectorResponse
from inspector.models._complete.error import Error
from inspector.models._complete.extra import Extra
from inspector.models._complete.finding import CompleteFinding
from inspector.models._complete.instance import CompleteInstance
from inspector.models._complete.location import Location, LocationPoint
from inspector.models._complete.scanner_response import CompleteScannerResponse
from inspector.models._complete.severities import DetectorSeverities


def test_detector_response():
    # Test default initialization
    response = CompleteDetectorResponse()
    assert response.findings == []
    assert response.errors == []
    assert response.metadata == {}

    # Test with data
    response = CompleteDetectorResponse(
        findings=[CompleteFinding()], errors=[Error()], metadata={"key": "value"}
    )
    assert len(response.findings) == 1
    assert len(response.errors) == 1
    assert response.metadata == {"key": "value"}

    # Test JSON serialization
    json_data = response.__json__()
    assert "findings" in json_data
    assert "errors" in json_data
    assert "metadata" in json_data
    assert json_data["metadata"] == {"key": "value"}

    # Test from_dict
    response = CompleteDetectorResponse.from_dict(
        {
            "errors": ["test error"],
            "findings": [{"instances": []}],
            "metadata": {"key": "value"},
        }
    )
    assert len(response.errors) == 1
    assert response.errors[0].message == "test error"
    assert len(response.findings) == 1
    assert response.metadata == {"key": "value"}


def test_error():
    # Test default initialization
    error = Error()
    assert error.message == ""

    # Test with message
    error = Error(message="test")
    assert error.message == "test"

    # Test JSON serialization
    json_data = error.__json__()
    assert json_data["message"] == "test"


def test_extra():
    # Test default initialization
    extra = Extra()
    assert extra.metavars == {}
    assert extra.other == {}

    # Test with data
    extra = Extra(metavars={"key": "value"}, other={"meta": "data"})
    assert extra.metavars == {"key": "value"}
    assert extra.other == {"meta": "data"}

    # Test JSON serialization
    json_data = extra.__json__()
    assert json_data == {"metavars": {"key": "value"}, "other": {"meta": "data"}}

    # Test from_dict
    extra = Extra.from_dict(
        {"metavars": {"key": "value"}, "custom_field": "custom_value"}
    )
    assert extra.metavars == {"key": "value"}
    assert extra.other == {"custom_field": "custom_value"}


def test_finding():
    # Test default initialization
    finding = CompleteFinding()
    assert finding.instances == []
    assert finding.impacted == {}
    assert finding.lines == []
    assert finding.fixes == []

    # Test with data
    finding = CompleteFinding(
        instances=[CompleteInstance()],
        impacted={"file.py": 1},
        lines=["line1", "line2"],
        fixes=["fix1", "fix2"],
    )
    assert len(finding.instances) == 1
    assert finding.impacted == {"file.py": 1}
    assert finding.lines == ["line1", "line2"]
    assert finding.fixes == ["fix1", "fix2"]

    # Test JSON serialization
    json_data = finding.__json__()
    assert "instances" in json_data
    assert json_data["impacted"] == {"file.py": 1}

    # Test from_dict
    finding = CompleteFinding.from_dict(
        {"instances": [], "lines": ["line1", "line2"], "fixes": ["fix1", "fix2"]}
    )
    assert finding.instances == []
    assert finding.lines == ["line1", "line2"]
    assert finding.fixes == ["fix1", "fix2"]

    # Test add_instance and add_filename methods
    instance = CompleteInstance()
    finding.add_instance(instance)
    assert len(finding.instances) == 1
    assert finding.instances[0] == instance

    finding.add_filename("file.py")
    assert finding.impacted == {"file.py": 1}

    finding.add_filename("file.py")
    assert finding.impacted == {"file.py": 2}


def test_instance():
    # Test default initialization
    instance = CompleteInstance()
    assert instance.location is None
    assert instance.lines == []
    assert instance.fixes == []
    assert isinstance(instance.extra, Extra)

    # Test with data
    location = Location(
        path=Path("test.py"),
        start=LocationPoint(col=1, line=1, offset=0),
        end=LocationPoint(col=10, line=2, offset=20),
    )

    instance = CompleteInstance(
        location=location,
        lines=["line1", "line2"],
        fixes=["fix1", "fix2"],
        extra=Extra(metavars={"key": "value"}),
    )
    assert instance.location.path == Path("test.py")
    assert instance.location.start.line == 1
    assert instance.location.end.line == 2
    assert instance.lines == ["line1", "line2"]
    assert instance.fixes == ["fix1", "fix2"]
    assert instance.extra.metavars == {"key": "value"}

    # Test JSON serialization
    json_data = instance.__json__()
    assert "location" in json_data
    assert json_data["lines"] == ["line1", "line2"]
    assert json_data["fixes"] == ["fix1", "fix2"]
    assert "extra" in json_data

    # Test from_dict
    instance = CompleteInstance.from_dict(
        {
            "file_path": "test.py",
            "offset_start": 0,
            "offset_end": 20,
            "extras": {"metavars": {"key": "value"}},
        }
    )
    assert instance.location.path == Path("test.py")
    assert instance.location.start.offset == 0
    assert instance.location.end.offset == 20
    assert instance.extra.metavars == {"key": "value"}


def test_location():
    # Test default initialization
    location = Location()
    assert location.path == Path(".")
    assert location.start.line == 0
    assert location.end.line == 0

    # Test with data
    location = Location(
        path=Path("test.py"),
        start=LocationPoint(col=1, line=1, offset=0),
        end=LocationPoint(col=10, line=2, offset=20),
    )
    assert location.path == Path("test.py")
    assert location.start.line == 1
    assert location.end.line == 2
    assert location.start.col == 1
    assert location.end.col == 10

    # Test JSON serialization
    json_data = location.__json__()
    assert json_data["path"] == "test.py"
    assert json_data["position"]["start"]["line"] == 1
    assert json_data["position"]["end"]["line"] == 2

    # Test from_dict
    location = Location.from_dict(
        {
            "path": "test.py",
            "start": {"col": 1, "line": 1, "offset": 0},
            "end": {"col": 10, "line": 2, "offset": 20},
        }
    )
    assert location.path == Path("test.py")
    assert location.start.line == 1
    assert location.end.line == 2
    assert location.start.col == 1
    assert location.end.col == 10

    # Test set_start_location and set_end_location
    location = Location()
    location.set_start_location(col=1, line=1, offset=0)
    assert location.start.col == 1
    assert location.start.line == 1
    assert location.start.offset == 0

    location.set_end_location(col=10, line=2, offset=20)
    assert location.end.col == 10
    assert location.end.line == 2
    assert location.end.offset == 20


def test_location_point():
    # Test default initialization
    point = LocationPoint()
    assert point.line == -1
    assert point.col == -1
    assert point.offset == -1

    # Test with data
    point = LocationPoint(col=1, line=2, offset=10)
    assert point.line == 2
    assert point.col == 1
    assert point.offset == 10

    # Test from_dict
    point = LocationPoint.from_dict({})
    assert point.line == -1
    assert point.col == -1
    assert point.offset == -1

    point = LocationPoint.from_dict({"col": 1, "line": 2, "offset": 10})
    assert point.line == 2
    assert point.col == 1
    assert point.offset == 10


def test_scanner_response():
    # Test default initialization
    response = CompleteScannerResponse()
    assert response.errors == []
    assert response.scanned == []
    assert response.responses == {}

    # Test with data
    response = CompleteScannerResponse(
        errors=[Error()],
        scanned=["file1.py", "file2.py"],
        responses={"detector1": CompleteDetectorResponse()},
    )
    assert len(response.errors) == 1
    assert response.scanned == ["file1.py", "file2.py"]
    assert "detector1" in response.responses

    # Test JSON serialization
    json_data = response.__json__()
    assert "errors" in json_data
    assert json_data["scanned"] == ["file1.py", "file2.py"]
    assert "responses" in json_data
    assert "detector1" in json_data["responses"]

    # Test from_dict
    response = CompleteScannerResponse.from_dict(
        {
            "errors": ["test error"],
            "scanned": ["file1.py", "file2.py"],
            "responses": {"detector1": {}},
        }
    )
    assert len(response.errors) == 1
    assert response.errors[0].message == "test error"
    assert response.scanned == ["file1.py", "file2.py"]
    assert "detector1" in response.responses


def test_severity():
    # Test values
    assert DetectorSeverities.CRITICAL.value == "critical"
    assert DetectorSeverities.HIGH.value == "high"
    assert DetectorSeverities.MEDIUM.value == "medium"
    assert DetectorSeverities.LOW.value == "low"
    assert DetectorSeverities.INFO.value == "info"
    assert DetectorSeverities.NOTE.value == "note"

    # Test string representation
    assert str(DetectorSeverities.CRITICAL) == "critical"
    assert repr(DetectorSeverities.CRITICAL) == "DetectorSeverities.CRITICAL"

    # Test from_string
    assert DetectorSeverities.from_string("critical") == DetectorSeverities.CRITICAL
    assert DetectorSeverities.from_string("CRITICAL") == DetectorSeverities.CRITICAL
    assert DetectorSeverities.from_string("invalid") is None

    # Test to_dict
    severity_dict = DetectorSeverities.CRITICAL.to_dict()
    assert severity_dict == {"name": "CRITICAL", "value": "critical"}

    # Test comparison
    assert DetectorSeverities.INFO < DetectorSeverities.NOTE
    assert DetectorSeverities.NOTE < DetectorSeverities.LOW
    assert DetectorSeverities.LOW < DetectorSeverities.MEDIUM
    assert DetectorSeverities.MEDIUM < DetectorSeverities.HIGH
    assert DetectorSeverities.HIGH < DetectorSeverities.CRITICAL
    assert not (DetectorSeverities.INFO < DetectorSeverities.INFO)
    assert not (DetectorSeverities.CRITICAL < DetectorSeverities.HIGH)
