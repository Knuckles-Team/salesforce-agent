"""Metadata describe, record counts, and limits."""

import pytest


@pytest.mark.concept("SFDC-1.2")
class TestDescribe:
    def test_global_describe(self, fake, api):
        result = api.describe.global_describe()
        assert [s["name"] for s in result["sobjects"]] == ["Account", "Contact"]

    def test_sobject_describe_fields_and_picklists(self, fake, api):
        result = api.describe.sobject("Account")
        assert result["name"] == "Account"
        field = result["fields"][0]
        assert field["type"] == "picklist"
        assert field["picklistValues"] == [{"value": "Energy"}]
        assert result["childRelationships"][0]["childSObject"] == "Contact"

    def test_record_counts_all(self, fake, api):
        result = api.describe.record_counts()
        assert result["sObjects"][0]["count"] == 10

    def test_record_counts_filtered(self, fake, api):
        result = api.describe.record_counts(["Account", "Contact"])
        assert [s["name"] for s in result["sObjects"]] == ["Account", "Contact"]
        assert fake.api_requests[-1].url.params["sObjects"] == "Account,Contact"

    def test_limits(self, fake, api):
        result = api.describe.limits()
        assert result["DailyApiRequests"]["Remaining"] == 14998

    def test_versioned_paths(self, fake, api):
        api.describe.limits()
        assert fake.api_requests[-1].url.path == "/services/data/v62.0/limits"
