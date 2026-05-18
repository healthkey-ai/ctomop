import datetime
import logging
from typing import Any, Dict

import requests

from patient_portal.infrastructure.airflow_client.airflow_client import AirflowClient
from patient_portal.infrastructure.airflow_client.airflow_errors import AirflowError, BadCodeAirflowError
from patient_portal.infrastructure.airflow_client.airflow_types import (
    AirflowDag,
    AirflowDagRunState,
    DagRunId,
    TaskId,
)

_logger = logging.getLogger(__name__)


class AirflowClientImplementation(AirflowClient):
    def __init__(self, airflow_url: str, airflow_username: str, airflow_password: str):
        self._base_url = airflow_url
        self._username = airflow_username
        self._password = airflow_password

    def create_dag_run(
        self,
        dag: AirflowDag,
        dag_run_prefix: str,
        conf: Dict[str, Any] | None,
    ) -> DagRunId:
        url = self._base_url + "/dags/" + dag.value + "/dagRuns"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")
        dag_run_id = dag_run_prefix + "__" + timestamp
        payload = {
            "conf": conf,
            "dag_run_id": dag_run_id,
        }
        return self._request_with_error_handling(url, "post", payload).json()["dag_run_id"]

    def get_dag_run_state(self, dag: AirflowDag, dag_run_id: DagRunId) -> AirflowDagRunState:
        url = self._base_url + f"/dags/{dag.value}/dagRuns/{dag_run_id}"
        state_str = self._request_with_error_handling(url, "get", None).json()["state"]
        try:
            return AirflowDagRunState(state_str)
        except ValueError:
            raise AirflowError(
                description=f"Unexpected state {state_str} (missing enum value?)",
                url=url,
                method="get",
            )

    def get_dag_run_task_instances(self, dag: AirflowDag, dag_run_id: DagRunId) -> Dict[str, Any]:
        url = self._base_url + f"/dags/{dag.value}/dagRuns/{dag_run_id}/taskInstances"
        return self._request_with_error_handling(url, "get", None).json()

    def get_xcom_entry(
        self,
        dag: AirflowDag,
        dag_run_id: DagRunId,
        task_id: TaskId,
        key: str,
    ) -> Any:
        url = (
            self._base_url
            + f"/dags/{dag.value}/dagRuns/{dag_run_id}/taskInstances/{task_id}/xcomEntries/{key}"
        )
        return self._request_with_error_handling(url, "get", None).json()["value"]

    def _request_with_error_handling(
        self,
        url: str,
        method: str,
        payload: Dict[str, Any] | None,
    ) -> requests.Response:
        try:
            return self._request(url, method, payload)
        except AirflowError:
            raise
        except Exception as e:
            raise AirflowError(
                description=str(e),
                url=url,
                method=method,
            ) from e

    def _request(self, url: str, method: str, payload: Dict[str, Any] | None) -> requests.Response:
        started_at = datetime.datetime.now()
        response = requests.request(
            method=method,
            url=url,
            auth=(self._username, self._password),
            json=payload,
        )
        elapsed = datetime.datetime.now() - started_at
        _logger.info(
            "Airflow request url=%s method=%s elapsed=%s response_code=%s",
            url, method, elapsed, response.status_code,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise BadCodeAirflowError(
                url=url,
                method=method,
                elapsed=elapsed,
                response_code=response.status_code,
                response=response.text,
            ) from e
        return response
