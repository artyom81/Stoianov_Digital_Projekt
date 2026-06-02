import importlib.resources
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import lucene
from java.nio.file import Paths
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.search import IndexSearcher, MatchAllDocsQuery
from org.apache.lucene.store import FSDirectory

from clarin.sru.constants import SRUDiagnostics, SRUResultCountPrecision
from clarin.sru.diagnostic import SRUDiagnostic, SRUDiagnosticList
from clarin.sru.exception import SRUConfigException, SRUException
from clarin.sru.fcs.constants import FCS_NS, FCSQueryType
from clarin.sru.fcs.server.search import EndpointDescription, SimpleEndpointSearchEngineBase
from clarin.sru.fcs.xml.reader import SimpleEndpointDescriptionParser
from clarin.sru.fcs.xml.writer import FCSRecordXMLStreamWriter
from clarin.sru.queryparser import CQLQuery, SRUQuery
from clarin.sru.server.config import SRUServerConfig
from clarin.sru.server.request import SRURequest
from clarin.sru.server.result import SRUScanResultSet, SRUSearchResultSet
from clarin.sru.xml.writer import SRUXMLStreamWriter

from scripts.FCS.fcs_endpoint import build_query, _normalize_kwic_term
from scripts.TextSearch.Searcher import kwic, _fallback_snippet


LOGGER = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
INDEX_DIR = str(BASE_DIR / "index_dir")

ENDPOINTDESCRIPTION_PACKAGE = "scripts.FCS_Server"
ENDPOINTDESCRIPTION_FILENAME = "endpoint-description.xml"

def _extra(request: SRURequest, name: str, default=None):
    try:
        value = request.get_extra_request_data(name)
    except Exception:
        return default
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    return value

class ZXSearchResultSet(SRUSearchResultSet):
    def __init__(
        self,
        diagnostics: SRUDiagnosticList,
        records: List[Dict[str, Any]],
        total: int,
        request: Optional[SRURequest] = None,
    ) -> None:
        super().__init__(diagnostics)
        self.records = records
        self.total = total
        self.request = request

        if request:
            self.start_record = max(1, request.get_start_record())
            self.maximum_records = request.get_maximum_records()
        else:
            self.start_record = 1
            self.maximum_records = len(records)

        self.current_record_cursor = 0

    def get_total_record_count(self) -> int:
        return self.total

    def get_record_count(self) -> int:
        return len(self.records)

    def get_result_count_precision(self) -> Optional[SRUResultCountPrecision]:
        return SRUResultCountPrecision.EXACT

    def get_record_schema_identifier(self) -> str:
        if self.request:
            rsid = self.request.get_record_schema_identifier()
            if rsid:
                return rsid
        return FCS_NS

    def next_record(self) -> bool:
        if self.current_record_cursor < len(self.records):
            self.current_record_cursor += 1
            return True
        return False

    def get_record_identifier(self) -> Optional[str]:
        if 0 < self.current_record_cursor <= len(self.records):
            return self.records[self.current_record_cursor - 1].get("identifier")
        return None

    def get_surrogate_diagnostic(self) -> Optional[SRUDiagnostic]:
        if (
            self.get_record_schema_identifier()
            and FCS_NS != self.get_record_schema_identifier()
        ):
            raise SRUDiagnostic(
                SRUDiagnostics.RECORD_NOT_AVAILABLE_IN_THIS_SCHEMA,
                self.get_record_schema_identifier(),
                message=(
                    f'Record is not available in record schema '
                    f'"{self.get_record_schema_identifier()}".'
                ),
            )
        return None

    def write_record(self, writer: SRUXMLStreamWriter) -> None:
        rec = self.records[self.current_record_cursor - 1]

        title = rec.get("title") or "Untitled"
        identifier = rec.get("identifier") or ""
        snippets = rec.get("snippets") or []

        FCSRecordXMLStreamWriter.startResource(writer, title, identifier)
        FCSRecordXMLStreamWriter.startResourceFragment(writer, identifier or None)

        for snip in snippets:
            FCSRecordXMLStreamWriter.writeSingleHitHitsDataView(
                writer,
                left=snip.get("left", ""),
                hit=snip.get("match", ""),
                right=snip.get("right", ""),
            )

        FCSRecordXMLStreamWriter.endResourceFragment(writer)
        FCSRecordXMLStreamWriter.endResource(writer)

class ZXSearchEngine(SimpleEndpointSearchEngineBase):
    def _load_bundled_EndpointDescription(self) -> EndpointDescription:
        if not importlib.resources.is_resource(
            ENDPOINTDESCRIPTION_PACKAGE, ENDPOINTDESCRIPTION_FILENAME
        ):
            raise SRUConfigException(
                f"cannot open {ENDPOINTDESCRIPTION_FILENAME} "
                f"in {ENDPOINTDESCRIPTION_PACKAGE}"
            )

        with importlib.resources.open_text(
            ENDPOINTDESCRIPTION_PACKAGE,
            ENDPOINTDESCRIPTION_FILENAME,
            encoding="utf-8",
            errors="strict",
        ) as fp:
            return SimpleEndpointDescriptionParser.parse(fp)

    def create_EndpointDescription(
        self,
        config: SRUServerConfig,
        query_parser_registry_builder,
        params: Dict[str, str],
    ) -> EndpointDescription:
        LOGGER.warning("ZXSearchEngine.create_EndpointDescription called")
        return self._load_bundled_EndpointDescription()

    def do_init(
        self,
        config: SRUServerConfig,
        query_parser_registry_builder,
        params: Dict[str, str],
    ) -> None:
        LOGGER.warning("ZXSearchEngine.do_init called")
        lucene.initVM(vmargs=["-Djava.awt.headless=true"])
        lucene.getVMEnv().attachCurrentThread()
        self.reader = DirectoryReader.open(FSDirectory.open(Paths.get(INDEX_DIR)))
        self.searcher = IndexSearcher(self.reader)

    def do_scan(
        self,
        config: SRUServerConfig,
        request: SRURequest,
        diagnostics: SRUDiagnosticList,
    ) -> SRUScanResultSet:
        return None

    def search(
        self,
        config: SRUServerConfig,
        request: SRURequest,
        diagnostics: SRUDiagnosticList,
    ) -> SRUSearchResultSet:
        LOGGER.warning("ZXSearchEngine.search called")

        raw_query = ""
        if request.is_query_type(FCSQueryType.CQL):
            query_in: SRUQuery = request.get_query()
            assert isinstance(query_in, CQLQuery)
            raw_query = str(query_in)
        else:
            raise SRUException(
                SRUDiagnostics.CANNOT_PROCESS_QUERY_REASON_UNKNOWN,
                f"Queries with queryType '{request.get_query_type()}' "
                f"are not supported by this endpoint.",
            )

        lang = _extra(request, "x-language", "ru")
        y_from = _extra(request, "x-yearFrom")
        y_to = _extra(request, "x-yearTo")
        mag = _extra(request, "x-magazine")
        form_ = _extra(request, "x-form")

        if raw_query:
            lucene_q = build_query(
                qtext=raw_query,
                magazine=mag,
                form=form_,
                lang=lang,
                year_from=int(y_from) if y_from else None,
                year_to=int(y_to) if y_to else None,
            )
        else:
            lucene_q = MatchAllDocsQuery()

        start = max(1, request.get_start_record())
        maxre = max(0, request.get_maximum_records())
        fetch = start - 1 + maxre if maxre > 0 else 0

        total = self.searcher.count(lucene_q)
        out_records: List[Dict[str, Any]] = []

        if maxre > 0:
            fetch = min(max(1, fetch), 1000)
            hits = self.searcher.search(lucene_q, fetch).scoreDocs
            window = hits[start - 1 : start - 1 + maxre]
            sf = self.reader.storedFields()

            kwic_term = _normalize_kwic_term(_extra(request, "x-kwicTerm") or raw_query)
            kwic_window = int(_extra(request, "x-kwicWindow", 5))

            def split_lmr(snippet: str, needle: str):
                s_l = (snippet or "").lower()
                n_l = (needle or "").lower()
                i = s_l.find(n_l)
                if i == -1:
                    return ("", snippet or "", "")
                j = i + len(needle)
                return ((snippet or "")[:i], (snippet or "")[i:j], (snippet or "")[j:])

            for sd in window:
                doc = sf.document(sd.doc)
                title = doc.get("title") or doc.get("filename") or f"doc-{sd.doc}"
                identifier = doc.get("article_url") or doc.get("print_url") or str(sd.doc)

                snippets = []
                if kwic_term:
                    content = doc.get("content") or ""
                    snips = kwic(content, kwic_term, window=kwic_window, max_snips=3) or []
                    if not snips:
                        fb = _fallback_snippet(content, kwic_term, chars=180)
                        if fb:
                            snips = [fb]

                    for s in snips:
                        left, match, right = split_lmr(s, kwic_term)
                        snippets.append(
                            {"left": left, "match": match, "right": right}
                        )

                if not snippets:
                    snippets = [{"left": "", "match": title, "right": ""}]

                out_records.append(
                    {
                        "identifier": identifier,
                        "title": title,
                        "snippets": snippets,
                    }
                )

        return ZXSearchResultSet(
            diagnostics=diagnostics,
            records=out_records,
            total=total,
            request=request,
        )