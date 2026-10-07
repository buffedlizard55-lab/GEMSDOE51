import numpy as np
import pandas as pd
from gems51.vector_budget import clip_segment, segment_tensor, summaries, budget

def test_clipping():
    assert clip_segment(-5,5,15,5,0,0,10,10)==(0,5,10,5)
    assert clip_segment(-5,15,15,15,0,0,10,10) is None
    assert clip_segment(1,1,1,1,0,0,10,10) is None

def test_tensor_and_reversal():
    # 10km E-W fault at 1mm/yr in a 100km² tile, normal at60°.
    n=segment_tensor(0,0,10000,0,1,'N')
    np.testing.assert_allclose(n,[0,5e-8,0],atol=1e-20)
    np.testing.assert_allclose(n,segment_tensor(10000,0,0,0,1,'N'))
    a=segment_tensor(0,0,10000,0,1,'RL');b=segment_tensor(0,0,10000,0,1,'LL')
    np.testing.assert_allclose(a,-b);assert a[2]==5e-8
    summary=summaries(*a); assert summary['dilatation']==0
    np.testing.assert_allclose(summary['shear'],5e-8)

def test_tile_length_conserved_on_boundary():
    df=pd.DataFrame([[0,243350,4498550,263350,4498550,1.,'1','N']],columns=['record_id','x0','y0','x1','y1','slip_mm_yr','slip_text','sense'])
    e,meta=budget(df)
    assert meta['used_length_m']==20000
    assert np.count_nonzero(e)==2
    empty,meta=budget(df,excluded=[0]);assert not empty.any()
