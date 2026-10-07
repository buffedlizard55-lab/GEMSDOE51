#!/usr/bin/env python3
"""Official attribute verification and separate geometry-based Stage1 diagnostics.

Does not alter the frozen P1 stage1 mask. Outputs raw scalar residuals for the
source-defined dilation/shear/invariant, plus a five-way whole-trace holdout.
No absolute deficit is interpreted as a located fault.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from gems51.vector_budget import budget,summaries
from gems51.strain_budget import observed_tiles
from gems51.grid import GRID


def main():
    p=ROOT/'registry/official'
    local=pd.read_csv(ROOT/'data/raw/external/gdr_qfaults_traces.csv')
    official=pd.read_csv(p/'qfault_attributes.csv');selected=official.iloc[local.trace_id.to_numpy()]
    attrs=dict(rows=len(local),name_matches=int(np.sum(selected.NAME.to_numpy()==local.name.to_numpy())),
        rate_matches=int(np.sum(np.isclose(selected.SLIPRTNUM.to_numpy(),local.slip_rate.to_numpy()))),
        sense_matches=int(np.sum(selected.SLIPSENSE.fillna('').to_numpy()==local.slip_sense.fillna('').to_numpy())),
        units='mm/year; official field definitions lines39-43',component='unresolved; plane vs vertical are alternative assumptions')
    (ROOT/'evidence/official_attribute_audit_20261007.json').write_text(json.dumps(attrs,indent=2)+'\n')
    rows=pd.read_csv(p/'trace_segments_utm11.csv');fp=np.load(ROOT/'data/prepared/footprint.npy')
    obs={}
    with rasterio.open(ROOT/'data/raw/training_features.tif') as src:
        names=[d.split(' - ')[0] for d in src.descriptions]
        for label,name in [('dilatation','geod_dilaterate'),('shear','geod_shearrate'),('second_invariant','geod_2ndinv')]:
            a=src.read(names.index(name)+1).astype(float);a[a < -1e38]=np.nan
            obs[label]=observed_tiles(a,fp,100)
    results={}
    npz={}
    for convention in ('fault_plane','vertical'):
        tensor,meta=budget(rows,convention=convention);theory=summaries(*tensor)
        residuals={}
        for factor in (1e-9,1e-8):
            # Source writes '10E-9/yr'. Preserve both interpretations instead of
            # silently certifying a factor-of-ten choice.
            for label in obs:
                residual=obs[label]-theory[label]/factor
                npz[f'{convention}_{factor:g}_{label}_residual']=residual
                residuals[f'{factor:g}_{label}']=dict(median=float(np.nanmedian(residual)),positive_fraction=float(np.mean(residual[np.isfinite(residual)]>0)))
        results[convention]=dict(metadata=meta,raw_residuals=residuals)
    # Label-independent source geometry holds out whole record IDs, not pixels.
    ids=np.unique(rows.record_id);np.random.default_rng(51).shuffle(ids)
    masks=[]
    for split in range(5):
        held=ids[split::5];tensor,meta=budget(rows,excluded=held)
        inv=summaries(*tensor)['second_invariant']
        valid=np.isfinite(obs['second_invariant'])
        from scipy.stats import rankdata
        score=np.full(inv.shape,np.nan);score[valid]=(rankdata(obs['second_invariant'][valid])-rankdata(inv[valid]))/valid.sum()
        big=np.repeat(np.repeat(score,100,axis=0),100,axis=1)[:GRID.shape[0],:GRID.shape[1]]
        approved=fp & np.isfinite(big) & (big>=np.nanpercentile(big[fp],10))
        held_rows=rows[rows.record_id.isin(held)]
        geoms=[({'type':'LineString','coordinates':[(r.x0,r.y0),(r.x1,r.y1)]},1) for r in held_rows.itertuples(index=False)]
        truth=rasterize(geoms,out_shape=GRID.shape,transform=Affine(*GRID.transform),dtype='uint8')>0
        truth &= fp
        area=float(approved.sum()/fp.sum());recall=float((truth & approved).sum()/max(truth.sum(),1))
        masks.append(dict(split=split,held_trace_rows=len(held),truth_pixels=int(truth.sum()),area=area,recall=recall,lift=recall/area))
    np.savez_compressed(ROOT/'data/prepared/official_vector_residuals.npz',**npz)
    receipt=dict(source='https://gdr.openei.org/submissions/1391',formula_source='https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf',
        formula='E_ij = 0.5 sum L_k*u_k/(A*sin(dip_k))*(n_i*m_j+n_j*m_i)',
        input_segments=len(rows),input_trace_records=len(ids),results=results,
        holdout=dict(instrument='Five whole-official-trace splits; recall/lift only, not DTI; distinct from legacy P1 Stage1',splits=masks,mean_area=float(np.mean([x['area'] for x in masks])),mean_recall=float(np.mean([x['recall'] for x in masks])),mean_lift=float(np.mean([x['lift'] for x in masks]))),
        shear_definition='min(abs(eigenvalue1),abs(eigenvalue2)) if opposite signs, else0',
        role='Separate physical audit, NOT silently substituted into preregistered P1 screen',
        limitations=['Source unit notation 10E-9/yr is ambiguous: both 1e-9 and1e-8 scenarios retained.','Per-trace dip/rake/component missing; normal60deg, lateral90deg assumptions.','Scalar-summary subtraction is not subtraction of full observed tensors.','Tile size10km is bookkeeping, finer than geodetic resolving length; residual may be off-fault/aseismic/catalogue error.','Normal/LL/RL only; other senses omitted with segment count.','Bounds-qualified numeric rates are point assumptions, not precise measured values.'])
    (ROOT/'evidence/official_vector_budget_20261007.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
