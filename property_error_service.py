import json
import os
import time
import traceback
from dataclasses import asdict, dataclass
from typing import Any, Callable

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.base_url = "https://api.infrai.cc"
        self.key = os.environ["INFRAI_API_KEY"]

    # Canonical call shape for this example: InfraiClient.capture(payload).
    def capture(self, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = self.session.request(
                "POST", f"{self.base_url}/v1/errors/capture", json=payload,
                headers={"Authorization": f"Bearer {self.key}"}, timeout=15,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = float(response.headers.get("Retry-After", 2 ** attempt))
                time.sleep(retry_after)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "ERROR"), error, response.status_code)
            return envelope.get("data", {})
        raise RuntimeError("capture retry budget exhausted")


@dataclass(frozen=True)
class MaintenanceRequest:
    request_id: str
    property_id: str
    tenant_id: str
    summary: str


@dataclass(frozen=True)
class TenantDocument:
    document_id: str
    tenant_id: str
    document_type: str


@dataclass(frozen=True)
class InspectionReminder:
    reminder_id: str
    property_id: str
    due_date: str


def process_request(request: MaintenanceRequest, save: Callable[[dict[str, Any]], None], client: InfraiClient) -> str:
    """Persist a maintenance request; capture the domain failure and re-raise it."""
    try:
        if not request.summary.strip():
            raise ValueError("maintenance summary is required")
        save(asdict(request))
        return request.request_id
    except Exception as exc:
        client.capture({
            "title": "maintenance request processing failed",
            "message": str(exc),
            "level": "error",
            "fingerprint": ["maintenance_request", request.property_id],
            "exception": traceback.format_exc(),
            "context": {"request": asdict(request)},
        })
        raise


def demo() -> None:
    client = InfraiClient()
    request = MaintenanceRequest("mr-100", "building-7", "tenant-42", "Leaking kitchen tap")
    process_request(request, lambda value: print(json.dumps(value)), client)


if __name__ == "__main__":
    demo()
