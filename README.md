# Decision Status Vocabulary (SKOS)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21899592.svg)](https://doi.org/10.5281/zenodo.21899592)

A W3C SKOS controlled vocabulary describing the decision state of a conversational segment.

The vocabulary formalises the `decision_status` field of a retrieval-augmented generation experiment. Adding the full metadata layer to the retrieval index improved Precision@5 by 40% and Recall@5 by 61% against a baseline without metadata, over a test set of 10 questions with 28 relevance judgements, against a retrieval corpus of 47 semantic units consolidated from 284 segments across ten conversations.

## What this vocabulary is for

An ablation study over ten configurations separated the two mechanisms through which the field acts. Roughly 60% of the retrieval improvement came from using the status value to filter the candidate set at query time; roughly 40% came from prepending status and annotation text to the embedded document. The two mechanisms overlap by about 17%.

The vocabulary is therefore primarily a **query-side filtering vocabulary**, not a document enrichment vocabulary. Its value lies in supporting the question "which records are in this decision state", which is why scope notes state boundary rules rather than describing content. Implementations that only prepend the label to indexed text will realise the smaller share of the benefit.

## Files

| File | Purpose |
|---|---|
| `decision-status.ttl` | The vocabulary, serialised as RDF Turtle |
| `validate_skos.py` | Conformance checks, run with `rdflib` |

## Concepts

```
DecisionBearing (top concept, structural)
├── Exploring
├── Decided
├── Implemented
├── Abandoned
└── Superseded
Informational (top concept)
```

Ordered collection `DecisionProgression`: Exploring, Decided, Implemented.

## Design decisions

**The six original values sit on two axes.** `Informational` records whether a segment carries decision intent at all. The remaining five record the stage a decision has reached. A flat list is workable as a database field but produces an inconsistent hierarchy once modelled, so the two axes are separated: `DecisionBearing` groups the five stage values, and `Informational` stands beside it as a second top concept. No `NonDecisionBearing` parent was created, since a parent with one child carries no information.

`DecisionBearing` is structural and is not assigned during indexing. It is retained so that every decision-related segment can be retrieved in a single traversal along `skos:narrower`.

**Sequence is modelled as an ordered collection, not a hierarchy.** Exploring, Decided and Implemented form a progression, but sequence is not a relation of meaning, and asserting it through `skos:broader` would contradict the intent axis. `Abandoned` and `Superseded` are exits from the sequence rather than stages within it and are excluded from the collection.

**`Superseded` is assigned retrospectively.** Whether a segment is superseded depends on evidence outside that segment: a replacing decision must be identifiable elsewhere in the corpus. A segment therefore acquires the concept at annotation time rather than at the time it was written, and its status can change as the corpus grows. The other five concepts are decidable from the segment alone. Where a replacement cannot be identified, `Abandoned` is assigned instead, as the weaker claim.

**Every concept carries a scope note stating its boundary rule.** Definitions state what a concept means; scope notes state how to choose between concepts that compete for the same segment. The contested boundaries are Decided against Implemented, Exploring against Decided, Abandoned against Superseded, and Informational against Exploring. Each is resolved by an explicit rule rather than by annotator judgement.

## Conformance

`validate_skos.py` reports two categories separately, because the SKOS Reference distinguishes between them.

**Integrity conditions.** The specification defines exactly six: S9, S13, S14, S27, S37 and S46. A failure here means the data is genuinely inconsistent with the SKOS data model. All other numbered statements in the specification are class and property definitions that license inference, not constraints.

| Condition | Checked |
|---|---|
| S9 | `skos:ConceptScheme` is disjoint with `skos:Concept` |
| S13 | `skos:prefLabel`, `skos:altLabel` and `skos:hiddenLabel` are pairwise disjoint |
| S14 | No more than one `skos:prefLabel` per language tag |
| S27 | `skos:related` is disjoint with `skos:broaderTransitive` |
| S37 | `skos:Collection` is disjoint with `skos:Concept` and `skos:ConceptScheme` |
| S46 | `skos:exactMatch` is disjoint with `skos:broadMatch` and `skos:relatedMatch` |

Section 9.6.4 is also checked: the semantic relation properties have `skos:Concept` as domain and range, so using them on a collection makes the graph inconsistent.

**Usage conventions.** The following are permitted by the specification but are treated as defects in this vocabulary. Each is reported separately so that no conformance claim rests on them.

- Every concept is attached to a concept scheme. No domain is stated for `skos:inScheme` (section 4.6.5).
- No cycles in the hierarchy. Section 8.6.8 states that cycles are consistent with the data model, since no condition requires `skos:broaderTransitive` to be irreflexive.
- No top concept also asserts `skos:broader`. Section 4.6.3 states that such a graph is consistent and that an application may reject it but is not required to.
- No `skos:prefLabel` and no `skos:notation` is shared by two concepts. Section 6.5.3 records notation uniqueness as a convention.
- Every concept has both a definition and a scope note. This is an editorial requirement of this vocabulary, not of SKOS.

Both categories currently report zero failures.

```bash
pip install rdflib
python validate_skos.py
```

Established alternatives for this task are qSKOS and Skosify. The checks here are written out explicitly so that the conformance claim can be inspected rather than taken on trust.

## Known limitations

**The replacement relation is not expressible in SKOS.** `Superseded` states that a later decision replaced an earlier one, but SKOS has no vocabulary for asserting that one resource replaces another between instances. The relation is carried in a scope note only. Formalising it requires two time axes, the time a decision was taken and the time it ceased to hold, which is a task for an OWL layer.

**Permitted transitions are not constrained.** Nothing in the vocabulary prevents a segment moving from Implemented back to Exploring. SKOS has no mechanism for stating such constraints.

**One concept has no attested use.** No record in the source corpus carries `Superseded`. The concept is retained and flagged with a history note, but the vocabulary should not be described as fully evidenced by use.

**The retrieval corpus is small.** Forty-seven semantic units were consolidated from 284 segments across ten conversations, within a segmentation of 1,014 segments over 66 conversations. Ranking the top five from a pool of this size is an easier task than retrieval over the full corpus, and the absolute figures should not be read as generalising to it. Concept frequencies are correspondingly uneven: Exploring 17, Informational 16, Abandoned 9, Decided 3, Implemented 1, Superseded 0, with one record unassigned.

**The vocabulary does not model absence of assignment.** An unassigned record is a data quality state, not a decision state, and is handled by the application. One record of 47 in the source corpus is unassigned.

**Definitions and scope notes are English only.** Preferred labels are given in English and Traditional Chinese. Full bilingual documentation is outstanding.

**Namespace.** The namespace URI is currently under a domain that does not serve content negotiation, so concept URIs are stable identifiers but are not dereferenceable. Migration to a `w3id.org` permanent identifier is the intended next step.

## License

CC BY 4.0.
