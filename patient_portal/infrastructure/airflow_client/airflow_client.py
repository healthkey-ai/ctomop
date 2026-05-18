import abc
from typing import Any, Dict

from patient_portal.infrastructure.airflow_client.airflow_types import (
    AirflowDag,
    AirflowDagRunState,
    DagRunId,
    TaskId,
)


class AirflowClient(abc.ABC):
    @abc.abstractmethod
    def create_dag_run(
        self,
        dag: AirflowDag,
        dag_run_prefix: str,
        conf: Dict[str, Any] | None,
    ) -> DagRunId:
        """Create a new DAG run. Returns the assigned `dag_run_id`."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_dag_run_state(self, dag: AirflowDag, dag_run_id: DagRunId) -> AirflowDagRunState:
        raise NotImplementedError

    @abc.abstractmethod
    def get_dag_run_task_instances(self, dag: AirflowDag, dag_run_id: DagRunId) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_xcom_entry(
        self,
        dag: AirflowDag,
        dag_run_id: DagRunId,
        task_id: TaskId,
        key: str,
    ) -> Any:
        raise NotImplementedError
