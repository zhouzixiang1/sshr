# PDF Text Audit

This terminal audit extracts searchable text from the author and anonymous PDFs with Poppler and checks manuscript anchors, identity separation, and public-placeholder hygiene.

## Status counts

- pass: 2

| manuscript | status | pages | characters | words | missing anchors | forbidden hits | identity anchors | failures |
|---|---|---:|---:|---:|---|---|---|---|
| author | pass | 39 | 193097 | 16770 | none | none | author=True; anonymous=False | none |
| anonymous | pass | 39 | 191780 | 16599 | none | none | author=False; anonymous=True | none |
