"""REST API client for Dirac settings."""
import json
import time
import urllib.request


class DiracRest:
    """REST API at port 8090."""

    def __init__(self, ip, port=8090):
        self.base = f"http://{ip}:{port}"

    def _put(self, path, timeout=5):
        uid = str(int(time.time() * 1000))
        sep = "&" if "?" in path else "?"
        url = f"{self.base}{path}{sep}id={uid}"
        req = urllib.request.Request(url, method="PUT")
        return urllib.request.urlopen(req, timeout=timeout).read()

    def _get(self, path, timeout=5):
        return urllib.request.urlopen(f"{self.base}{path}", timeout=timeout).read()

    def enable_filtering(self):
        return self._put("/api/filtering?enabled=1")

    def disable_filtering(self):
        return self._put("/api/filtering?enabled=0")

    def set_active_slot(self, index):
        return self._put(f"/api/active-slot?index={index}")

    def set_master_gain(self, gain_db):
        return self._put(f"/api/speaker?gain={gain_db}")

    @property
    def filtering_enabled(self):
        return bool(json.loads(self._get("/api/filtering")).get("enabled", 0))

    @property
    def active_slot(self):
        return int(json.loads(self._get("/api/active-slot")).get("index", -1))

    @property
    def master_gain(self):
        return float(json.loads(self._get("/api/speaker")).get("gain", 0))
