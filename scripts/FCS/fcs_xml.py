from lxml import etree

NS_SRU = "http://docs.oasis-open.org/ns/search-ws/sruResponse"
NS_FCS = "http://clarin.eu/fcs/1.0"
NS_HITS = "http://clarin.eu/fcs/dataview/1.0"
NS_ZR = "http://explain.z3950.org/dtd/2.1/"

NSMAP = {
    "sru": NS_SRU,
    "fcs": NS_FCS,
    "hits": NS_HITS,
    "zr": NS_ZR,
}


def _sru_root(local_name: str):
    return etree.Element(etree.QName(NS_SRU, local_name), nsmap=NSMAP)


def sru_diagnostic_xml(code: str, message: str, details: str = "", version: str = "2.0") -> bytes:
    root = _sru_root("diagnostics")
    etree.SubElement(root, etree.QName(NS_SRU, "version")).text = version

    diag = etree.SubElement(root, etree.QName(NS_SRU, "diagnostic"))
    etree.SubElement(diag, etree.QName(NS_SRU, "uri")).text = f"info:srw/diagnostic/1/{code}"
    etree.SubElement(diag, etree.QName(NS_SRU, "details")).text = details or ""
    etree.SubElement(diag, etree.QName(NS_SRU, "message")).text = message or ""

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


def fcs_explain_xml(meta: dict, version: str = "2.0") -> bytes:
    root = _sru_root("explainResponse")
    etree.SubElement(root, etree.QName(NS_SRU, "version")).text = version

    record = etree.SubElement(root, etree.QName(NS_SRU, "record"))
    etree.SubElement(record, etree.QName(NS_SRU, "recordSchema")).text = NS_FCS
    etree.SubElement(record, etree.QName(NS_SRU, "recordPacking")).text = "packed"
    etree.SubElement(record, etree.QName(NS_SRU, "recordXMLEscaping")).text = "xml"
    record_data = etree.SubElement(record, etree.QName(NS_SRU, "recordData"))

    edesc = etree.SubElement(record_data, etree.QName(NS_FCS, "EndpointDescription"))

    caps = meta.get("capabilities") or []
    if caps:
        caps_el = etree.SubElement(edesc, etree.QName(NS_FCS, "Capabilities"))
        for c in caps:
            etree.SubElement(caps_el, etree.QName(NS_FCS, "capability")).text = c

    dvs = meta.get("supported_data_views") or []
    if dvs:
        sdv = etree.SubElement(edesc, etree.QName(NS_FCS, "SupportedDataViews"))
        for dv in dvs:
            etree.SubElement(sdv, etree.QName(NS_FCS, "dataView")).text = dv

    cols = meta.get("collections") or []
    if cols:
        cols_el = etree.SubElement(edesc, etree.QName(NS_FCS, "Collections"))
        for c in cols:
            cx = etree.SubElement(cols_el, etree.QName(NS_FCS, "Collection"))
            etree.SubElement(cx, etree.QName(NS_FCS, "id")).text = c.get("id", "")
            etree.SubElement(cx, etree.QName(NS_FCS, "label")).text = c.get("label", "")

    langs = meta.get("languages") or []
    if langs:
        langs_el = etree.SubElement(edesc, etree.QName(NS_FCS, "Languages"))
        for lang in langs:
            etree.SubElement(langs_el, etree.QName(NS_FCS, "language")).text = lang

    if meta.get("default_language"):
        etree.SubElement(edesc, etree.QName(NS_FCS, "DefaultLanguage")).text = meta["default_language"]

    fields = meta.get("fields") or []
    if fields:
        fld = etree.SubElement(edesc, etree.QName(NS_FCS, "Fields"))
        for f in fields:
            fx = etree.SubElement(fld, etree.QName(NS_FCS, "field"))
            etree.SubElement(fx, etree.QName(NS_FCS, "name")).text = f.get("name", "")
            etree.SubElement(fx, etree.QName(NS_FCS, "type")).text = f.get("type", "text")
            etree.SubElement(fx, etree.QName(NS_FCS, "stored")).text = "true" if f.get("stored", True) else "false"
            etree.SubElement(fx, etree.QName(NS_FCS, "indexed")).text = "true" if f.get("indexed", True) else "false"

    if meta.get("maxPageSize"):
        etree.SubElement(edesc, etree.QName(NS_FCS, "MaxPageSize")).text = str(meta["maxPageSize"])

    if meta.get("meta"):
        m = etree.SubElement(edesc, etree.QName(NS_FCS, "Meta"))
        if meta["meta"].get("rights"):
            etree.SubElement(m, etree.QName(NS_FCS, "rights")).text = meta["meta"]["rights"]
        if meta["meta"].get("license"):
            etree.SubElement(m, etree.QName(NS_FCS, "license")).text = meta["meta"]["license"]

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")

def sru_explain_xml(
    meta: dict,
    *,
    host: str,
    port: str,
    database_path: str,
    version: str = "2.0",
) -> bytes:
    root = _sru_root("explainResponse")
    etree.SubElement(root, etree.QName(NS_SRU, "version")).text = version

    record = etree.SubElement(root, etree.QName(NS_SRU, "record"))
    etree.SubElement(record, etree.QName(NS_SRU, "recordSchema")).text = NS_ZR
    etree.SubElement(record, etree.QName(NS_SRU, "recordPacking")).text = "packed"
    etree.SubElement(record, etree.QName(NS_SRU, "recordXMLEscaping")).text = "xml"
    record_data = etree.SubElement(record, etree.QName(NS_SRU, "recordData"))

    explain = etree.SubElement(record_data, etree.QName(NS_ZR, "explain"))
    explain.set("authoritative", "true")

    server_info = etree.SubElement(explain, etree.QName(NS_ZR, "serverInfo"))
    server_info.set("protocol", "SRU")
    server_info.set("version", version)
    server_info.set("transport", "http")
    server_info.set("method", "GET")
    server_info.set("host", host)
    server_info.set("port", port)
    server_info.set("database", database_path)

    database_info = etree.SubElement(explain, etree.QName(NS_ZR, "databaseInfo"))

    title = meta.get("title") or "ZX Press Corpus"
    etree.SubElement(database_info, etree.QName(NS_ZR, "title")).text = title

    description = meta.get("description") or "SRU/FCS endpoint for the ZX Press corpus."
    etree.SubElement(database_info, etree.QName(NS_ZR, "description")).text = description

    if meta.get("meta", {}).get("rights"):
        etree.SubElement(database_info, etree.QName(NS_ZR, "restrictions")).text = meta["meta"]["rights"]

    index_info = etree.SubElement(explain, etree.QName(NS_ZR, "indexInfo"))

    index_defs = [
        ("cql.serverChoice", "All searchable text fields"),
        ("title", "Article title"),
        ("content", "Article content"),
        ("magazine", "Magazine name"),
        ("language", "Language"),
        ("form", "Publication form"),
    ]

    for idx_name, idx_title in index_defs:
        idx = etree.SubElement(index_info, etree.QName(NS_ZR, "index"))
        etree.SubElement(idx, etree.QName(NS_ZR, "title")).text = idx_title
        map_el = etree.SubElement(idx, etree.QName(NS_ZR, "map"))
        etree.SubElement(map_el, etree.QName(NS_ZR, "name"), set="cql").text = idx_name

    schema_info = etree.SubElement(explain, etree.QName(NS_ZR, "schemaInfo"))
    schema = etree.SubElement(schema_info, etree.QName(NS_ZR, "schema"))
    schema.set("name", "fcs")
    schema.set("identifier", NS_FCS)
    etree.SubElement(schema, etree.QName(NS_ZR, "title")).text = "CLARIN-FCS"

    config_info = etree.SubElement(explain, etree.QName(NS_ZR, "configInfo"))
    etree.SubElement(config_info, etree.QName(NS_ZR, "default"), type="numberOfRecords").text = "10"
    etree.SubElement(config_info, etree.QName(NS_ZR, "setting"), type="maximumRecords").text = str(
        meta.get("maxPageSize") or 50
    )

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")

def fcs_searchretrieve_xml(*, records, total, start_record, maximum_records, query_str, version: str = "2.0") -> bytes:
    root = _sru_root("searchRetrieveResponse")
    etree.SubElement(root, etree.QName(NS_SRU, "version")).text = version

    echo = etree.SubElement(root, etree.QName(NS_SRU, "echoedSearchRetrieveRequest"))
    etree.SubElement(echo, etree.QName(NS_SRU, "version")).text = version
    etree.SubElement(echo, etree.QName(NS_SRU, "query")).text = query_str or ""
    etree.SubElement(echo, etree.QName(NS_SRU, "startRecord")).text = str(start_record)
    etree.SubElement(echo, etree.QName(NS_SRU, "maximumRecords")).text = str(maximum_records)

    returned = len(records) if maximum_records else 0
    if maximum_records and (start_record - 1 + returned) < total:
        etree.SubElement(root, etree.QName(NS_SRU, "nextRecordPosition")).text = str(start_record + returned)

    etree.SubElement(root, etree.QName(NS_SRU, "numberOfRecords")).text = str(total)

    recs = etree.SubElement(root, etree.QName(NS_SRU, "records"))
    for i, r in enumerate(records, start=start_record):
        rec = etree.SubElement(recs, etree.QName(NS_SRU, "record"))
        etree.SubElement(rec, etree.QName(NS_SRU, "recordSchema")).text = NS_FCS
        etree.SubElement(rec, etree.QName(NS_SRU, "recordPacking")).text = "packed"
        etree.SubElement(rec, etree.QName(NS_SRU, "recordXMLEscaping")).text = "xml"
        rdata = etree.SubElement(rec, etree.QName(NS_SRU, "recordData"))
        res = etree.SubElement(rdata, etree.QName(NS_FCS, "Resource"))

        rh = etree.SubElement(res, etree.QName(NS_FCS, "ResourceHeader"))
        etree.SubElement(rh, etree.QName(NS_FCS, "title")).text = r.get("title", "")

        ident = r.get("id") or r.get("article_url") or r.get("identifier") or ""
        if ident:
            etree.SubElement(rh, etree.QName(NS_FCS, "identifier")).text = ident

        extents = etree.SubElement(rh, etree.QName(NS_FCS, "extents"))
        if r.get("magazine"):
            ex = etree.SubElement(extents, etree.QName(NS_FCS, "extent"))
            ex.set("type", "magazine")
            ex.text = r.get("magazine", "")
        if r.get("issue_label"):
            ex = etree.SubElement(extents, etree.QName(NS_FCS, "extent"))
            ex.set("type", "issue")
            ex.text = r.get("issue_label", "")
        if r.get("issue_date_iso"):
            ex = etree.SubElement(extents, etree.QName(NS_FCS, "extent"))
            ex.set("type", "date")
            ex.text = r.get("issue_date_iso", "")

        dv = etree.SubElement(res, etree.QName(NS_FCS, "DataView"))
        dv.set("type", "hits:kwic-1.0")

        for k in r.get("kwic", []) or []:
            kw = etree.SubElement(dv, etree.QName(NS_HITS, "kwic"))
            etree.SubElement(kw, etree.QName(NS_HITS, "leftContext")).text = k.get("left", "")
            etree.SubElement(kw, etree.QName(NS_HITS, "match")).text = k.get("match", "")
            etree.SubElement(kw, etree.QName(NS_HITS, "rightContext")).text = k.get("right", "")

        etree.SubElement(rec, etree.QName(NS_SRU, "recordPosition")).text = str(i)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")