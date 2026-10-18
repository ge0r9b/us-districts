# summarize raw/b<build>-<tag>-<vp>.json into a markdown table row set; usage: table.py <build> <sha> <tag>
import json,sys,glob,os,statistics as st
B,SHA,TAG=sys.argv[1:4]
VPS=["390x844","375x667","320x568","ipad820x1180"]
def L(R,k):
  v=[x for x in R['lat'].get(k,[]) if x is not None]
  return f"{round(st.median(v))} / {round(max(v))}" if v else "-"
def first(R,k):
  v=R['lat'].get(k,[]); return f"{round(v[0])}" if v and v[0] is not None else "-"
rows=[]
for vp in VPS:
  f=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","raw",f"b{B}-{TAG}-{vp}.json")
  try: R=json.load(open(f))[vp]
  except Exception: continue
  t=R['timing']; bi=R['bytes_initial']; bp=R['bytes_pa_session']; pan=R['pan']
  rows.append(f"| {B} ({SHA}) | {vp} | {bi['app']['enc']/1e6:.2f} / {bi['app']['dec']/1e6:.2f} | {bp['app']['enc']/1e6:.2f} / {bp['app']['dec']/1e6:.2f} | {t['dcl']} | {t['load']} | {t['first_map']} | {t['longest_task']} | {L(R,'all_states')} (cold {first(R,'all_states')}) | {L(R,'ushouse_pick')} (cold {first(R,'ushouse_pick')}) | {L(R,'chart_line')} | {L(R,'drill_PA')} | {L(R,'back')} | {L(R,'time_step')} | {pan.get('fps')} fps, p95 {pan.get('p95_ms')}, max {pan.get('max_ms')}, dropped {pan.get('dropped')}/{pan.get('frames')} |")
print("\n".join(rows))
