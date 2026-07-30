from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/bab4_evidence_final'

def main():
    statuses=pd.DataFrame([
        {'subsection':'4.1.1','status':'READY','evidence':'profil workbook/sheet'},
        {'subsection':'4.1.2','status':'READY','evidence':'inventaris aturan dan komponen'},
        {'subsection':'4.1.3','status':'READY','evidence':'dictionary, lineage, trace samples'},
        {'subsection':'4.2.1','status':'READY','evidence':'Airflow DAG/run/task evidence'},
        {'subsection':'4.2.2','status':'READY WITH LIMITATIONS','evidence':'artefak Bronze/Silver lokal'},
        {'subsection':'4.2.3','status':'READY WITH LIMITATIONS','evidence':'Gold lokal; storage/query konservatif'},
        {'subsection':'4.3.1','status':'READY','evidence':'rekonsiliasi 2023–2025 dengan selisih Rp0'},
        {'subsection':'4.3.2','status':'READY','evidence':'lima manifest freshness terkorolasi upload–Gold–PostgreSQL–Superset'},
        {'subsection':'4.3.3','status':'READY WITH LIMITATIONS','evidence':'UAT portal satu pengguna utama; alignment 5 vs 7 indikator'},
    ])
    fallback=OUT/'section_evidence_map_final_updated.csv'
    statuses.to_csv(fallback,index=False,encoding='utf-8-sig')
    try:
        statuses.to_csv(OUT/'section_evidence_map_final.csv',index=False,encoding='utf-8-sig')
        target='canonical'
    except PermissionError:
        target='fallback_due_to_excel_lock'
    headers=list(statuses.columns)
    lines=['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']
    lines.extend('| '+' | '.join(str(row[column]) for column in headers)+' |' for _,row in statuses.iterrows())
    report='# Final Validation Report\n\n'+'\n'.join(lines)+'\n\nStatus keseluruhan: **READY WITH LIMITATIONS**.\n'
    (OUT/'final_validation_report_updated.md').write_text(report,encoding='utf8')
    print(target)
if __name__=='__main__': main()
