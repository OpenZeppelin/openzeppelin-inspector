import pytest
from inspector.models.issue_template import IssueTemplate, IssueReport
from inspector.models.metadata_models import DetectorMetadata


def test_issue_template_default():
    template = IssueTemplate()
    assert template.title == ""
    assert template.opening == ""
    assert template.body == ""
    assert template.body_single_file_single_instance == ""
    assert template.body_single_file_multiple_instance == ""
    assert template.body_multiple_file_multiple_instance == ""
    assert template.body_list_item_intro == ""
    assert template.body_list_item == ""
    assert template.body_list_item_single_file == ""
    assert template.body_list_item_multiple_file == ""
    assert template.closing == ""


def test_issue_template_from_dict_empty():
    template = IssueTemplate.from_dict({})
    assert template.title == ""
    assert template.opening == ""
    assert template.body == ""


def test_issue_template_from_dict_partial():
    data = {"title": "Test Title", "opening": "Test Opening", "body": "Test Body"}
    template = IssueTemplate.from_dict(data)
    assert template.title == "Test Title"
    assert template.opening == "Test Opening"
    assert template.body == "Test Body"
    assert template.closing == ""


def test_issue_template_from_dict_with_hyphenated_keys():
    data = {
        "body-single-file-single-instance": "Single File Single",
        "body-multiple-file-multiple-instance": "Multiple Files Multiple",
    }
    template = IssueTemplate.from_dict(data)
    assert template.body_single_file_single_instance == "Single File Single"
    assert template.body_multiple_file_multiple_instance == "Multiple Files Multiple"


def test_issue_report_default():
    report = IssueReport()
    assert report.severity == 0
    assert report.tags == []
    assert isinstance(report.template, IssueTemplate)


def test_issue_report_from_dict_empty():
    report = IssueReport.from_dict({})
    assert report.severity == 0
    assert report.tags == []
    assert isinstance(report.template, IssueTemplate)


def test_issue_report_from_dict_with_data():
    data = {
        "severity": 2,
        "tags": ["security", "critical"],
        "template": {"title": "Test Title", "body": "Test Body"},
    }
    report = IssueReport.from_dict(data)
    assert report.severity == 2
    assert report.tags == ["security", "critical"]
    assert report.template.title == "Test Title"
    assert report.template.body == "Test Body"


def test_detector_metadata_default():
    metadata = DetectorMetadata()
    assert metadata.id == ""
    assert metadata.uid == ""
    assert metadata.description == ""
    assert metadata.description_full == ""
    assert metadata.scanners == []
    assert metadata.references == []
    assert isinstance(metadata.report, IssueReport)


def test_detector_metadata_from_dict_with_data():
    data = {
        "id": "test-id",
        "uid": "test-uid",
        "description": "Test Description",
        "description-full": "Full Description",
        "scanners": ["scanner1", "scanner2"],
        "references": ["ref1", "ref2"],
        "report": {
            "severity": 2,
            "tags": ["security"],
            "template": {"title": "Test Title"},
        },
    }
    metadata = DetectorMetadata.from_dict(data)
    assert metadata.id == "test-id"
    assert metadata.uid == "test-uid"
    assert metadata.description == "Test Description"
    assert metadata.description_full == "Full Description"
    assert metadata.scanners == ["scanner1", "scanner2"]
    assert metadata.references == ["ref1", "ref2"]
    assert metadata.report.severity == 2
    assert metadata.report.tags == ["security"]
    assert metadata.report.template.title == "Test Title"
