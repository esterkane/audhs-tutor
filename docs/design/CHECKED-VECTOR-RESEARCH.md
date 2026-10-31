# Checked vector research

Research authoring can calculate dot products and cosine similarities for a compact,
explicitly named set of vectors without a model request. This prevents guessed numeric
results and avoids generation delay for this calculation. It does not establish whether
an embedding model, distance metric or retrieval architecture is suitable.

Example source (notes or extracted text upload):

    Vectors:
    q=[1,0]
    A=[1,0]
    B=[10,1]

Editable research question:

    Compare dot product and cosine similarity for query `q` with candidates `A` and `B`.

German source header `Vektoren:` and question are also supported:

    Vergleiche Skalarprodukt und Kosinusähnlichkeit für Anfragevektor `q` mit Kandidaten `A` und `B`.

Every candidate receives both scores. Dot products use exact rational arithmetic;
cosines are approximate display values, with exact ranking keys including negative
values and ties. A zero vector has undefined cosine and is excluded from cosine ranking.
Malformed or oversized sources, differing dimensions, additional instructions, unresolved
questions and selected memories keep the normal tutor path. No source code is evaluated.

The existing research ownership, version checks, history limit, source binding, saved
exchange identity and recovery validation still apply. A calculation carries
`vector.dot-cosine.v1` and no model call ID; previous exchanges remain intact. The UI
labels saved calculation provenance as unverified, rather than certifying the uploaded
source. Learners can use, edit and save a calculated section through Write and Review.
The calculation does not create assessment or mastery evidence.

Tests cover exact arithmetic/order, zero vectors, bounded parsing, context deferral,
EN/DE presentation, discuss/draft persistence, reuse and earlier-history preservation.
The browser journey uses a synthetic text upload, optional persona, editable section,
save/reload and Review. Accepted lesson reading/resume is checked separately.
