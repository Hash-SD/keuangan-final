from __future__ import annotations
import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.metrics.data_freshness import compute_freshness
OUT=ROOT/'outputs/bab4_evidence_final/03_pengujian/432_kinerja_dashboard'
FIG=ROOT/'outputs/bab4_evidence_final/figures'

def main():
    records=[]
    for p in (ROOT/'outputs/reports/pipeline_runs').glob('freshness-*.json'):
        result=compute_freshness(json.loads(p.read_text(encoding='utf8')))
        if result.get('status')=='validated': records.append(result)
    frame=pd.DataFrame(records).sort_values('dashboard_verified_at')
    OUT.mkdir(parents=True,exist_ok=True); (FIG/'data').mkdir(parents=True,exist_ok=True)
    frame.to_csv(OUT/'freshness_runs.csv',index=False,encoding='utf-8-sig')
    frame.to_latex(OUT/'freshness_runs.tex',index=False,caption='Hasil pengukuran freshness lima run',label='tab:freshness-runs')
    stats=frame[['pipeline_latency_seconds','dashboard_serving_delay_seconds','freshness_seconds']].agg(['count','mean','median','min','max','std']).T.reset_index(names='metric')
    stats.to_csv(OUT/'freshness_statistics.csv',index=False,encoding='utf-8-sig')
    stats.to_latex(OUT/'freshness_statistics.tex',index=False,caption='Statistik freshness lima run',label='tab:freshness-statistik')
    (OUT/'freshness_validation.json').write_text(json.dumps({'status':'validated','run_count':len(frame),'dataset_session_ids':frame.dataset_session_id.unique().tolist(),'all_timeline_valid':True},ensure_ascii=False,indent=2),encoding='utf8')
    frame[['pipeline_run_id','freshness_seconds']].to_csv(FIG/'data/fig_432_freshness_per_run.csv',index=False,encoding='utf-8-sig')
    ax=frame.plot.bar(x='pipeline_run_id',y='freshness_seconds',legend=False,figsize=(10,5),color='#1f77b4'); ax.set_title('Freshness Data per Run'); ax.set_xlabel('Pipeline run ID'); ax.set_ylabel('Detik'); plt.xticks(rotation=25,ha='right'); plt.tight_layout(); plt.savefig(FIG/'fig_432_freshness_per_run.png',dpi=300); plt.savefig(FIG/'fig_432_freshness_per_run.pdf'); plt.close()
    print(json.dumps({'run_count':len(frame),'mean_freshness_seconds':frame.freshness_seconds.mean()},ensure_ascii=False))
if __name__=='__main__': main()
