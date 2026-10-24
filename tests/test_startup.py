import pytest
import importlib.metadata


@pytest.mark.concept("SFDC-1.0")
def test_startup():
    import re

    import salesforce_agent

    assert re.fullmatch(r"\d+\.\d+\.\d+", importlib.metadata.version("salesforce-agent"))


@pytest.mark.concept("SFDC-1.0")
def test_core_surface_exposed():
    import salesforce_agent

    assert callable(salesforce_agent.Api)
    assert callable(salesforce_agent.SalesforceAuth)
    assert callable(salesforce_agent.SalesforceConfig)
    assert callable(salesforce_agent.get_client)
