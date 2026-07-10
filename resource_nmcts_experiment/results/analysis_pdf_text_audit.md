# PDF Text Audit

This terminal audit extracts searchable text from the author and anonymous PDFs with Poppler and checks manuscript anchors, identity separation, and public-placeholder hygiene.

## Status counts

- pass: 2

| manuscript | status | pages | characters | words | missing anchors | forbidden hits | identity anchors | failures |
|---|---|---:|---:|---:|---|---|---|---|
| author | pass | 59 | 289561 | 25644 | none | none | author=True; anonymous=False | none |
| anonymous | pass | 59 | 288241 | 25473 | none | none | author=False; anonymous=True | none |
