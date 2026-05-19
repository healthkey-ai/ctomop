from enum import StrEnum

DagRunId = str

TaskId = str


class AirflowDag(StrEnum):
    """DAGs registered in the healthkey-etl Airflow instance.

    Values must match the `dag_id` declared in the corresponding DAG file.
    """

    FHIR_INGEST = "fhir_ingest"


class AirflowDagRunState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"

    def is_finished(self) -> bool:
        return self.is_done() or self.is_failed()

    def is_done(self) -> bool:
        return self == AirflowDagRunState.SUCCESS

    def is_failed(self) -> bool:
        return self in (
            AirflowDagRunState.FAILED,
            AirflowDagRunState.CANCELLED,
        )
