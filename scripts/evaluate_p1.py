#!/usr/bin/env python3
"""One preregistered P1 experiment; checkpointed outputs, no slot submission."""
from __future__ import annotations
import json, time, sys, hashlib, platform
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from gems51.detector import Stack, fit_detector, predict_grid
from gems51.profile_features import profile_features
from gems51.holdout import make_folds
from gems51.grid import GRID
from scripts.evaluate_hk1_holdout import _load_stage1_inputs, _stage1_q10_approved, _score_field

P = ROOT/'data/prepared'
OUT = ROOT/'evidence/p1_holdout_20261007.json'
FROZEN = .285340602656319

def main():
    import sklearn, scipy
    if OUT.exists() and "promoted" in json.loads(OUT.read_text()):
        raise SystemExit("P1 is a completed fixed experiment; do not rerun to shop for a passing result")
    t = time.time()
    fp, cat = np.load(P/'footprint.npy'), np.load(P/'catalogue.npy')
    stack = Stack(P)
    names = json.loads((P/'extras_static_names.json').read_text())
    mm = np.memmap(P/'extras_static.dat', dtype='float32', mode='r', shape=(len(names), *GRID.shape))
    with rasterio.open(ROOT/'data/raw/training_features.tif') as src:
        desc = [n.split(' - ')[0] for n in src.descriptions]
        elevation = src.read(desc.index('det_elev')+1).astype(np.float32)
        elevation[elevation < -1e38] = np.nan
    profile = profile_features(elevation, fp)
    del elevation
    for name, arr in profile.items(): np.save(P/f'{name}.npy', arr)
    extras = {arm:[mm[i] for i,n in enumerate(names) if 'facecoh' in n or (arm!='hd' and n.startswith('hh_'))] for arm in ('hd','hh','p1')}
    extras['p1'] += list(profile.values())
    df, assignments, obs = _load_stage1_inputs(fp, cat)
    rows=[]
    for fold in make_folds(fp,cat,buffer_px=12,n_rows=3,n_cols=3,min_truth=500):
        fields={}
        for arm in extras:
            path = P/f'p1screen_{arm}_fold{fold.index}.npy'
            # No stale cross-experiment cache: this prefix is exclusive to P1.
            if path.exists():
                field=np.load(path)
            else:
                X,y=stack.sample(fold.train_pos, fold.train_neg_pool, 250000, np.random.default_rng(1000+fold.index), extra=extras[arm])
                model=fit_detector(X,y,seed=fold.index,max_iter=250)
                del X,y
                field=predict_grid(model,stack,fp & fold.block,extra=extras[arm])
                np.save(path,field)
            fields[arm]=np.nan_to_num(field,nan=0)
            print('field',fold.index,arm,'seconds',round(time.time()-t),flush=True)
        approved,s1=_stage1_q10_approved(fp,fold,df,assignments,obs)
        allowed=fp & fold.block & (ndi.distance_transform_edt(~fold.known)>2)
        k=round(3.47*fold.n_truth)
        base=(fields['hd']+fields['hh'])*.5
        candidate=(fields['hd']+fields['p1'])*.5
        scores={
            'baseline_ungated':_score_field(base,allowed,k,fold,fp),
            'baseline_gated':_score_field(base,allowed & approved,k,fold,fp),
            'candidate_gated':_score_field(candidate,allowed & approved,k,fold,fp),
        }
        rows.append(dict(fold=fold.index,n_truth=fold.n_truth,requested_dots=k,stage1=s1,scores=scores))
        print(json.dumps(rows[-1]),flush=True)
        OUT.write_text(json.dumps(dict(status='INCOMPLETE_NOT_FOR_SUBMISSION',rows=rows),indent=2)+'\n')
    bv=np.array([r['scores']['baseline_ungated']['dti'] for r in rows])
    bg=np.array([r['scores']['baseline_gated']['dti'] for r in rows])
    cv=np.array([r['scores']['candidate_gated']['dti'] for r in rows])
    area=np.array([r['stage1']['approved_area_share'] for r in rows])
    gates=dict(six_folds=len(rows)==6,baseline_reproduced=abs(bv.mean()-FROZEN)<=1e-5,
        beats_frozen=cv.mean()>FROZEN,beats_paired=cv.mean()>bg.mean(),positive_folds=int((cv>bg).sum())>=4,
        stage1_broad=bool((area>=2/3).all()),confinement=all(r['scores']['candidate_gated']['dots']==r['scores']['candidate_gated']['emitted_inside_allowed']==r['requested_dots'] for r in rows))
    gates={k:bool(v) for k,v in gates.items()}
    receipt=dict(candidate='P1 odd/even topographic normal profiles', status='LOCAL_PROXY_PROMOTED' if all(gates.values()) else 'RESEARCH_ONLY_NOT_PROMOTED',
        promoted=all(gates.values()),gates=gates,rows=rows,
        summary=dict(baseline_ungated=float(bv.mean()),baseline_gated=float(bg.mean()),candidate_gated=float(cv.mean()),paired_delta=float((cv-bg).mean()),positive_folds=int((cv>bg).sum()),frozen_best=FROZEN,baseline_drift=float(bv.mean()-FROZEN)),
        protocol='knowledge/next-candidates-20261007.md',stage1_holdout='evidence/stage1_q10_trace_holdout_20261007.json',
        versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__),
        runtime_seconds=time.time()-t,slot_used=False,limitations=['Visible-catalogue proxy, not hidden expert truth.','Repeated use of folds is selection-biased; no independent lockbox.','Stage1 approximate centroid rate assignment; source units reviewed separately; do not infer physical residual from ranks.'])
    OUT.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt['summary'],indent=2),flush=True)

if __name__=='__main__':main()
