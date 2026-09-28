"""Replay the logged stop-and-replan run (B2) in headless Gazebo and record the camera topic -> gz_raw_b2.mp4.
Run after the server is up with replay_b2.sdf (see run_replay_b2.sh)."""
import csv, math, os, sys, time, threading, subprocess, numpy as np
from gz.transport13 import Node
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.world_control_pb2 import WorldControl
from gz.msgs10.image_pb2 import Image

FPS=20; FAST,SLOW=14.0,1.5; SLOW_WIN=(141.5,151.0)          # playback speed; slow around the event
T_SPAWN,T_STOP=143.18,147.48                                  # box spawn, zero-velocity stop (metrics.txt / replan_events.csv)
NMAX=int(sys.argv[1]) if len(sys.argv)>1 else 10**9
A=os.environ['AV_P2'].rstrip('/')+'/'
rows=[r for r in csv.DictReader(l for l in open(A+'logs/m5v2/follower_trace.csv') if not l.startswith('#'))]
t=np.array([float(r['t_sim']) for r in rows]); x=np.array([float(r['x']) for r in rows])-2.0142
y=np.array([float(r['y']) for r in rows])-0.5; yaw=np.unwrap(np.array([float(r['yaw']) for r in rows]))
ft=[]; tt=t[0]
while tt<t[-1]+8:                                             # hold a little at the goal
    ft.append(tt); tt+=(SLOW if SLOW_WIN[0]<=tt<SLOW_WIN[1] else FAST)/FPS
ft=np.array(ft)[:NMAX]
fx,fy,fyaw=np.interp(ft,t,x),np.interp(ft,t,y),np.interp(ft,t,yaw)
k=int(0.6*FPS); w=np.hanning(2*k+1); w/=w.sum()
cx=np.convolve(np.pad(fx,k,mode='edge'),w,mode='valid'); cy=np.convolve(np.pad(fy,k,mode='edge'),w,mode='valid')
OFF=(0.0,-0.15,9.0); PITCH=math.atan2(9.0,0.15); CYAW=math.pi/2

def quat(r,p,yw):
    cr,sr,cp,sp,cy_,sy=math.cos(r/2),math.sin(r/2),math.cos(p/2),math.sin(p/2),math.cos(yw/2),math.sin(yw/2)
    return (sr*cp*cy_-cr*sp*sy, cr*sp*cy_+sr*cp*sy, cr*cp*sy-sr*sp*cy_, cr*cp*cy_+sr*sp*sy)
node=Node(); latest={'stamp':-1,'data':None}; lock=threading.Lock()
def on_img(msg):
    with lock: latest.update(stamp=msg.header.stamp.sec+msg.header.stamp.nsec*1e-9,data=msg.data)
assert node.subscribe(Image,'/world/replay/model/cam/link/l/sensor/c/image',on_img)
def set_pose(name,px,py,pz,r=0,p=0,yw=0):
    m=Pose(); m.name=name; m.position.x,m.position.y,m.position.z=px,py,pz
    m.orientation.x,m.orientation.y,m.orientation.z,m.orientation.w=quat(r,p,yw)
    ok,rep=node.request('/world/replay/set_pose',m,Pose,Boolean,2000); assert ok and rep.data,name
def step_and_grab():
    with lock: before=latest['stamp']
    for attempt in range(6):
        m=WorldControl(); m.pause=True; m.multi_step=100
        ok,rep=node.request('/world/replay/control',m,WorldControl,Boolean,2000); assert ok
        t_end=time.time()+1.5
        while time.time()<t_end:
            with lock:
                if latest['stamp']>before+1e-6: return latest['data']
            time.sleep(0.005)
    raise RuntimeError('no camera frame')

ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','960x540','-r',str(FPS),'-i','-',
    '-c:v','libx264','-crf','16','-preset','fast','-pix_fmt','yuv420p','gz_raw_b2.mp4'],stdin=subprocess.PIPE)
time.sleep(1.0); box_up=path_up=False
for i in range(len(ft)):
    set_pose('burger',fx[i],fy[i],0.01,0,0,fyaw[i]); set_pose('marker',fx[i],fy[i],0.004)
    set_pose('cam',cx[i]+OFF[0],cy[i]+OFF[1],OFF[2],0,PITCH,CYAW)
    if not box_up and ft[i]>=T_SPAWN: set_pose('box',1.1358,3.923,0.2); box_up=True
    if not path_up and ft[i]>=T_STOP+0.3: set_pose('replan',0,0,0.004); path_up=True
    step_and_grab()                      # poses are applied during a step ...
    ff.stdin.write(step_and_grab())      # ... so the second render shows them
    if i%50==0: print('frame',i,'/',len(ft),flush=True)
ff.stdin.close(); ff.wait(); np.save('frame_times_b2.npy',ft); print('done',len(ft))
