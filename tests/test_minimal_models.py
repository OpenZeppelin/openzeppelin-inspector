import pytest
from inspector.models.minimal import (
    MinimalDetectorResponse,
    Error,
    Extra,
    MinimalFinding,
    MinimalInstance,
    MinimalScannerResponse,
)


def test_detector_response():
    response = MinimalDetectorResponse()
    assert response.findings == []
    assert response.errors == []

    response = MinimalDetectorResponse(findings=[MinimalFinding()], errors=[Error()])
    assert len(response.findings) == 1
    assert len(response.errors) == 1

    # Test __json__ method
    json_data = response.__json__()
    assert "findings" in json_data
    assert "errors" in json_data

    # Test from_dict method
    response_from_dict = MinimalDetectorResponse.from_dict(
        {"findings": [], "errors": [{"message": "test error"}]}
    )
    assert len(response_from_dict.findings) == 0
    assert len(response_from_dict.errors) == 1


def test_error():
    error = Error()
    assert error.message == ""

    error = Error(message="test")
    assert error.message == "test"

    # Test __json__ method
    json_data = error.__json__()
    assert json_data == {"message": "test"}


def test_extra():
    extra = Extra()
    assert extra.metavars == {}
    assert extra.other == {}

    extra = Extra(metavars={"key": "value"}, other={"meta": "data"})
    assert extra.metavars == {"key": "value"}
    assert extra.other == {"meta": "data"}

    # Test __json__ method
    json_data = extra.__json__()
    assert json_data == {"metavars": {"key": "value"}, "other": {"meta": "data"}}

    # Test from_dict method
    extra_from_dict = Extra.from_dict(
        {"metavars": {"key": "value"}, "custom_field": "custom_value"}
    )
    assert extra_from_dict.metavars == {"key": "value"}
    assert extra_from_dict.other == {"custom_field": "custom_value"}


def test_finding():
    finding = MinimalFinding()
    assert finding.instances == []

    finding = MinimalFinding(
        instances=[MinimalInstance(path="test.py", offset_start=0, offset_end=10)]
    )
    assert len(finding.instances) == 1

    # Test __json__ method
    json_data = finding.__json__()
    assert "instances" in json_data

    # Test from_dict method
    finding_from_dict = MinimalFinding.from_dict(
        {"instances": [{"path": "test.py", "offset_start": 0, "offset_end": 10}]}
    )
    assert len(finding_from_dict.instances) == 1
    assert finding_from_dict.instances[0].path == "test.py"


def test_instance():
    instance = MinimalInstance(path="test.py", offset_start=0, offset_end=10)
    assert instance.path == "test.py"
    assert instance.offset_start == 0
    assert instance.offset_end == 10
    assert instance.fixes == []
    assert isinstance(instance.extra, Extra)

    instance = MinimalInstance(
        path="test.py",
        offset_start=1,
        offset_end=20,
        fixes=["fix1", "fix2"],
        extra=Extra(metavars={"key": "value"}),
    )
    assert instance.path == "test.py"
    assert instance.offset_start == 1
    assert instance.offset_end == 20
    assert instance.fixes == ["fix1", "fix2"]
    assert instance.extra.metavars == {"key": "value"}

    # Test __json__ method
    json_data = instance.__json__()
    assert json_data["path"] == "test.py"
    assert json_data["offset_start"] == 1
    assert json_data["offset_end"] == 20
    assert json_data["fixes"] == ["fix1", "fix2"]
    assert "extra" in json_data

    # Test from_dict method
    instance_from_dict = MinimalInstance.from_dict(
        {
            "path": "test.py",
            "offset_start": 0,
            "offset_end": 10,
            "fixes": ["fix1"],
            "extra": {"metavars": {"key": "value"}},
        }
    )
    assert instance_from_dict.path == "test.py"
    assert instance_from_dict.offset_start == 0
    assert instance_from_dict.offset_end == 10
    assert instance_from_dict.fixes == ["fix1"]
    assert instance_from_dict.extra.metavars == {"key": "value"}


def test_scanner_response():
    response = MinimalScannerResponse()
    assert response.errors == []
    assert response.scanned == []
    assert response.responses == {}

    response = MinimalScannerResponse(
        errors=[Error()],
        scanned=["file1.py"],
        responses={"detector1": MinimalDetectorResponse()},
    )
    assert len(response.errors) == 1
    assert response.scanned == ["file1.py"]
    assert "detector1" in response.responses

    # Test __json__ method
    json_data = response.__json__()
    assert "errors" in json_data
    assert "scanned" in json_data
    assert "responses" in json_data

    # Test from_dict method
    response_from_dict = MinimalScannerResponse.from_dict(
        {
            "errors": [{"message": "test error"}],
            "scanned": ["file1.py"],
            "detector_responses": {"detector1": {"findings": [], "errors": []}},
        }
    )
    assert len(response_from_dict.errors) == 1
    assert response_from_dict.scanned == ["file1.py"]
    assert "detector1" in response_from_dict.responses
