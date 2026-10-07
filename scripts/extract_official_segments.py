#!/usr/bin/env python3
"""Extract official trace vertices in competition bounding box, not label-derived.

Runs on GitHub Actions where GDR is reachable; the small CSV is auditable and
kept in Git. The official archive itself stays an Actions artifact, not in Git.
"""
import csv
import io
from pathlib import Path
import zipfile
import shapefile
from pyproj import CRS, Transformer

with zipfile.ZipFile('official/qfaults.zip') as z:
    stem = next(n[:-4] for n in z.namelist() if n.lower().endswith('.shp'))
    r = shapefile.Reader(shp=io.BytesIO(z.read(stem+'.shp')), shx=io.BytesIO(z.read(stem+'.shx')), dbf=io.BytesIO(z.read(stem+'.dbf')))
    crs = CRS.from_wkt(z.read(stem+'.prj').decode())
    tr = Transformer.from_crs(crs,32611,always_xy=True)
    out=Path('registry/official/trace_segments_utm11.csv')
    with out.open('w') as f:
        w=csv.writer(f);w.writerow(['record_id','x0','y0','x1','y1','slip_mm_yr','slip_text','sense'])
        for rid, item in enumerate(r.iterShapeRecords()):
            rec=item.record.as_dict(); pts=item.shape.points
            ends=list(item.shape.parts)+[len(pts)]
            for start,end in zip(ends[:-1],ends[1:]):
                x,y=tr.transform(*zip(*pts[start:end]))
                for i in range(len(x)-1):
                    if max(x[i:i+2]) <243350 or min(x[i:i+2])>572550 or max(y[i:i+2])<4135550 or min(y[i:i+2])>4508550:continue
                    w.writerow([rid,round(x[i],3),round(y[i],3),round(x[i+1],3),round(y[i+1],3),rec['SLIPRTNUM'],rec['SLIPRT2023'],rec['SLIPSENSE']])
