from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Optional

import random
import httpx

from dashboard.settings import BNG_CONTROLLER_BASE_URL

log = logging.getLogger(__name__)


def _preview_text(s: str, limit: int = 500) -> str:
    s = s.replace("\n", "\\n")
    if len(s) > limit:
        return s[:limit] + f"...(+{len(s) - limit} chars)"
    return s


def _safe_json_preview(resp: httpx.Response, limit: int = 800) -> str:
    """Try to show json preview, fall back to text preview."""
    try:
        data = resp.json()
        dumped = json.dumps(data, ensure_ascii=False)
        return _preview_text(dumped, limit=limit)
    except Exception:
        try:
            return _preview_text(resp.text, limit=limit)
        except Exception:
            return "<no body>"


class BngBlasterControllerClient:
    """Client for the BNG Blaster Controller REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = (base_url or BNG_CONTROLLER_BASE_URL).rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"

    def _make_client(self) -> httpx.AsyncClient:
        """
        Create an AsyncClient with request/response hooks for logging.
        """
        async def on_request(request: httpx.Request) -> None:
            rid = request.extensions.get("rid", "-")
            log.debug("[rid=%s] --> %s %s", rid, request.method, request.url)
            # Log small JSON payload preview if present
            if request.content:
                # content may be bytes; try decode
                try:
                    body = request.content.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                except Exception:
                    body = str(request.content)
                # log.debug("[rid=%s] request body=%s", rid, _preview_text(body, 800))

        async def on_response(response: httpx.Response) -> None:
            rid = response.request.extensions.get("rid", "-")
            elapsed_ms = response.extensions.get("elapsed_ms", None)
            log.debug(
                "[rid=%s] <-- %s %s (%s) %s",
                rid,
                response.request.method,
                response.request.url,
                response.status_code,
                f"{elapsed_ms}ms" if elapsed_ms is not None else "",
            )
            log.debug("[rid=%s] response body=%s", rid, _safe_json_preview(response))

        return httpx.AsyncClient(
            timeout=self.timeout,
            event_hooks={
                "request": [on_request],
                "response": [on_response],
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        rid = uuid.uuid4().hex[:12]
        url = self._url(path)

        t0 = time.perf_counter()
        async with self._make_client() as client:
            try:
                req = client.build_request(method, url, json=json_body)
                req.extensions["rid"] = rid
                log.info("[rid=%s] Sending %s request to %s", rid, method, url)
                if json_body:
                    log.info("[rid=%s] Request body: %s", rid, _preview_text(json.dumps(json_body)))
                resp = await client.send(req)
                resp.extensions["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)

                # If error: log details before raising
                if resp.status_code >= 400:
                    log.error(
                        "[rid=%s] HTTP %s for %s %s body=%s",
                        rid,
                        resp.status_code,
                        method,
                        url,
                        _safe_json_preview(resp),
                    )
                    resp.raise_for_status()

                return resp

            except httpx.HTTPError as exc:
                log.exception("[rid=%s] httpx error for %s %s: %s", rid, method, url, exc)
                raise

            except Exception as exc:
                log.exception("[rid=%s] unexpected error for %s %s: %s", rid, method, url, exc)
                raise

    async def list_instances(self) -> list[str]:
        resp = await self._request("GET", "/api/v1/instances")
        data = resp.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected list_instances payload type: {type(data)}")
        return [str(x) for x in data]

    async def upload_config(
        self,
        instance_name: str,
        config_obj: dict[str, Any],
    ) -> dict[str, Any]:
        # PUT config
        await self._request("PUT", f"/api/v1/instances/{instance_name}", json_body=config_obj)

        # Verify stored config
        resp = await self._request("GET", f"/api/v1/instances/{instance_name}/config.json")
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected config.json payload type: {type(data)}")
        return data


    async def update_instance_config(self, instance_name: str, cfg: dict):
        # Beispiel-Endpoint:
        # PUT /api/v1/instances/{name}/config
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.put(
                f"{self.base_url}/api/v1/instances/{instance_name}/config",
                json=cfg,
            )
            r.raise_for_status()
            return r.json() if r.headers.get("content-type","").startswith("application/json") else r.text

    
    async def get_instance_config(self, instance_name: str) -> dict[str, Any]:
        """
        Retrieves the stored configuration for a specific instance.
        """
        # The BNG Blaster Controller stores the config under config.json
        url = f"/api/v1/instances/{instance_name}/config.json"
        
        resp = await self._request("GET", url)
        data = resp.json()
        
        if not isinstance(data, dict):
            raise RuntimeError(
                f"Unexpected config payload type for {instance_name}: {type(data)}"
            )
        return data
    
    async def get_instance_status(
        self,
        instance_name: str,
    ) -> str:
        url_base = f"/api/v1/instances/{instance_name}"

        try:
            resp = await self._request("GET", url_base)
            data = resp.json()


            status = data.get("status")
            return str(status or "")
        except Exception as exc:
            log.warning("get_instance_status failed for %s: %s", instance_name, exc)
            return ""
        
    async def start_instance(
        self,
        instance_name: str,
        start_params: dict[str, Any],
    ) -> dict[str, Any]:
        url_base = f"/api/v1/instances/{instance_name}"
        log.debug("Starting instance %s with params: %s", instance_name, start_params)
        try:
            resp = await self._request("GET", url_base)
            log.debug("get_instance_status for %s: %s", instance_name, resp.json())
            status = resp.json().get("status")
            log.debug("pre-check status for %s: %s", instance_name, status)
            if status == "started":
                log.debug("instance %s already started -> stopping first", instance_name)
                await self.stop_instance(instance_name)
        except Exception as exc:
            log.warning("pre-check failed for %s (ignored): %s", instance_name, exc)

        # Start
        await self._request("POST", f"{url_base}/_start", json_body=start_params)

        # Read back
        resp = await self._request("GET", url_base)
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected start_instance payload type: {type(data)}")
        return data

    async def stop_instance_1(self, instance_name: str) -> dict[str, Any]:
        url_base = f"/api/v1/instances/{instance_name}"

        await self._request("POST", f"{url_base}/_stop")

        resp = await self._request("GET", url_base)
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected stop_instance payload type: {type(data)}")
        return data
    
    async def stop_instance(self, instance_name: str) -> dict[str, Any]:
        """
        Stops the instance and waits until the status is 'stopped' 
        using an incremental backoff polling logic.
        """
        url_base = f"/api/v1/instances/{instance_name}"

        # 1. Send the stop command
        await self._request("POST", f"{url_base}/_stop")

        # 2. Initial wait (corresponds to time.sleep(1) in Robot)
        await asyncio.sleep(1)

        counter = 0
        while counter < 5:
            # 3. Fetch current status
            resp = await self._request("GET", url_base)
            data = resp.json()
            
            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected status payload type: {type(data)}")

            status = data.get("status")

            # 4. Check if stopped
            if status == "stopped":
                return data
            
            # 5. Incremental backoff: 1s, 3s, 5s, 7s, 9s
            wait_time = counter * 2 + 1
            counter += 1
            
            # Optional: Log the status and wait time here
            # print(f"Instance {instance_name} is still {status}, waiting {wait_time}s...")
            
            await asyncio.sleep(wait_time)

        # 6. Fallback if not stopped after 5 retries
        # You could also raise a TimeoutError here depending on your needs
        resp = await self._request("GET", url_base)
        return resp.json()
    
    async def delete_instance(self, instance_name: str) -> httpx.Response:
        url_base = f"/api/v1/instances/{instance_name}"

        resp = await self._request("DELETE", f"{url_base}")

        return resp

    async def get_run_report(self, instance_name: str) -> dict[str, Any]:
        url_base = f"/api/v1/instances/{instance_name}"
                
        counter = 0
        while counter < 5:
            # Request the run-report
            resp = await self._request("GET", f"{url_base}/run_report.json")
            
            # Check if the request was successful
            if resp.status_code == 200:
                data = resp.json()
                # If the report is valid and contains data, return it
                if data and isinstance(data, dict):
                    return data
            
            # Incremental backoff: 1s, 3s, 5s, 7s, 9s
            wait_time = counter * 2 + 1
            counter += 1
            
            # Optional: logging could be added here
            await asyncio.sleep(wait_time)
            
        # If no report is found after 5 retries, return an empty dict or raise an error
        return {}

    async def instance_command(
        self,
        instance_name: str,
        command: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a controller '_command' to an instance."""
        arguments = arguments or {}
        path = f"/api/v1/instances/{instance_name}/_command"
        payload = {"command": command, "arguments": arguments}
        # log.debug(f"Sending instance command: {payload} to {path}")
        resp = await self._request("POST", path, json_body=payload)

        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected instance_command payload type: {type(data)}")
        return data


    async def instance_command_with_retries(
        self,
        instance_name: str,
        command: str,
        arguments: dict[str, Any] | None = None,
        *,
        retries: int = 3,
        base_delay: float = 0.25,
        max_delay: float = 2.0,
    ) -> dict[str, Any]:
        
        RETRY_STATUS = {500, 502, 503, 504}

        """Send a controller '_command' to an instance."""
        arguments = arguments or {}
        path = f"/api/v1/instances/{instance_name}/_command"
        payload = {"command": command, "arguments": arguments}

        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                resp = await self._request("POST", path, json_body=payload)

                # Wenn _request NICHT raise_for_status macht:
                status = getattr(resp, "status_code", None)
                if status in RETRY_STATUS and attempt < retries:
                    delay = min(max_delay, base_delay * (2 ** attempt))
                    delay *= (0.8 + 0.4 * random.random())
                    await asyncio.sleep(delay)
                    continue

                # Wenn _request raise_for_status macht, kommst du bei 5xx hier gar nicht hin.
                data = resp.json()
                if not isinstance(data, dict):
                    raise RuntimeError(f"Unexpected instance_command payload type: {type(data)}")
                
                log.info(f"instance_command '{command}' \ndata: \n{data} \n(attempt {attempt+1})")
                return data

            except Exception as e:
                # Wenn _request bei 5xx schon Exception wirft, landen wir hier.
                # Versuche Statuscode herauszulesen (httpx/requests-like)
                status = getattr(e, "status_code", None)
                if status is None and hasattr(e, "response") and e.response is not None:
                    status = getattr(e.response, "status_code", None)

                retryable = (status in RETRY_STATUS) or (status is None)

                if (not retryable) or (attempt >= retries):
                    raise

                last_error = e
                delay = min(max_delay, base_delay * (2 ** attempt))
                delay *= (0.8 + 0.4 * random.random())
                await asyncio.sleep(delay)

        # sollte nicht passieren
        raise last_error or RuntimeError("instance_command failed")
