"""
SKOS conformance and convention checks.

Two categories are reported separately:

  SPEC        The six integrity conditions defined in the SKOS Reference
              (W3C Recommendation, 18 August 2009): S9, S13, S14, S27,
              S37, S46. A failure here means the data is genuinely
              inconsistent with the SKOS data model.

  CONVENTION  Usage conventions and editorial requirements. The SKOS
              Reference explicitly permits several of these patterns.
              A failure here is a quality problem, not a conformance
              problem.

Reference: https://www.w3.org/TR/skos-reference/
"""

from rdflib import Graph, RDF, RDFS
from rdflib.namespace import SKOS
from rdflib.collection import Collection
from collections import defaultdict

TTL = "decision-status.ttl"

g = Graph()
g.parse(TTL, format="turtle")

concepts = set(g.subjects(RDF.type, SKOS.Concept))
schemes = set(g.subjects(RDF.type, SKOS.ConceptScheme))
collections = set(g.subjects(RDF.type, SKOS.Collection)) | \
              set(g.subjects(RDF.type, SKOS.OrderedCollection))

spec_fail, conv_fail = [], []
def short(u): return str(u).split("#")[-1]

print(f"parsed {TTL}: {len(g)} triples, {len(concepts)} concepts, "
      f"{len(schemes)} scheme(s), {len(collections)} collection(s)\n")

# ---------------------------------------------------------------
# SPEC: integrity conditions
# ---------------------------------------------------------------

# S9  skos:ConceptScheme is disjoint with skos:Concept
for r in concepts & schemes:
    spec_fail.append(f"S9  {short(r)} is typed as both Concept and ConceptScheme")

# S13 prefLabel, altLabel and hiddenLabel are pairwise disjoint
for c in concepts:
    pref = {(str(l), l.language) for l in g.objects(c, SKOS.prefLabel)}
    alt = {(str(l), l.language) for l in g.objects(c, SKOS.altLabel)}
    hid = {(str(l), l.language) for l in g.objects(c, SKOS.hiddenLabel)}
    for a, b, name in ((pref, alt, "pref/alt"), (pref, hid, "pref/hidden"),
                       (alt, hid, "alt/hidden")):
        if a & b:
            spec_fail.append(f"S13 {short(c)} shares a label across {name}: {a & b}")

# S14 no more than one prefLabel per language tag
for c in concepts:
    by_lang = defaultdict(list)
    for l in g.objects(c, SKOS.prefLabel):
        by_lang[l.language].append(str(l))
    for lang, labels in by_lang.items():
        if len(labels) > 1:
            spec_fail.append(f"S14 {short(c)} has {len(labels)} prefLabels in @{lang}")

# S27 skos:related is disjoint with skos:broaderTransitive
broader = defaultdict(set)
for s, o in g.subject_objects(SKOS.broader):
    broader[s].add(o)
for s, o in g.subject_objects(SKOS.narrower):
    broader[o].add(s)

def ancestors(n, acc=None):
    acc = set() if acc is None else acc
    for p in broader.get(n, ()):
        if p not in acc:
            acc.add(p)
            ancestors(p, acc)
    return acc

for s, o in g.subject_objects(SKOS.related):
    if o in ancestors(s) or s in ancestors(o):
        spec_fail.append(f"S27 related({short(s)}, {short(o)}) clashes with the hierarchy")

# S37 skos:Collection is disjoint with skos:Concept and skos:ConceptScheme
for r in collections & (concepts | schemes):
    spec_fail.append(f"S37 {short(r)} is typed as both Collection and Concept/ConceptScheme")

# S46 skos:exactMatch is disjoint with skos:broadMatch and skos:relatedMatch
for s, o in g.subject_objects(SKOS.exactMatch):
    if (s, SKOS.broadMatch, o) in g or (s, SKOS.relatedMatch, o) in g:
        spec_fail.append(f"S46 exactMatch({short(s)}, {short(o)}) clashes with another mapping")

# Section 9.6.4: semantic relation properties have domain and range skos:Concept,
# so linking to or from a Collection makes the graph inconsistent.
for p in (SKOS.broader, SKOS.narrower, SKOS.related):
    for s, o in g.subject_objects(p):
        for node, role in ((s, "subject"), (o, "object")):
            if node in collections:
                spec_fail.append(
                    f"9.6.4 {short(node)} is a Collection used as {role} of {p.split('#')[-1]}")

# ---------------------------------------------------------------
# CONVENTION: usage and editorial checks
# ---------------------------------------------------------------

# Not a spec condition. Section 4.6.5 states no domain for skos:inScheme.
for c in concepts:
    if not set(g.objects(c, SKOS.inScheme)):
        conv_fail.append(f"{short(c)} is not attached to any concept scheme")

# Not a spec condition. Section 8.6.8 states that cycles are consistent
# with the SKOS data model; no condition requires irreflexivity.
def cyclic(n, path):
    if n in path:
        return True
    return any(cyclic(p, path | {n}) for p in broader.get(n, ()))

for c in concepts:
    if cyclic(c, frozenset()):
        conv_fail.append(f"cycle in the hierarchy involving {short(c)}")

# Not a spec condition. Section 4.6.3 states that a top concept with a
# broader concept is consistent; an application may reject it but need not.
for sch in schemes:
    for t in set(g.objects(sch, SKOS.hasTopConcept)) | set(g.subjects(SKOS.topConceptOf, sch)):
        if set(g.objects(t, SKOS.broader)):
            conv_fail.append(f"top concept {short(t)} also asserts skos:broader")

# Not a spec condition. Distinct prefLabels aid human readability only.
seen = defaultdict(list)
for c in concepts:
    for l in g.objects(c, SKOS.prefLabel):
        seen[(str(l), l.language)].append(short(c))
for k, v in seen.items():
    if len(v) > 1:
        conv_fail.append(f"prefLabel {k} is shared by {v}")

# Not a spec condition. Section 6.5.3 records the convention that notations
# are unique within a scheme.
notations = defaultdict(list)
for c in concepts:
    for n in g.objects(c, SKOS.notation):
        notations[str(n)].append(short(c))
for k, v in notations.items():
    if len(v) > 1:
        conv_fail.append(f"notation '{k}' is shared by {v}")

# Editorial requirement of this vocabulary, not of SKOS.
for c in sorted(concepts):
    if not set(g.objects(c, SKOS.definition)):
        conv_fail.append(f"{short(c)} has no skos:definition")
    if not set(g.objects(c, SKOS.scopeNote)):
        conv_fail.append(f"{short(c)} has no skos:scopeNote")

# S36 entailment check: every item of a memberList is also a member.
for coll in g.subjects(RDF.type, SKOS.OrderedCollection):
    for ml in g.objects(coll, SKOS.memberList):
        items = list(Collection(g, ml))
        print(f"ordered collection {short(coll)}: {[short(i) for i in items]}")
        for i in items:
            if i not in concepts:
                spec_fail.append(f"S32 collection member {short(i)} is not a skos:Concept")

print("\n--- hierarchy ---")
for c in sorted(concepts):
    bs = [short(b) for b in g.objects(c, SKOS.broader)]
    print(f"  {short(c):16} broader: {bs if bs else '(top concept)'}")

print("\n--- result ---")
print(f"SPEC       integrity conditions violated: {len(spec_fail)}")
for f in spec_fail:
    print("   x", f)
print(f"CONVENTION usage or editorial issues:     {len(conv_fail)}")
for f in conv_fail:
    print("   !", f)
if not spec_fail and not conv_fail:
    print("\nConsistent with the SKOS data model and with the stated conventions.")
