"""
A Korp CLARIN FCS 2.0 endpoint example converter of FCS to CQP.
"""

import logging
from typing import List
from typing import Union

import cql
import fcsql.parser
from clarin.sru.constants import SRUDiagnostics
from clarin.sru.exception import SRUException
from clarin.sru.fcs.constants import FCSDiagnostics
from clarin.sru.fcs.queryparser import FCSQuery
from clarin.sru.queryparser import CQLQuery

# ---------------------------------------------------------------------------


LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------


def cql2cqp(query: CQLQuery) -> str:
    """Convert CQL query to CQP query string.

    Args:
        query: the CQL query

    Returns:
        str: the CQP Query

    Raises:
        SRUException: If the query is too complex or it cannot be performed for any other reason
    """

    node: Union[
        cql.parser.CQLTriple, cql.parser.CQLSearchClause
    ] = query.parsed_query.root

    # Translate the CQL query to a Lucene query.
    # If a CQL feature was used, that is not supported by us,
    # throw a SRU error (with a detailed error message)
    # Right now, we're pretty stupid and only support terms

    if isinstance(node, cql.parser.CQLTriple):
        operator = node.operator.value
        raise SRUException(
            SRUDiagnostics.UNSUPPORTED_BOOLEAN_OPERATOR,
            operator,
            message=f"Unsupported Boolean operator: {operator}",
        )

    if isinstance(node, cql.parser.CQLSearchClause):
        terms = node.term.lower().split()  # .casefold()?
        if len(terms) == 1:
            return f"[word = '{terms[0]}']"

        # from java implementation, not sure whether this is the best escaping strategy ...
        terms = [term.strip("\"'") for term in terms]
        return "".join(f"[word = '{term}']" for term in terms)

    raise SRUException(
        SRUDiagnostics.CANNOT_PROCESS_QUERY_REASON_UNKNOWN, f"unknown cql node: {node}"
    )


# ---------------------------------------------------------------------------


def fcs2cqp(query: FCSQuery) -> str:
    """Convert FCS-QL query to CQP query string.

    Args:
        query: the FCS-QL query

    Returns:
        str: the CQP query

    Raises:
        SRUException: If the query is too complex or it cannot be performed for any other reason
    """
    tree: fcsql.parser.QueryNode = query.parsed_query
    LOGGER.debug("FCS-Query: %s", tree)

    # A somewhat crude query translator
    if isinstance(tree, fcsql.parser.QuerySequence):
        return _transform_query_sequence(tree)
    if isinstance(tree, fcsql.parser.QuerySegment):
        return _transform_query_segment(tree)
    raise SRUException(
        FCSDiagnostics.GENERAL_QUERY_TOO_COMPLEX_CANNOT_PERFORM_QUERY,
        message="Endpoint only supports sequences or single segment queries",
    )


def _transform_query_sequence(tree: fcsql.parser.QuerySequence) -> str:
    return "".join(
        _transform_query_segment(child)
        for child in tree.children
        if isinstance(child, fcsql.parser.QuerySegment)
    )


def _transform_query_segment(segment: fcsql.parser.QuerySegment) -> str:
    op: fcsql.parser.Expression = segment.get_expression()
    if isinstance(op, fcsql.parser.ExpressionAnd):
        return f"[{_transform_expression_bool_op(op, ' & ')}]"
    if isinstance(op, fcsql.parser.ExpressionOr):
        return f"[{_transform_expression_bool_op(op, ' | ')}]"

    occ_str = _transform_occurrences(segment.min_occurs, segment.max_occurs)

    if isinstance(op, fcsql.parser.Expression):
        return f"[{_transform_expression(op)}]{occ_str}"
    if isinstance(op, fcsql.parser.ExpressionWildcard):
        return f" []{occ_str}"

    raise SRUException(
        FCSDiagnostics.GENERAL_QUERY_TOO_COMPLEX_CANNOT_PERFORM_QUERY,
        message="Endpoint only supports sequences or single segment expressions",
    )


def _transform_occurrences(min: int, max: int) -> str:
    if min == max == 1:
        return " "
    if min == max:
        return f"{{{min}}} "
    return f"{{{min},{max}}} "


def _transform_expression_bool_op(
    op: Union[fcsql.parser.ExpressionAnd, fcsql.parser.ExpressionOr], op_str: str
) -> str:
    assert (
        len(op.operands) == 2
    ), "Boolean Expression should only have exactly two operands!"
    return f"{_transform_expression(op.operands[0])}{op_str}{_transform_expression(op.operands[1])}"


def _transform_expression(expression: fcsql.parser.Expression) -> str:
    if (
        expression.identifier in ("text", "token", "word", "lemma", "pos")
        and expression.qualifier is None
        and expression.operator
        in (fcsql.parser.Operator.EQUALS, fcsql.parser.Operator.NOT_EQUALS)
        # and expression.regex_flags is None
    ):
        # Not really worth it using regexFlags
        # Still handled in getWordLayerFilter(). /ljo

        # Translate PoS value or just get the text/word layer as is.
        if expression.identifier == "pos":
            return _translate_pos(
                expression.identifier,
                _translate_operator(expression.operator),
                expression.regex,
            )
        if expression.identifier == "lemma":
            return _translate_lemma_layer_filter(expression)
        return _translate_word_layer_filter(expression)

    raise SRUException(
        FCSDiagnostics.GENERAL_QUERY_TOO_COMPLEX_CANNOT_PERFORM_QUERY,
        "Endpoint only supports 'text', 'word', 'lemma', and 'pos' layers, the '=' and '!=' operators and no regex flags",
    )


def _translate_pos(layer_identifier: str, operator: str, pos: str) -> str:
    sucT = toSUC(pos)
    sucPos = sucT[0] if len(sucT) == 1 else f"({'|'.join(sucT)})"

    return f"{layer_identifier} {operator} '{sucPos}'"


def _translate_operator(op: fcsql.parser.Operator) -> str:
    return "!=" if op is fcsql.parser.Operator.NOT_EQUALS else "="


def _translate_operatorw(op: fcsql.parser.Operator) -> str:
    return "not contains" if op is fcsql.parser.Operator.NOT_EQUALS else "contains"


def _translate_flags(expression: fcsql.parser.Expression) -> str:
    flags = []
    if expression.regex_flags:
        if fcsql.parser.RegexFlag.CASE_INSENSITIVE in expression.regex_flags:
            flags.append("c")
        if fcsql.parser.RegexFlag.CASE_SENSITIVE in expression.regex_flags:
            pass
        if fcsql.parser.RegexFlag.LITERAL_MATCHING in expression.regex_flags:
            flags.append("l")
        if fcsql.parser.RegexFlag.IGNORE_DIACRITICS in expression.regex_flags:
            flags.append("d")
    return f" %{''.join(flags)}" if flags else ""


def _translate_word_layer_filter(expression: fcsql.parser.Expression) -> str:
    layer_identifier = (
        "word" if expression.identifier in ("text", "token") else expression.identifier
    )

    return f"{layer_identifier} {_translate_operator(expression.operator)} '{expression.regex}'{_translate_flags(expression)}"


def _translate_lemma_layer_filter(expression: fcsql.parser.Expression) -> str:
    return f"{expression.identifier} {_translate_operatorw(expression.operator)} '{expression.regex}'{_translate_flags(expression)}"


# ---------------------------------------------------------------------------


UD172SUC = {
    "NOUN": ["NN"],
    "PROPN": ["PM"],
    "ADJ": ["JJ", "PC", "RO"],
    "VERB": ["VB", "PC"],
    "AUX": ["VB"],
    "NUM": ["RG", "RO"],  # No RO?
    "PRON": ["PN", "PS", "HP", "HS"],  # No PS, HS?
    "DET": ["DT", "HD", "HS", "PS"],
    "PART": ["IE"],
    "ADV": ["AB", "HA", "PL"],  # No PL?
    "ADP": ["PL", "PP"],  # No PL?
    "CCONJ": ["KN"],
    "SCONJ": ["SN"],
    "INTJ": ["IN"],
    "PUNCT": ["MAD", "MID", "PAD"],
    "X": ["UO"],
}

SUC2UD17 = {
    # fixme! - check lemma/msd for toUd17
    "NN": ["NOUN"],
    "PM": ["PROPN"],
    "VB": ["VERB", "AUX"],
    "IE": ["PART"],
    "PC": ["VERB"],  # No ADJ?
    "PL": ["PART"],  # No ADV, ADP?
    "PN": ["PRON"],
    "PS": ["DET"],  # No PRON?
    "HP": ["PRON"],
    "HS": ["DET"],  # No PRON?
    "DT": ["DET"],
    "HD": ["DET"],
    "JJ": ["ADJ"],
    "AB": ["ADV"],
    "HA": ["ADV"],
    "KN": ["CCONJ"],
    "SN": ["SCONJ"],
    "PP": ["ADP"],
    "RG": ["NUM"],
    "RO": ["ADJ"],  # No NUM?
    "IN": ["INTJ"],
    # Could be any PoS, most probably a noun /ljo
    "UO": ["X"],
    "MAD": ["PUNCT"],
    "MID": ["PUNCT"],
    "PAD": ["PUNCT"],
}


def toSUC(ud17: str) -> List[str]:
    res = UD172SUC.get(ud17.upper())
    if res:
        return res
    raise SRUException(
        SRUDiagnostics.QUERY_SYNTAX_ERROR,
        message=f"unknown UD-17 PoS code in query: {ud17}",
    )


def fromSUC(suc: str) -> List[str]:
    pos = suc.split(".", 1)[0]
    res = SUC2UD17.get(pos.upper())
    if res:
        return res
    raise SRUException(
        SRUDiagnostics.CANNOT_PROCESS_QUERY_REASON_UNKNOWN,
        message=f"unknown PoS code from search engine: {pos}",
    )


# ---------------------------------------------------------------------------
