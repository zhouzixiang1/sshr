# PDF Text Audit

This terminal audit extracts searchable text from the author and anonymous PDFs with Poppler and checks manuscript anchors, identity separation, and public-placeholder hygiene.

## Status counts

- pass: 2

| manuscript | status | pages | characters | words | missing anchors | forbidden hits | identity anchors | failures |
|---|---|---:|---:|---:|---|---|---|---|
| author | pass | 48 | 230744 | 20604 | none | none | author=True; anonymous=False | none |
| anonymous | pass | 48 | 229423 | 20433 | none | none | author=False; anonymous=True | none |
