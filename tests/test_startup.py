import pytest


@pytest.mark.concept("SFDC-1.0")
def test_startup():
    import salesforce_agent

    assert salesforce_agent.__version__ == "0.1.0"


@pytest.mark.concept("SFDC-1.0")
def test_core_surface_exposed():
    import salesforce_agent

    assert callable(salesforce_agent.Api)
    assert callable(salesforce_agent.SalesforceAuth)
    assert callable(salesforce_agent.SalesforceConfig)
    assert callable(salesforce_agent.get_client)


@pytest.mark.concept("SFDC-1.0")
def test_mcp_server_entrypoints_importable():
    from salesforce_agent.mcp_server import get_mcp_instance, mcp_server

    assert callable(get_mcp_instance)
    assert callable(mcp_server)


@pytest.mark.concept("SFDC-1.0")
def test_agent_server_entrypoint_importable():
    from salesforce_agent.agent_server import agent_server

    assert callable(agent_server)
