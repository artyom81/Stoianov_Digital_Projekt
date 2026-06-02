import re

def _strip_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v

def cql_to_lucene(cql: str) -> str:
    if not cql:
        return ""
    q = cql.strip()
    m = re.fullmatch(r'(?:cql\.serverChoice|cql\.anywhere)\s*=\s*"([^"]+)"', q, flags=re.I)
    if m:
        return f'"{m.group(1)}"'
    m = re.fullmatch(r'(?:dc\.title|title)\s*=\s*"([^"]+)"', q, flags=re.I)
    if m:
        return f'title:"{m.group(1)}"'
    field_matches = re.findall(r'([a-zA-Z0-9_.]+)\s*=\s*"([^"]+)"', q)
    if field_matches:
        parts = []
        for field, value in field_matches:
            f = field.lower()
            if f in {"cql.serverchoice", "cql.anywhere"}:
                parts.append(f'"{value}"')
            elif f in {"title", "dc.title"}:
                parts.append(f'title:"{value}"')
            elif f in {"magazine", "form", "language"}:
                parts.append(f'{f}:"{value}"')
            else:
                parts.append(f'"{value}"')

        if re.search(r"\bOR\b", q, flags=re.I):
            return " OR ".join(parts)
        if re.search(r"\bNOT\b", q, flags=re.I):
            if len(parts) == 2:
                return f"{parts[0]} NOT {parts[1]}"
        return " AND ".join(parts)

    # nackte Phrase
    if q.startswith('"') and q.endswith('"'):
        return q

    q = re.sub(r"\bAND\b", "AND", q, flags=re.I)
    q = re.sub(r"\bOR\b", "OR", q, flags=re.I)
    q = re.sub(r"\bNOT\b", "NOT", q, flags=re.I)

    return q