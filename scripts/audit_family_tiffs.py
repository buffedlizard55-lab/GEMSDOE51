#!/usr/bin/env python3
"""Hash-checked inventory audit; no retired uniqueness checker dependency.

Fetch cache lives outside Git. A pass is bounded to the pinned inventory,
not every artifact ever published. Missing/mutated/unreadable references fail
coverage closed. Similarity thresholds stay unchanged, including dense maps.
"""
import argparse,concurrent.futures,hashlib,json,sys,subprocess,base64
from pathlib import Path
import numpy as np
import rasterio
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_public_uniqueness_audit import fetch_one, eligible,git_blob_sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate');a=ap.parse_args()
    inv=json.loads((ROOT/'registry/sibling_tiff_inventory.json').read_text())
    cache=ROOT/'data/raw/family_refs';cache.mkdir(exist_ok=True)
    records={}
    for repo in inv['repos']:
        for f in repo.get('tifs',[]):
            if not eligible(f['path']):continue
            records.setdefault(f['sha'],dict(repo=repo['repo'],branch=repo.get('branch') or 'main',path=f['path'],size=f['size'],git_blob_sha=f['sha']))
    def fetch(task):
        i,rec=task;dest=cache/f'{i:04d}-{rec["git_blob_sha"][:12]}.tif'
        if dest.exists() and git_blob_sha(dest.read_bytes())==rec['git_blob_sha']:
            return dict(ok=True,path=str(dest),record=rec)
        result=fetch_one((i,rec,str(cache)))
        if not result['ok']:
            # Immutable object lookup recovers older paths removed from main.
            proc=subprocess.run(['gh','api',f"repos/buffedlizard55-lab/{rec['repo']}/git/blobs/{rec['git_blob_sha']}"],capture_output=True)
            if proc.returncode==0:
                payload=json.loads(proc.stdout);data=base64.b64decode(payload['content'])
                if git_blob_sha(data)==rec['git_blob_sha'] and len(data)==rec['size']:
                    dest.write_bytes(data)
                    return dict(ok=True,path=str(dest),record=rec)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,enumerate(records.values())))
    failed=[dict(source=r['record'],error=r.get('error')) for r in results if not r['ok']]
    report=dict(scope='Committed 54-repository inventory: docs/downloads and submissions; unique Git blobs',expected=len(records),downloaded=sum(r['ok'] for r in results),failures=failed)
    if a.candidate:
        path=Path(a.candidate);sha=hashlib.sha256(path.read_bytes()).hexdigest()
        with rasterio.open(path) as src:values=src.read(1)
        support=np.isfinite(values)&(values>0);comparisons=[];invalid=[]
        for rec in results:
            if not rec['ok']:continue
            ref=Path(rec['path'])
            try:
                with rasterio.open(ref) as src:arr=src.read(1)
                if arr.shape!=values.shape:raise ValueError('different grid shape')
                other=np.isfinite(arr)&(arr>0)
                inter=int((support & other).sum());union=int((support | other).sum())
                comparisons.append(dict(source=rec['record'],sha256=hashlib.sha256(ref.read_bytes()).hexdigest(),jaccard=inter/max(union,1),containment=inter/max(int(support.sum()),1),identical_support=bool(np.array_equal(support,other))))
            except Exception as exc:invalid.append(dict(source=rec['record'],error=str(exc)))
        maxj=max((r['jaccard'] for r in comparisons),default=1);maxc=max((r['containment'] for r in comparisons),default=1)
        duplicate=any(r['sha256']==sha or r['identical_support'] for r in comparisons)
        coverage=not failed and not invalid and len(comparisons)==len(records)
        report.update(candidate=path.name,sha256=sha,comparisons=comparisons,invalid=invalid,coverage_complete=coverage,exact_duplicate=duplicate,max_jaccard=maxj,max_containment=maxc,
            verdict='PASS' if coverage and not duplicate and maxj<=.5 and maxc<=.6 else 'NOT_CLEARED',thresholds=dict(jaccard=.5,containment=.6))
    (ROOT/'evidence/p1_family_audit_20261007.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='comparisons'},indent=2))
if __name__=='__main__':main()
