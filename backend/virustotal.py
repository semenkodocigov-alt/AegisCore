"""VirusTotal API v3 client used by background scan workers."""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any

import requests


API_BASE = "https://www.virustotal.com/api/v3"
REPORT_BASE = "https://www.virustotal.com/gui/file"
MAX_UPLOAD_BYTES = 32 * 1024 * 1024
REQUEST_TIMEOUT = (5, 15)
API_KEY_PATTERN = re.compile(r"^[A-Fa-f0-9]{64}$")
EMPTY_FILE_SHA256 = hashlib.sha256(b"").hexdigest()


class VirusTotalError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_api_key(api_key: str) -> bool:
    return bool(API_KEY_PATTERN.fullmatch(api_key.strip()))


def _handle_error(response: requests.Response) -> None:
    if response.status_code == 401:
        raise VirusTotalError("VIRUSTOTAL_INVALID_KEY", "VirusTotal API key is invalid.")
    if response.status_code == 429:
        raise VirusTotalError("VIRUSTOTAL_RATE_LIMIT", "VirusTotal rate limit reached. Try again later.")
    if response.status_code == 403:
        raise VirusTotalError("VIRUSTOTAL_FORBIDDEN", "VirusTotal denied access to this resource.")
    if response.status_code >= 400:
        raise VirusTotalError(
            "VIRUSTOTAL_API_ERROR",
            "VirusTotal request failed. Check your API access.",
        )


def test_api_key(api_key: str, session: requests.Session | None = None) -> None:
    if not validate_api_key(api_key):
        raise VirusTotalError("VIRUSTOTAL_INVALID_FORMAT", "Enter a valid 64-character VirusTotal API key.")
    client = session or requests.Session()
    try:
        response = client.get(
            f"{API_BASE}/files/{EMPTY_FILE_SHA256}",
            headers={"x-apikey": api_key.strip()},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code not in (200, 404):
            _handle_error(response)
    except requests.Timeout as error:
        raise VirusTotalError("VIRUSTOTAL_TIMEOUT", "VirusTotal request timed out.") from error
    except requests.RequestException as error:
        raise VirusTotalError("VIRUSTOTAL_NETWORK_ERROR", "Could not connect to VirusTotal.") from error
    finally:
        if "response" in locals():
            response.close()
        if session is None:
            client.close()


def _sha256(filepath: str) -> str:
    digest = hashlib.sha256()
    try:
        with open(filepath, "rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise VirusTotalError("VIRUSTOTAL_FILE_ERROR", "Could not read the file for VirusTotal lookup.") from error
    return digest.hexdigest()


def _request(
    session: requests.Session,
    method: str,
    url: str,
    api_key: str,
    **kwargs: Any,
) -> requests.Response:
    try:
        response = session.request(
            method,
            url,
            headers={"x-apikey": api_key},
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
    except requests.Timeout as error:
        raise VirusTotalError("VIRUSTOTAL_TIMEOUT", "VirusTotal request timed out.") from error
    except requests.RequestException as error:
        raise VirusTotalError("VIRUSTOTAL_NETWORK_ERROR", "Could not connect to VirusTotal.") from error
    if response.status_code not in (200, 201, 404):
        try:
            _handle_error(response)
        except VirusTotalError:
            response.close()
            raise
    return response


def _report(sha256: str, attributes: dict[str, Any]) -> dict[str, Any]:
    stats = attributes.get("last_analysis_stats")
    if not isinstance(stats, dict):
        raise VirusTotalError("VIRUSTOTAL_INVALID_RESPONSE", "VirusTotal returned an invalid file report.")
    malicious = int(stats.get("malicious", 0) or 0)
    suspicious = int(stats.get("suspicious", 0) or 0)
    total = sum(int(value or 0) for value in stats.values() if isinstance(value, (int, float)))
    results = attributes.get("last_analysis_results", {})
    detections = []
    if isinstance(results, dict):
        for engine, value in results.items():
            if not isinstance(value, dict) or value.get("category") not in ("malicious", "suspicious"):
                continue
            detections.append({
                "engine": str(engine),
                "label": str(value.get("result") or value.get("category")),
            })
    return {
        "status": "detected" if malicious or suspicious else "clean",
        "sha256": sha256,
        "malicious": malicious,
        "suspicious": suspicious,
        "total": total,
        "detections": detections[:10],
        "reportUrl": f"{REPORT_BASE}/{sha256}",
        "message": "VirusTotal analysis is available.",
    }


def _scan_file_with_session(
    filepath: str,
    api_key: str,
    upload_unknown: bool = False,
    client: requests.Session | Any = None,
) -> dict[str, Any]:
    if not validate_api_key(api_key):
        raise VirusTotalError("VIRUSTOTAL_INVALID_FORMAT", "Enter a valid 64-character VirusTotal API key.")
    sha256 = _sha256(filepath)
    response = _request(client, "GET", f"{API_BASE}/files/{sha256}", api_key.strip())
    try:
        if response.status_code == 200:
            body = response.json()
            attributes = body.get("data", {}).get("attributes")
            if not isinstance(attributes, dict):
                raise VirusTotalError("VIRUSTOTAL_INVALID_RESPONSE", "VirusTotal returned an invalid file report.")
            return _report(sha256, attributes)
    finally:
        response.close()

    result: dict[str, Any] = {
        "status": "not_found",
        "sha256": sha256,
        "malicious": 0,
        "suspicious": 0,
        "total": 0,
        "detections": [],
        "reportUrl": f"{REPORT_BASE}/{sha256}",
        "message": "No VirusTotal report was found for this file.",
    }
    if not upload_unknown:
        return result

    try:
        size = os.path.getsize(filepath)
    except OSError as error:
        raise VirusTotalError("VIRUSTOTAL_FILE_ERROR", "Could not read the file for VirusTotal upload.") from error
    if size >= MAX_UPLOAD_BYTES:
        raise VirusTotalError("VIRUSTOTAL_FILE_TOO_LARGE", "Files must be smaller than 32 MB to upload.")

    try:
        with open(filepath, "rb") as file:
            upload_response = client.post(
                f"{API_BASE}/files",
                headers={"x-apikey": api_key.strip()},
                files={"file": (os.path.basename(filepath), file)},
                timeout=REQUEST_TIMEOUT,
            )
    except requests.Timeout as error:
        raise VirusTotalError("VIRUSTOTAL_TIMEOUT", "VirusTotal request timed out.") from error
    except requests.RequestException as error:
        raise VirusTotalError("VIRUSTOTAL_NETWORK_ERROR", "Could not connect to VirusTotal.") from error
    if upload_response.status_code not in (200, 201):
        try:
            _handle_error(upload_response)
        finally:
            upload_response.close()
    try:
        body = upload_response.json()
    except ValueError as error:
        raise VirusTotalError("VIRUSTOTAL_INVALID_RESPONSE", "VirusTotal returned an invalid upload response.") from error
    finally:
        upload_response.close()
    analysis_id = body.get("data", {}).get("id")
    if not isinstance(analysis_id, str) or not analysis_id:
        raise VirusTotalError("VIRUSTOTAL_INVALID_RESPONSE", "VirusTotal did not return an analysis identifier.")
    result.update(
        status="queued",
        analysisId=analysis_id,
        message="File uploaded; VirusTotal analysis is queued.",
    )
    return result


def scan_file(
    filepath: str,
    api_key: str,
    upload_unknown: bool = False,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    if session is not None:
        return _scan_file_with_session(filepath, api_key, upload_unknown, session)
    with requests.Session() as client:
        return _scan_file_with_session(filepath, api_key, upload_unknown, client)
