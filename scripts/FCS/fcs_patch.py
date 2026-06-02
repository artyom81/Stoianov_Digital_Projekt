from org.apache.lucene.analysis.tokenattributes import CharTermAttribute
from java.io import StringReader

def _analyze_terms(text: str, analyzer) -> list[str]:
    if not text:
        return []
    ts = analyzer.tokenStream("content", StringReader(text))
    term_attr = ts.addAttribute(CharTermAttribute.class_)
    ts.reset()
    terms = []
    while ts.incrementToken():
        terms.append(term_attr.toString())
    ts.end()
    ts.close()
    return terms

def _fallback_boolean_query(terms: list[str]) -> BooleanQuery:
    b = BooleanQuery.Builder()
    for t in terms:
        # auf content ODER title matchen
        b_sub = BooleanQuery.Builder()
        b_sub.add(TermQuery(Term("content", t)), BooleanClause.Occur.SHOULD)
        b_sub.add(TermQuery(Term("title",   t)), BooleanClause.Occur.SHOULD)
        b.add(b_sub.build(), BooleanClause.Occur.MUST)
    return b.build() if terms else MatchAllDocsQuery()