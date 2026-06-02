import importlib
import logging
from typing import Any
from typing import Dict
from typing import Optional

from clarin.sru.constants import SRUDiagnostics
from clarin.sru.constants import SRUResultCountPrecision
from clarin.sru.diagnostic import SRUDiagnostic
from clarin.sru.diagnostic import SRUDiagnosticList
from clarin.sru.exception import SRUConfigException
from clarin.sru.exception import SRUException
from clarin.sru.fcs.constants import FCS_NS
from clarin.sru.fcs.constants import FCSQueryType
from clarin.sru.fcs.queryparser import FCSQuery
from clarin.sru.fcs.server.search import EndpointDescription
from clarin.sru.fcs.server.search import SimpleEndpointSearchEngineBase
from clarin.sru.fcs.xml.reader import SimpleEndpointDescriptionParser
from clarin.sru.fcs.xml.writer import AdvancedDataViewWriter
from clarin.sru.fcs.xml.writer import FCSRecordXMLStreamWriter
from clarin.sru.fcs.xml.writer import SpanOffsetUnit
from clarin.sru.queryparser import CQLQuery
from clarin.sru.queryparser import SRUQuery
from clarin.sru.queryparser import SRUQueryParserRegistry
from clarin.sru.server.config import SRUServerConfig
from clarin.sru.server.request import SRURequest
from clarin.sru.server.result import SRUScanResultSet
from clarin.sru.server.result import SRUSearchResultSet
from clarin.sru.xml.writer import SRUXMLStreamWriter

from korp_endpoint.korp import API_BASE_URL
from korp_endpoint.korp import get_korp_corpus_info
from korp_endpoint.korp import get_modern_corpora
from korp_endpoint.korp import make_query
from korp_endpoint.query_converter import cql2cqp
from korp_endpoint.query_converter import fcs2cqp
from korp_endpoint.query_converter import fromSUC

# ---------------------------------------------------------------------------


LOGGER = logging.getLogger(__name__)

RESOURCE_INVENTORY_URL_KEY = "se.gu.spraakbanken.fcs.korp.sru.resourceInventoryURL"
API_BASE_URL_KEY = "se.gu.spraakbanken.fcs.korp.sru.apiBaseUrl"
ENDPOINTDESCRIPTION_PACKAGE = "korp_endpoint"
ENDPOINTDESCRIPTION_FILENAME = "endpoint-description.xml"


# ---------------------------------------------------------------------------


# class KorpScanResultSet(SRUScanResultSet):
#     pass


class KorpSearchResultSet(SRUSearchResultSet):
    def __init__(
        self,
        config: SRUServerConfig,
        diagnostics: SRUDiagnosticList,
        resultset: Dict[str, Any],
        query: str,
        corpora_info: Dict[str, Any],
        request: Optional[SRURequest] = None,
    ) -> None:
        super().__init__(diagnostics)
        self.config = config
        self.request = request
        self.resultset = resultset
        self.query = query
        self.corpora_info = corpora_info

        if request:
            self.start_record = max(1, request.get_start_record())
            self.current_record_cursor = self.start_record - 1
            self.maximum_records = self.start_record - 1 + request.get_maximum_records()
            self.record_count = request.get_maximum_records()
        else:
            self.start_record = 1
            self.current_record_cursor = self.start_record - 1
            self.maximum_records = 250
            self.record_count = 250

    def get_total_record_count(self) -> int:
        if self.resultset:
            return self.resultset["hits"]
        return -1

    def get_record_count(self) -> int:
        if self.resultset and self.resultset["hits"] > -1:
            if self.resultset["hits"] < self.maximum_records:
                return self.resultset["hits"]
            else:
                return self.maximum_records
        return 0

    def get_result_count_precision(self) -> Optional[SRUResultCountPrecision]:
        return SRUResultCountPrecision.EXACT

    def get_record_schema_identifier(self) -> str:
        if self.request:
            rsid = self.request.get_record_schema_identifier()
            if rsid:
                return rsid
        return FCS_NS  # CLARIN_FCS_RECORD_SCHEMA

    def next_record(self) -> bool:
        if self.current_record_cursor < min(
            self.resultset["hits"], self.maximum_records
        ):
            self.current_record_cursor += 1
            return True
        return False

    def get_record_identifier(self) -> str:
        return None

    def get_surrogate_diagnostic(self) -> Optional[SRUDiagnostic]:
        if (
            self.get_record_schema_identifier()
            and FCS_NS != self.get_record_schema_identifier()
        ):
            raise SRUDiagnostic(
                SRUDiagnostics.RECORD_NOT_AVAILABLE_IN_THIS_SCHEMA,
                self.get_record_schema_identifier(),
                message=f'Record is not available in record schema "{self.get_record_schema_identifier()}".',
            )
        return None

    def write_record(self, writer: SRUXMLStreamWriter) -> None:
        helper = AdvancedDataViewWriter(SpanOffsetUnit.ITEM)
        wordLayerId = "http://spraakbanken.gu.se/ns/fcs/layer/word"
        lemmaLayerId = "http://spraakbanken.gu.se/ns/fcs/layer/lemma"
        posLayerId = "http://spraakbanken.gu.se/ns/fcs/layer/pos"

        kwic = self.resultset["kwic"][self.current_record_cursor - self.start_record]
        tokens = kwic["tokens"]
        match = kwic["match"]
        corpus: str = kwic["corpus"]

        FCSRecordXMLStreamWriter.startResource(writer, f"{corpus}-{match['position']}")
        FCSRecordXMLStreamWriter.startResourceFragment(writer)

        def _add_spans(idxs: range, start=1, do_highlight=False) -> int:
            kwargs = dict(highlight=1) if do_highlight else {}
            for i in idxs:
                end = start + len(tokens[i]["word"])
                helper.addSpan(wordLayerId, start, end, tokens[i]["word"], **kwargs)
                try:
                    helper.addSpan(
                        posLayerId, start, end, fromSUC(tokens[i]["msd"])[0], **kwargs
                    )
                except SRUException:
                    pass
                helper.addSpan(lemmaLayerId, start, end, tokens[i]["lemma"], **kwargs)
                start = end + 1
            return start

        start = 1
        if match["start"] != 1:
            start = _add_spans(range(match["start"]), start=1)

        start = _add_spans(
            range(match["start"], match["end"]), start=start, do_highlight=True
        )

        if len(tokens) > match["end"]:
            _add_spans(range(match["end"], len(tokens)), start=start)

        helper.writeHitsDataView(writer, wordLayerId)
        if self.request is None or self.request.is_query_type(FCSQueryType.FCS):
            helper.writeAdvancedDataView(writer)

        FCSRecordXMLStreamWriter.endResourceFragment(writer)
        FCSRecordXMLStreamWriter.endResource(writer)


# ---------------------------------------------------------------------------


class KorpEndpointSearchEngine(SimpleEndpointSearchEngineBase):
    """A Korp CLARIN FCS 2.0 endpoint example search engine."""

    def __init__(self) -> None:
        super().__init__()
        self.corporaInfo: Optional[Dict[str, Any]] = None
        self.api_base_url: str = API_BASE_URL

    def _load_bundled_EndpointDescription(self) -> EndpointDescription:
        if not importlib.resources.is_resource(
            ENDPOINTDESCRIPTION_PACKAGE, ENDPOINTDESCRIPTION_FILENAME
        ):
            raise SRUConfigException(
                f"cannot open {ENDPOINTDESCRIPTION_FILENAME} in {ENDPOINTDESCRIPTION_PACKAGE}"
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
        query_parser_registry_builder: SRUQueryParserRegistry.Builder,
        params: Dict[str, str],
    ) -> EndpointDescription:
        riu = params.get(RESOURCE_INVENTORY_URL_KEY)
        if riu is None or riu.isspace():
            LOGGER.debug("Using bundled 'endpoint-description.xml' file")
            return self._load_bundled_EndpointDescription()
        else:
            LOGGER.debug("Using external file '%s'", riu)
            return SimpleEndpointDescriptionParser.parse(riu)

    def do_init(
        self,
        config: SRUServerConfig,
        query_parser_registry_builder: SRUQueryParserRegistry.Builder,
        params: Dict[str, str],
    ) -> None:
        LOGGER.info("KorpEndpointSearchEngine.doInit %s", config.port)

        abu = params.get(API_BASE_URL_KEY)
        if abu is not None and not abu.isspace():
            self.api_base_url = abu
        LOGGER.debug("Korp API base url: %s", self.api_base_url)

        open_corpora = get_modern_corpora(api_base_url=self.api_base_url)
        self.corporaInfo = get_korp_corpus_info(
            open_corpora, api_base_url=self.api_base_url
        )
        if self.corporaInfo is None:
            raise SRUException(
                SRUDiagnostics.GENERAL_SYSTEM_ERROR,
                message="Error querying korp corpus info",
            )

    # ----------------------------------------------------

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
        # translate query
        query: str
        if request.is_query_type(FCSQueryType.CQL):
            # Got a CQL query (either SRU 1.1 or higher).
            # Translate to a proper CQP query ...
            query_in: SRUQuery = request.get_query()
            assert isinstance(query_in, CQLQuery)
            query = cql2cqp(query_in)
        elif request.is_query_type(FCSQueryType.FCS):
            # Got a FCS query (SRU 2.0).
            # Translate to a proper CQP query
            query_in: SRUQuery = request.get_query()
            assert isinstance(query_in, FCSQuery)
            query = fcs2cqp(query_in)
        else:
            # Got something else we don't support. Send error ...
            raise SRUException(
                SRUDiagnostics.CANNOT_PROCESS_QUERY_REASON_UNKNOWN,
                f"Queries with queryType '{request.get_query_type()}' are not supported by this CLARIN-FCS Endpoint.",
            )

        # check fcs context (corpus)
        assert self.corporaInfo is not None
        corpora2query = list(self.corporaInfo.keys())

        # if X_FCS_CONTEXT in request.get_extra_request_data_names():
        #     corpus = request.get_extra_request_data(X_FCS_CONTEXT)
        #     if corpus is not None and not corpus.isspace():
        #         # hdl%3A10794%2Fsbmoderna (default) ?
        #         LOGGER.info("Loading specific corpus data: '{}'", corpus)
        #         corpora2query = [corpus]

        # TODO: map pid/handle to Korp corpusname

        # perform search
        result = make_query(
            query,
            corpora2query,
            request.get_start_record(),
            request.get_maximum_records(),
            api_base_url=self.api_base_url,
        )
        if result is None:
            raise SRUException(
                SRUDiagnostics.CANNOT_PROCESS_QUERY_REASON_UNKNOWN,
                "The query execution failed by this CLARIN-FCS Endpoint.",
            )
        return KorpSearchResultSet(
            config=config,
            diagnostics=diagnostics,
            resultset=result,
            query=query,
            corpora_info=self.corporaInfo,
            request=request,
        )

    # ----------------------------------------------------


# ---------------------------------------------------------------------------
