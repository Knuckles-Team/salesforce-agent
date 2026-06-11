"""CONCEPT:SFDC-1.2 Input-model contracts for the action-routed tool surface."""

import json

import pytest
from pydantic import ValidationError

from salesforce_agent.salesforce_input_models import (
    BulkJobCreateInput,
    BulkResultsInput,
    CollectionsDeleteInput,
    CollectionsInput,
    CompositeInput,
    RecordGetInput,
    RecordUpsertInput,
    ReportRunInput,
    SoqlQueryInput,
    SoslSearchInput,
)


@pytest.mark.concept("SFDC-1.2")
class TestInputModels:
    def test_soql_query_round_trips_to_params_json(self):
        model = SoqlQueryInput(soql="SELECT Id FROM Account", max_records=100)
        params = json.loads(model.model_dump_json(exclude_none=True))
        assert params == {"soql": "SELECT Id FROM Account", "max_records": 100}

    def test_sosl_search_requires_sosl(self):
        with pytest.raises(ValidationError):
            SoslSearchInput.model_validate({})

    def test_record_get_matches_tool_param_keys(self):
        model = RecordGetInput(sobject="Account", id="001A", fields=["Name"])
        assert set(model.model_dump(exclude_none=True)) == {"sobject", "id", "fields"}

    def test_record_upsert_requires_external_id_fields(self):
        with pytest.raises(ValidationError):
            RecordUpsertInput.model_validate(
                {"sobject": "Account", "data": {"Name": "Acme"}}
            )

    def test_composite_defaults_all_or_none_false(self):
        model = CompositeInput(subrequests=[{"method": "GET", "url": "/x"}])
        assert model.all_or_none is False

    def test_collections_inputs_carry_records_and_ids(self):
        create = CollectionsInput(records=[{"attributes": {"type": "Account"}}])
        delete = CollectionsDeleteInput(ids=["001A", "001B"])
        assert create.records and delete.ids == ["001A", "001B"]

    def test_bulk_job_create_rejects_unknown_operation(self):
        with pytest.raises(ValidationError):
            BulkJobCreateInput.model_validate(
                {"sobject": "Account", "operation": "merge"}
            )

    def test_bulk_results_kind_default_is_successful(self):
        assert BulkResultsInput(job_id="750A").kind == "successful"

    def test_report_run_defaults_include_details(self):
        assert ReportRunInput(report_id="00OA").include_details is True
