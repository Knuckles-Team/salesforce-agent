import pytest


@pytest.mark.concept("SFDC-1.0")
def test_init_dynamics():
    import salesforce_agent

    assert salesforce_agent._MCP_AVAILABLE is True
    assert salesforce_agent._AGENT_AVAILABLE is True


@pytest.mark.concept("SFDC-1.0")
def test_unknown_attribute_raises():
    import salesforce_agent

    missing_attribute = "does_not_exist"
    with pytest.raises(AttributeError):
        getattr(salesforce_agent, missing_attribute)
