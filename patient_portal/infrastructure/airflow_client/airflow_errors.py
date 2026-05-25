import datetime


class AirflowError(Exception):
    """Base class for Airflow errors."""
    url: str
    method: str

    def __init__(self, description: str, url: str, method: str, **kwargs):
        self.url = url
        self.method = method
        values = {
            "url": url,
            "method": method,
            **kwargs,
        }
        values_str = ", ".join([f"{k}={v}" for k, v in values.items()])
        super().__init__(f"{description} {values_str}")


class BadCodeAirflowError(AirflowError):
    """Raised when the Airflow REST API returns a non-2xx response."""
    elapsed: datetime.timedelta
    response_code: int
    response: str

    def __init__(self, url: str, method: str, elapsed: datetime.timedelta, response_code: int, response: str):
        self.elapsed = elapsed
        self.response_code = response_code
        self.response = response
        super().__init__(
            description="Bad response code from Airflow server",
            url=url,
            method=method,
            elapsed=elapsed,
            response_code=response_code,
            response=response,
        )
