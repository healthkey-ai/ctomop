# Cytogenetic marker summary coding

`cytogenetic_markers` retains canonical selection tokens for PatientRecord and
matching. It is a local multi-marker summary, not a genetic variant status.
Its OMOP projection uses Observation concept **0** (no matching concept) and
the stable source value `mm-cytogenetic-markers`. No standard concept is claimed.
Choices without a verified equivalent remain uncoded; curator-provided mappings
are retained unless they match the specific erroneous seed associations.

The earlier seed incorrectly associated marker choices with LOINC test and
metadata identifiers. For example, [81249-5](https://loinc.org/81249-5) is a
genomic reference sequence coding system, not 1q gain/amplification.
[69548-6](https://loinc.org/69548-6) is genetic variant assessment with
present/absent/no-call/indeterminate answers, not a comma-separated marker list.
Neither changing an OMOP domain nor loading more vocabulary fixes that mismatch.

Issue #1204 reconciles the separate `genetic_mutations.*` component domains,
including the legitimate `genetic_mutations.status` use of 69548-6. This summary
does not reuse or modify those mappings. The repair of prior development data
is restricted to the summary field/choice associations and Observation rows
with source `mm-cytogenetic-markers` and the previously incorrect 69548-6 code.

The merge migration joins the cytogenetic rename branch to current dev, while
also repairing development databases that already applied the earlier seed.
