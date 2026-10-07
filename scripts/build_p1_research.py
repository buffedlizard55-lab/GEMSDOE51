#!/usr/bin/env python3
"""Train a genuinely new P1 field, emit a diagnostic TIFF, never use a slot.

A completed failed holdout is still useful as a DOWNLOADABLE RESEARCH artifact;
its existence is explicitly not authorization to upload. Never copy a prior
raster into the prediction path. Reference rasters enter only after emission.
"""
import sys,json,time,hashlib,zipfile
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from gems51.detector import Stack
from gems51.submission import write_tif
from gems51.uniqueness import run_gate
from scripts.build_submission_hh_blend import selected_extras,fit_full_field,stage1_prior,load_observed
from scripts.build_submission import prior_rasters,require_family_reference_coverage
from scripts.evaluate_hk1_holdout import _ste_emit
from gems51 import strain_budget as sb


def main():
    hold=json.loads((ROOT/'evidence/p1_holdout_20261007.json').read_text())
    if len(hold.get('rows',[]))!=6 or 'promoted' not in hold:raise SystemExit('completed six-fold holdout required')
    if (ROOT/'evidence/p1_artifact_20261007.json').exists():raise SystemExit('P1 artifact already exists; do not relabel/rebuild it')
    p=ROOT/'data/prepared';fp=np.load(p/'footprint.npy');cat=np.load(p/'catalogue.npy');stack=Stack(p)
    hd,_=selected_extras(stack,[],fp,'H_D');hh,_=selected_extras(stack,[],fp,'H_H')
    hh += [np.load(p/f'{n}.npy') for n in ('p1_step_fraction','p1_near_far_agreement','p1_even_fraction')]
    fields=[]
    for arm,extras,seed in [('hd',hd,17),('p1',hh,19)]:
        print('fitting full',arm,flush=True)
        field=fit_full_field(stack,fp,cat,extras,seed,250000,250)
        fields.append(np.nan_to_num(field,nan=0));np.save(p/f'p1final_{arm}.npy',field)
    field=(fields[0]+fields[1])*.5
    s1=stage1_prior(cat,fp,sb.load_slip_rates(ROOT/'data/raw'),load_observed(),q=10)
    approved=s1['approved'];allowed=fp & approved & (ndi.distance_transform_edt(~cat)>2)
    ys,xs=_ste_emit(field,allowed,44069)
    if len(ys)!=44069:raise SystemExit('dot budget not reached')
    support=np.zeros(fp.shape,bool);support[ys,xs]=True
    if np.any(support & ~approved):raise SystemExit('confinement failed')
    uy,ux=_ste_emit(field,fp & (ndi.distance_transform_edt(~cat)>2),44069)
    ungated=np.zeros(fp.shape,bool);ungated[uy,ux]=True
    ablation=dict(gated_vs_ungated_support_jaccard=float((support & ungated).sum()/max((support | ungated).sum(),1)),
                  fraction_gated_points_also_ungated=float((support & ungated).sum()/support.sum()))
    priors=prior_rasters();ref_count=require_family_reference_coverage(priors)
    digest=hashlib.sha256(support.tobytes()).hexdigest()[:12]
    base=f'gemsdoe51-p1-odd-even-q10-{digest}-zeros'
    target=ROOT/'docs/downloads'/f'{base}.tif'
    check=write_tif(target,support.astype(np.float32),fp,outside=0,nodata=None)
    if not check['checks']['all_cells_finite_in_range'] or not check['checks']['format_valid']:raise SystemExit('format failed')
    gate=run_gate(target,priors,support,fp,approved)
    if gate.byte_duplicate_of:target.unlink();raise SystemExit('duplicate bytes rejected')
    # Broadness is only a necessary test of non-dominance; also report actual
    # within-tile sparsity. It is not causal attribution to a prior.
    s1check=gate.stage1_dominance
    s1check['emitted_outside_approved']=int(np.count_nonzero(support & ~approved))
    s1check['approved_pixel_occupancy']=float(support.sum()/approved.sum())
    s1check['interpretation']='Pass means broad gate, not proof of causal independence; zero soft Stage1 weight.'
    zip_path=target.with_suffix('.zip')
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:z.write(target,target.name)
    record=dict(id='P1_ODD_EVEN_Q10',role='RESEARCH_ONLY',status='NOT_FOR_SUBMISSION',file=target.name,zip=zip_path.name,
        submission_name=f'GEMSDOE51-P1-Q10-{digest}',note='RESEARCH ONLY: odd/even scarp-profile HGB + HD blend; q10 broad strain gate; STE L9; 44069 dots; blocked holdout not cleared. Do not upload.',
        sha256=check['sha256'],bytes=check['bytes'],format=check,holdout=hold['summary'],holdout_promoted=hold['promoted'],
        uniqueness=gate.as_dict(),reference_count=ref_count,stage1=s1check,stage1_ablation=ablation,
        model=dict(seeds=[17,19],negatives=250000,max_iter=250,blend=[.5,.5],planning_truth_count=12700,planning_truth_count_is_not_observed=True),
        source='new fitted feature-based predictions; no prior TIFF used as model input',
        decision='Research download only; no slot authorized. P1 promotion and scientific/provenance checks must all pass before any future recommendation.',
        limitations=['Local format validity is not portal acceptance.','Uniqueness scoped to available reference rasters, not all possible submissions.','Source geometry audit is separate; this artifact uses preregistered legacy q10 mask for exact experiment consistency.'])
    record['checks_file']=f'{base}-checks.json'
    for dest in (ROOT/'evidence/p1_artifact_20261007.json',target.parent/record['checks_file']):dest.write_text(json.dumps(record,indent=2)+'\n')
    path=ROOT/'data/submission_manifest.json';manifest=json.loads(path.read_text());manifest['research_only_artifacts'].append(record)
    manifest['latest_experiment']=record
    path.write_text(json.dumps(manifest,indent=1)+'\n')
    print(json.dumps(record,indent=2),flush=True)
if __name__=='__main__':main()
