"""Identity, org info, and analytics report surfaces."""

import pytest


@pytest.mark.concept("SFDC-1.2")
class TestAdmin:
    def test_user_info(self, fake, api):
        result = api.admin.user_info()
        assert result["preferred_username"] == "integration@example.com"
        assert fake.api_requests[-1].url.path == "/services/oauth2/userinfo"

    def test_org_info_queries_organization(self, fake, api):
        api.admin.org_info()
        assert "FROM Organization" in fake.api_requests[-1].url.params["q"]

    def test_list_reports(self, fake, api):
        result = api.admin.list_reports()
        assert result[0]["name"] == "Pipeline"

    def test_run_report(self, fake, api):
        result = api.admin.run_report("00Oxx0000000001")
        assert result["factMap"]["T!T"]["aggregates"][0]["value"] == 42
        assert fake.api_requests[-1].url.params["includeDetails"] == "true"

    def test_run_report_without_details(self, fake, api):
        result = api.admin.run_report("00Oxx0000000001", include_details=False)
        assert result["includeDetails"] == "false"
