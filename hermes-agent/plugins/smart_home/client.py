"""Tuya Smart IR Gateway REST Client for Hermes Agent."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).resolve().parent
CONFIG_TXT_PATH = CURRENT_DIR / "config.txt"

DEFAULT_CONFIG = {
    "gateway_url": "http://127.0.0.1:3000",
    "timeout_seconds": 10,
    "default_ac_id": "a35a4e0b12b02aa750ceh4",
    "default_tv_id": "a3378179e35b905deaoudv"
}


def load_config() -> Dict[str, Any]:
    """Load configuration from config.txt dynamically."""
    cfg = dict(DEFAULT_CONFIG)
    if not CONFIG_TXT_PATH.exists():
        return cfg
    try:
        content = CONFIG_TXT_PATH.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip().lower()
                v = v.strip().strip('"').strip("'")
                if k in ("timeout_seconds",):
                    try:
                        cfg[k] = int(v)
                    except ValueError:
                        pass
                else:
                    cfg[k] = v
    except Exception as e:
        logger.warning("Error reading config.txt: %s", e)
    return cfg


class SmartHomeClient:
    """Client communicating with local or network Tuya Smart IR Gateway."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        cfg = load_config()
        self.base_url = (base_url or cfg.get("gateway_url", "http://127.0.0.1:3000")).rstrip("/")
        self.timeout = timeout or cfg.get("timeout_seconds", 10)
        self.default_ac_id = cfg.get("default_ac_id", "a35a4e0b12b02aa750ceh4")
        self.default_tv_id = cfg.get("default_tv_id", "a3378179e35b905deaoudv")

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            res = requests.get(url, timeout=self.timeout)
            if res.status_code == 200:
                return res.json()
            return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"ไม่สามารถเชื่อมต่อไปยัง Tuya Gateway ที่ {self.base_url} ได้ กรุณาตรวจสอบว่าเซิร์ฟเวอร์เปิดอยู่หรือไม่"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _post(self, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            res = requests.post(url, json=payload or {}, timeout=self.timeout)
            if res.status_code in (200, 201):
                return res.json()
            return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"ไม่สามารถเชื่อมต่อไปยัง Tuya Gateway ที่ {self.base_url} ได้ กรุณาตรวจสอบว่าเซิร์ฟเวอร์เปิดอยู่หรือไม่"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Check gateway health and summary."""
        return self._get("/api/status")

    def get_devices(self) -> Dict[str, Any]:
        """List all registered IR remotes and hubs."""
        return self._get("/api/devices")

    def get_scenes(self) -> Dict[str, Any]:
        """List all available automation scenes."""
        return self._get("/api/scenes")

    def control_ac(
        self,
        remote_id: Optional[str] = None,
        power: Optional[bool] = None,
        temperature: Optional[int] = None,
        mode: Optional[str] = None,
        wind_speed: Optional[str] = None,
        swing: Optional[str] = None,
        eco: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Control Air Conditioner via Tuya IR Gateway.
        
        Args:
            remote_id: Remote ID or defaults to configured default AC
            power: True to turn on, False to turn off
            temperature: Desired temperature in Celsius (usually 16-30)
            mode: 'cool', 'auto', 'fan', 'dry', 'heat'
            wind_speed: 'auto', 'low', 'medium', 'high'
            swing: 'on', 'off'
            eco: True, False
        """
        target_id = remote_id or self.default_ac_id
        payload: Dict[str, Any] = {}
        if power is not None:
            payload["power"] = bool(power)
        if temperature is not None:
            payload["temperature"] = int(temperature)
        if mode is not None:
            payload["mode"] = str(mode).lower()
        if wind_speed is not None:
            payload["windSpeed"] = str(wind_speed).lower()
        if swing is not None:
            payload["swing"] = str(swing).lower()
        if eco is not None:
            payload["eco"] = bool(eco)

        return self._post(f"/api/remotes/{target_id}/command", payload)

    def trigger_scene(self, scene_id: str) -> Dict[str, Any]:
        """Trigger an automated scene."""
        return self._post(f"/api/scenes/{scene_id}/trigger")

    def sync_tuya(self) -> Dict[str, Any]:
        """Sync and fetch all newly added remotes from Tuya Cloud."""
        return self._post("/api/sync-tuya", {})

    def find_remote(self, query: Optional[str] = None, device_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find a remote by ID, name substring, or device type."""
        devices = self.get_devices()
        if not devices.get("success"):
            return None
        remotes = devices.get("remotes", [])
        if query:
            q = query.lower().strip()
            for r in remotes:
                if r.get("id") == query or q in r.get("name", "").lower():
                    return r
        if device_type:
            dt = device_type.lower().strip()
            for r in remotes:
                if r.get("type") == dt or dt in r.get("category", "").lower():
                    return r
        return None
