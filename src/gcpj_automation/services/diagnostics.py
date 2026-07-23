"""Safe diagnostics for selector calibration."""

from __future__ import annotations

import json
from datetime import datetime

from ..browser.gcpj_page import GCPJClosurePage
from ..browser.selectors import SelectorRegistry
from ..browser.session import CDPBrowserSession
from ..config import AppSettings


def collect_diagnostic(settings: AppSettings) -> bytes:
    selectors = SelectorRegistry(settings.selectors_path)
    with CDPBrowserSession(settings) as session:
        page = session.find_gcpj_page()
        gcpj = GCPJClosurePage(page, settings, selectors)
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "page": gcpj.diagnostic_snapshot(),
            "configured_selector_keys": selectors.keys(),
        }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
