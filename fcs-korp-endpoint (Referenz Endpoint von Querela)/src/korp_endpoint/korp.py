import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Union
from urllib.parse import quote_plus

import requests

# ---------------------------------------------------------------------------


LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://ws.spraakbanken.gu.se/ws/korp/v6/"
MODERN_CORPORA = [
    "ABOUNDERRATTELSER2012",
    "ABOUNDERRATTELSER2013",
    "ASTRA1960-1979",
    "ASTRANOVA",
    "AT2012",
    "ATTASIDOR",
    "BARNLITTERATUR",
    "BLOGGMIX1998",
    "BLOGGMIX1999",
    "BLOGGMIX2000",
    "BLOGGMIX2001",
    "BLOGGMIX2002",
    "BLOGGMIX2003",
    "BLOGGMIX2004",
    "BLOGGMIX2005",
    "BLOGGMIX2006",
    "BLOGGMIX2007",
    "BLOGGMIX2008",
    "BLOGGMIX2009",
    "BLOGGMIX2010",
    "BLOGGMIX2011",
    "BLOGGMIX2012",
    "BLOGGMIX2013",
    "BLOGGMIX2014",
    "BLOGGMIX2015",
    "BLOGGMIXODAT",
    "BORGABLADET",
    "BULLEN",
    "DN1987",
    "FANBARAREN",
    "FINSKTIDSKRIFT",
    "FNB1999",
    "FNB2000",
    "FOF",
    "FORUMFEOT",
    "FSBBLOGGVUXNA",
    "FSBESSAISTIK",
    "FSBSAKPROSA",
    "FSBSKONLIT1960-1999",
    "FSBSKONLIT2000TAL",
    "GP1994",
    "GP2001",
    "GP2002",
    "GP2003",
    "GP2004",
    "GP2005",
    "GP2006",
    "GP2007",
    "GP2008",
    "GP2009",
    "GP2010",
    "GP2011",
    "GP2012",
    "GP2013",
    "GP2D",
    "HANKEITEN",
    "HANKEN",
    "HBL1991",
    "HBL1998",
    "HBL1999",
    "HBL20122013",
    "HBL2014",
    "INFORMATIONSTIDNINGAR",
    "JAKOBSTADSTIDNING1999",
    "JAKOBSTADSTIDNING2000",
    "JFT",
    "KALLAN",
    "LAGTEXTER",
    "MAGMAKOLUMNER",
    "MEDDELANDEN",
    "MYNDIGHET",
    "NYAARGUS",
    "ORDAT",
    "OSTERBOTTENSTIDNING2011",
    "OSTERBOTTENSTIDNING2012",
    "OSTERBOTTENSTIDNING2013",
    "OSTERBOTTENSTIDNING2014",
    "OSTRANYLAND",
    "PARGASKUNGORELSER2011",
    "PARGASKUNGORELSER2012",
    "PRESS65",
    "PRESS76",
    "PRESS95",
    "PRESS96",
    "PRESS97",
    "PRESS98",
    "PROPOSITIONER",
    "ROM99",
    "ROMI",
    "ROMII",
    "SFS",
    "SNP7879",
    "STORSUC",
    "STUDENTBLADET",
    "SUC3",
    "SVENSKBYGDEN",
    "SYDOSTERBOTTEN2010",
    "SYDOSTERBOTTEN2011",
    "SYDOSTERBOTTEN2012",
    "SYDOSTERBOTTEN2013",
    "SYDOSTERBOTTEN2014",
    "TALBANKEN",
    "TWITTER",
    "UNGDOMSLITTERATUR",
    "VASABLADET1991",
    "VASABLADET2012",
    "VASABLADET2013",
    "VASABLADET2014",
    "VASTRANYLAND",
    "WEBBNYHETER2001",
    "WEBBNYHETER2002",
    "WEBBNYHETER2003",
    "WEBBNYHETER2004",
    "WEBBNYHETER2005",
    "WEBBNYHETER2006",
    "WEBBNYHETER2007",
    "WEBBNYHETER2008",
    "WEBBNYHETER2009",
    "WEBBNYHETER2010",
    "WEBBNYHETER2011",
    "WEBBNYHETER2012",
    "WEBBNYHETER2013",
    "WIKIPEDIA-SV",
]


# ---------------------------------------------------------------------------


def get_korp_info(api_base_url: str = API_BASE_URL) -> Optional[Dict[str, Any]]:
    cmd = "command=info"
    url = f"{api_base_url}?{cmd}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as ex:
        LOGGER.error("Korp Info Error: %s", ex)
    except requests.exceptions.JSONDecodeError as ex:
        LOGGER.error("Korp Info Error: %s", ex)
    return None


def get_korp_corpus_info(
    corpora_names: Union[str, List[str]], api_base_url: str = API_BASE_URL
) -> Optional[Dict[str, Any]]:
    if not corpora_names:
        return None
    if isinstance(corpora_names, str):
        corpora_names = [corpora_names]
    corpora_names = ",".join(corpora_names)

    cmd = "command=info&corpus="
    url = f"{api_base_url}?{cmd}{corpora_names}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        result = resp.json()
        return result["corpora"]
    except requests.exceptions.HTTPError as ex:
        LOGGER.error("Korp Corpus Info Error: %s", ex)
    except requests.exceptions.JSONDecodeError as ex:
        LOGGER.error("Korp Corpus Info Error: %s", ex)
    return None


def get_modern_corpora(api_base_url: str = API_BASE_URL) -> List[str]:
    info = get_korp_info(api_base_url=api_base_url)

    protected_corpora = set(info["protected_corpora"])
    open_corpora = info["corpora"]
    open_corpora = [c for c in open_corpora if c not in protected_corpora]
    open_corpora = [c for c in open_corpora if c in MODERN_CORPORA]

    return open_corpora


def make_query(
    cqp_query: str,
    corpora_names: Union[str, List[str], Set[str]],
    start_record: int = 0,
    maximum_records: int = 250,
    api_base_url: str = API_BASE_URL,
) -> Optional[Dict[str, Any]]:
    if not corpora_names:
        return None
    if isinstance(corpora_names, str):
        corpora_names = [corpora_names]
    corpora_names = ",".join(corpora_names)

    start_record = max(0, start_record - 1)
    maximum_records = (
        250 if maximum_records <= 0 else start_record + maximum_records - 1
    )
    cqp_query = quote_plus(cqp_query, encoding="utf-8")

    query_string = "command=query&defaultcontext=1+sentence&show=msd,lemma&cqp="
    range_param = f"&start={start_record}&end={maximum_records}"
    corpus_param = "&corpus="

    url = f"{api_base_url}?{query_string}{cqp_query}{range_param}{corpus_param}{corpora_names}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as ex:
        LOGGER.error("Korp Corpus Info Error: %s", ex)
    except requests.exceptions.JSONDecodeError as ex:
        LOGGER.error("Korp Corpus Info Error: %s", ex)
    return None


# ---------------------------------------------------------------------------
