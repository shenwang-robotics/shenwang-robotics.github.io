"""Write replay_b2.sdf: the mapping-replay world plus the planned route, the replanned path and the obstacle box.
Route and path are flat ribbons on the floor; path and box start below the ground and are raised by replay_b2.py."""
import os, math, numpy as np
A=os.environ['AV_P2'].rstrip('/')+'/'
SPAWN=(-2.0142,-0.5)                                   # map frame = world - spawn
def load(path,cols):
    rows=[l.strip().split(',') for l in open(path) if l.strip() and l[0] not in '#xr']
    return np.array([[float(r[c]) for c in cols] for r in rows])
def ribbon(name,pts,rgb,z,width=0.05):
    keep=[pts[0]]
    for p in pts[1:]:
        if np.hypot(*(p-keep[-1]))>=0.08: keep.append(p)
    keep.append(pts[-1]); out=[f'<model name="{name}"><static>true</static><pose>0 0 {z} 0 0 0</pose><link name="l">']
    for i,(a,b) in enumerate(zip(keep[:-1],keep[1:])):
        L=float(np.hypot(*(b-a)));
        if L<1e-6: continue
        m=(a+b)/2; yaw=math.atan2(b[1]-a[1],b[0]-a[0]); c=' '.join(f'{v:.3f}' for v in rgb)
        out.append(f'<visual name="s{i}"><cast_shadows>false</cast_shadows><pose>{m[0]+SPAWN[0]:.4f} {m[1]+SPAWN[1]:.4f} 0 0 0 {yaw:.4f}</pose>'
                   f'<geometry><box><size>{L+width*0.6:.4f} {width} 0.002</size></box></geometry>'
                   f'<material><ambient>{c} 1</ambient><diffuse>{c} 1</diffuse><specular>0 0 0 1</specular></material></visual>')
    out.append('</link></model>'); return '\n'.join(out)
route=load(A+'logs/m4v2_planned_path.csv',(0,1)); replan=load(A+'logs/m5v2/replanned_path.csv',(1,2))
box=('<model name="box"><static>true</static><pose>1.1358 3.923 -5 0 0 0</pose><link name="l"><visual name="v">'
     '<geometry><box><size>0.30 0.30 0.40</size></box></geometry>'
     '<material><ambient>0.95 0.5 0.1 1</ambient><diffuse>0.95 0.5 0.1 1</diffuse></material></visual></link></model>')
s=open('replay.sdf').read(); tag='<model name="cam">'; assert s.count(tag)==1
extra='\n'.join([ribbon('route',route,(0.16,0.20,0.30),0.003), ribbon('replan',replan,(0.50,0.05,0.80),-5.0,0.07), box])
open('replay_b2.sdf','w').write(s.replace(tag,extra+'\n    '+tag))
print('route pts',len(route),'replan pts',len(replan))
