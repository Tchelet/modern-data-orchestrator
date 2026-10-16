from __future__ import annotations

import time
from typing import Any

import requests


TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "canceled", "incomplete"}


class AirbyteClient:
    """Small wrapper around Airbyte OSS API variants used in local installs."""

    def __init__(
        self,
        base_url: str,
        api_mode: str = "public",
        auth: tuple[str, str] | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_mode = api_mode.lower()
        self.auth = auth
        self.timeout_seconds = timeout_seconds

    def trigger_sync(self, connection_id: str) -> int:
        if not connection_id:
            raise RuntimeError("AIRBYTE_CONNECTION_ID is required to trigger a sync.")

        if self.api_mode == "legacy":
            response = self._post(
                "connections/sync",
                {"connectionId": connection_id},
            )
        else:
            response = self._post(
                "jobs",
                {"connectionId": connection_id, "jobType": "sync"},
            )

        job_id = self._extract_job_id(response)
        if job_id is None:
            raise RuntimeError(f"Airbyte sync response did not include a job id: {response}")
        return job_id

    def get_job_status(self, job_id: int) -> str:
        if self.api_mode == "legacy":
            response = self._post("jobs/get", {"id": job_id})
        else:
            response = self._get(f"jobs/{job_id}")

        status = self._extract_status(response)
        if not status:
            raise RuntimeError(f"Airbyte job response did not include a status: {response}")
        return status.lower()

    def wait_for_job(
        self,
        job_id: int,
        poll_seconds: int,
        timeout_seconds: int,
    ) -> str:
        started_at = time.monotonic()
        while True:
            status = self.get_job_status(job_id)
            if status in TERMINAL_STATUSES:
                if status != "succeeded":
                    raise RuntimeError(f"Airbyte job {job_id} finished with status {status}.")
                return status

            if time.monotonic() - started_at > timeout_seconds:
                raise TimeoutError(
                    f"Airbyte job {job_id} did not finish within {timeout_seconds} seconds."
                )

            time.sleep(poll_seconds)

    def _get(self, path: str) -> dict[str, Any]:
        response = requests.get(
            self._url(path),
            auth=self.auth,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            self._url(path),
            json=payload,
            auth=self.auth,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    @staticmethod
    def _extract_job_id(response: dict[str, Any]) -> int | None:
        candidates = (
            response.get("jobId"),
            response.get("id"),
            response.get("job", {}).get("id") if isinstance(response.get("job"), dict) else None,
        )
        for candidate in candidates:
            if candidate is not None:
                return int(candidate)
        return None

    @staticmethod
    def _extract_status(response: dict[str, Any]) -> str | None:
        candidates = (
            response.get("status"),
            response.get("job", {}).get("status") if isinstance(response.get("job"), dict) else None,
        )
        for candidate in candidates:
            if candidate:
                return str(candidate)
        return None
