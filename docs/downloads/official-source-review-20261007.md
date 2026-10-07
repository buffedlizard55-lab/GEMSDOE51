# Source review, equations, and corrected assumptions

## Checked source table (2026-10-07)

| Claim | Evidence | Status / qualification |
|---|---|---|
| Target is surface fault pixels, not direct vent discovery | [Organizer problem/metric/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Fetched both chunks this session. Faults can be geothermal indicators; no vent labels or discovery claims. |
| Slip attributes actually exist in the shapefile | [Official GDR v2 ZIP](https://gdr.openei.org/files/1391/qfaults_ingenious_nad83conus117_2023-06-27.zip) | Downloaded on GitHub Actions; archive SHA256 and original field definitions retained in registry/official. DBF has SLIPRT2023 and SLIPRTNUM. |
| Numeric slip-rate units | Same ZIP, field-definition lines39–43 | SLIPRT2023 is mm/year; SLIPRTNUM is its numeric portion. All1,126 local rows match original DBF names/rates/senses. Component and individual dips NOT specified. |
| Actual trace geometry | Same ZIP; scripts/extract_official_segments.py | 84,331 projected vertex segments from1,126 regional records, EPSG32611. Local vector budget clips each segment at tile edges; no nearest-centroid transfer. |
| Geodetic scalar definitions | [Official geodetic ZIP](https://gdr.openei.org/files/1391/geodetics_INGENIOUS_regional_data.zip), retained README | II=√(e1²+e2²); dilation=e1+e2; shear=min(abs(e1),abs(e2)) when eigenvalues have opposite signs, otherwise0. Source writes units “10E-9/yr”; both1e-9 and1e-8 scenarios preserved because notation is ambiguous. |
| Tensor summation formula | [Kreemer et al.(2000), Eq3](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf) | PDF checked this session. Equation below, not an invented conversion. |
| Joint geologic/geodetic modeling precedent, three methods | [USGS UCERF3 AppendixC](https://pubs.usgs.gov/of/2013/1165/pdf/ofr2013-1165_appendixC.pdf) | Search-retrieved official excerpt describes NeoKinema, average block model and buried dislocation approach. Precedent is not validation of this project's residual heuristic. [1](https://pubs.usgs.gov/of/2013/1165/pdf/ofr2013-1165_appendixC.pdf) |
| Off-fault strain is physically plausible | [Zeng & Shen2016, USGS publication record](https://pubs.usgs.gov/publication/70160311) | The paper separately estimates off-fault moment release; a strain residual need not mean an unmapped localized fault. [2](https://pubs.usgs.gov/publication/70160311) |
| H33-2-B2 score attribution | [GEMSDOE32 owner page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | Owner describes37,654 dots after200m catalogue pruning, but still UNSCORED. User reports0.2778; exact score-to-file not organizer verified. |
| Submission rules/narrative | [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | PDF available; September2026 edition. Do not claim every clause re-reviewed this session. Existing site preserves AI disclosure instructions. |

Official source downloads were executed on the user's GitHub Actions runner because this sandbox's shell cannot directly reach GDR. The initial artifact download redirected to a blocked Azure host, so the workflow committed only small extracted metadata/attributes/geometry to the session branch. Bulk ASCII data was immediately removed from the final tree and kept in ignored data/raw. Archive receipts plus workflow source provide reproducible provenance. Dataset attribution: INGENIOUS Great Basin Regional Dataset Compilation, DOI10.15121/1881483, CC-BY4.0 as stated on [GDR1391](https://gdr.openei.org/submissions/1391).

## Exact formula, units, assumptions

\[
\dot M_{ij}^{(k)}=\mu L_k W_k\dot u_k(n_i m_j+n_j m_i),\quad
\dot\epsilon_{ij}=\frac{1}{2\mu V}\sum_k\dot M_{ij}^{(k)}
=\frac12\sum_k\frac{L_k\dot u_k}{A\sin\delta_k}(n_i m_j+n_j m_i).
\]

Here W=H/sinδ and V=AH; μ and common seismogenic thickness H cancel. L is the **clipped in-tile trace length in meters**; u is meters/year; A is the complete10km×10km tile area. n and m are3D unit normal/slip vectors; use their horizontal tensor components. N faults assume dip60° and pure normal slip: ε_nn=L·u_plane·cosδ/A. With a vertical-rate interpretation, replace u_plane by u_vertical/sinδ. RL/LL assume vertical faults and opposite signed strike-normal shear, ε_sn=±L·u/(2A). Unsupported senses are omitted and counted, not silently assigned normal slip.

For each tile, sum tensor components **before** deriving eigenvalues. Calculate source-matched dilation, shear and II from those eigenvalues. Subtract corresponding scalar observations and modeled scalar rates under each documented unit/component scenario. This is scalar-summary subtraction, **not** subtraction of an observed tensor whose orientation has not been supplied. The output is diagnostic tile residuals, not a fine-scale fault location. Negative residuals are retained in the audit, not arbitrarily zeroed.

The independent vector Stage1 audit holds out complete trace records in five fixed splits and reports area, held-trace recall and lift. That audit is not silently substituted into the frozen P1 pipeline, whose legacy centroid/raster q10 gate must remain unchanged for a fair benchmark comparison. A new source-corrected production mask needs a new paired Stage2 test.

## Corrected irregularities

1. Earlier statements that slip units were unknown are superseded: mm/year is now source-verified. Slip **component**, dip and rake assumptions remain unresolved.
2. Earlier statements that the geodetic fields satisfy no scalar identity used the wrong shear definition. Under the source convention, II²=D²+2S(|D|+S). On81,011 finite nearest-neighbor samples, median relative discrepancy is0.00686, p99=0.19355; interpolation or other processing can break identity. It is unjustified to infer independent original smoothing from the failed alternative formulas alone.
3. “DTI=TP/(0.2·M+0.8·|G|)” is not generally true for raw point count M. Exact: DTI=TP/[0.2(TP+FP)+0.8|G|]. The metric module implements this correctly; some older explanatory prose did not. One point may cover several truth pixels.
4. Broad-mask lift≤1.5 is a necessary operational non-dominance test, not causal proof. Report footprint breadth, confinement, point occupancy, actual gated/ungated support overlap, and separately weak Stage1 versus stronger Stage2 holdouts.
5. Official format says outside data bounds null/NaN; the reported portal error motivates an all-finite zero-outside diagnostic. Numeric safety is measured, but portal acceptance and interpretation of bounds versus footprint remain unverified. Do not certify an upload based on local range checks alone.
6. Repeated tuning on the same six known-fault folds creates selection bias. Frozen threshold protection is helpful but does not create an independent discovery lockbox.

## Why H33 may work, and what beating the reported scores requires

The triangulated-distance metric gives each truth pixel the maximum nearby confidence-weighted credit, while predictions with little nearby truth accumulate false-positive cost. Thinning redundant broad predictions can therefore improve the weighted credit-to-cost tradeoff; pruning near known catalogue geometry can concentrate the budget on eligible territory. This is a mathematical explanation of a **plausible mechanism**, not a causal decomposition of the user-reported0.2778 result.

Neither0.2778 nor the stated0.3195 is a target this local holdout can certify beating. Catalogue folds reward the kinds of structures already mapped; unknown expert faults have a different sampling process. The best route is more accurately located weak/covered traces supported by independent physical evidence, tested with spatial separation and eventually an untouched geography/trace-family lockbox. A broad geothermal-habitat raster is not a substitute. P1 tests one narrowly specified morphology discriminator; if it fails, retain the negative evidence and do not spend a slot.
