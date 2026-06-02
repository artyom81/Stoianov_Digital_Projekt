import os
import re
import yaml
import time
import unicodedata
from typing import Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://zxpress.ru"

# HTTP Parsing
DEFAULT_HEADERS = {
    "User-Agent": "ZXPressScraper/1.0 (+research; contact: your@email)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def get_soup(url: str, timeout: int = 20, retries: int = 3, sleep_between: float = 0.5) -> Optional[BeautifulSoup]:
    """
    Holt eine URL und gibt BeautifulSoup zurück (UTF-8).
    """
    last_exc = None
    for _ in range(retries):
        try:
            r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            r.encoding = "utf-8"
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            last_exc = e
            time.sleep(sleep_between)
    print(f"⚠️ get_soup fehlgeschlagen für {url}: {last_exc}")
    return None


def absolute_url(base_url: str, href: str) -> str:
    if not href:
        return base_url
    return urljoin(base_url.rstrip("/") + "/", href.lstrip("/"))

def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path

def safe_filename(name: str, max_len: int = 80) -> str:
    """
    Macht aus beliebigen Titeln sichere Dateinamen.
    """
    s = unicodedata.normalize("NFKC", name).strip()
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "untitled"
    if len(s) > max_len:
        s = s[:max_len].rstrip("_")
    return s

def fetch_html(url: str, timeout: int = 20, headers: dict = None) -> str:
    hdrs = DEFAULT_HEADERS.copy()
    if headers:
        hdrs.update(headers)
    r = requests.get(url, headers=hdrs, timeout=timeout)
    r.encoding = "utf-8"
    r.raise_for_status()
    return r.text

def abspath(*parts: str) -> str:
    return os.path.abspath(os.path.join(*parts))
# Russisch (meist Genitiv), plus einfache Nominativ-Varianten
_RU_MONTHS = {
    # genitiv
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    # nominativ (für Bereiche wie "май 1998 – март 2000")
    "январь": 1, "февраль": 2, "март": 3, "апрель": 4, "май": 5, "июнь": 6,
    "июль": 7, "август": 8, "сентябрь": 9, "октябрь": 10, "ноябрь": 11, "декабрь": 12,
}

def parse_ru_date(s: str) -> tuple[str | None, str | None]:
    if not s:
        return None, None
    human = unicodedata.normalize("NFKC", s).strip()
    t = human.lower()

    if "–" in t:
        t = t.split("–", 1)[0].strip()

    tokens = t.replace(",", " ").split()
    try:
        if len(tokens) >= 3 and tokens[0].isdigit() and tokens[2].isdigit():
            day = int(tokens[0])
            mon = _RU_MONTHS.get(tokens[1], None)
            year = int(tokens[2])
            if mon:
                return human, f"{year:04d}-{mon:02d}-{day:02d}"
        if len(tokens) >= 2 and tokens[1].isdigit():
            mon = _RU_MONTHS.get(tokens[0], None)
            year = int(tokens[1])
            if mon:
                return human, f"{year:04d}-{mon:02d}-01"
        if len(tokens) == 1 and tokens[0].isdigit():
            year = int(tokens[0])
            return human, f"{year:04d}-01-01"
    except Exception:
        pass
    return human, None

def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def make_session(cfg: dict | None = None) -> requests.Session:
    """
    Erstellt eine Requests Session mit User-Agent und Retries.
    """
    sess = requests.Session()
    headers = DEFAULT_HEADERS.copy()
    if cfg and isinstance(cfg, dict):
        ua = (cfg.get("http") or {}).get("user_agent")
        if ua:
            headers["User-Agent"] = ua
    sess.headers.update(headers)
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    return sess

def get_soup_session(url: str, session: requests.Session, timeout: int = 20) -> Optional[BeautifulSoup]:
    try:
        r = session.get(url, timeout=timeout)
        r.encoding = "utf-8"
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"⚠️ get_soup_session fehlgeschlagen für {url}: {e}")
        return None

def dump_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)