"""Replay a logged TurtleBot3 trajectory in headless Gazebo and record the camera topic.
Usage (after run_replay.sh has started the server): replay.py T0 T1 SPEED [NFRAMES]"""
import csv, math, os, sys, time, threading, subprocess, numpy as np
from gz.transport13 import Node
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.world_control_pb2 import WorldControl
from gz.msgs10.image_pb2 import Image

T0, T1, SPEED, FPS = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), 20
NMAX = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
A=os.path.join(os.environ['AV_P2'],'logs/video/mapping_trajectory.csv')  # AV_P2 = course project-2 folder (logs/, maps/)
rows=[r for r in csv.DictReader(open(A)) if r['phase']=='main_drive']
t=np.array([int(r['odom_header_ns']) for r in rows],dtype=np.float64)/1e9; t-=t[0]
x=np.array([float(r['map_x_m']) for r in rows])-2.0142   # map frame = world - spawn
y=np.array([float(r['map_y_m']) for r in rows])-0.5
yaw=np.unwrap(np.array([float(r['map_yaw_rad']) for r in rows]))
ft=np.arange(T0,T1,SPEED/FPS)[:NMAX]
fx,fy,fyaw=np.interp(ft,t,x),np.interp(ft,t,y),np.interp(ft,t,yaw)
# camera target: robot position smoothed symmetrically (+-0.6 s of video time)
k=int(0.6*FPS); w=np.hanning(2*k+1); w/=w.sum()
cx=np.convolve(np.pad(fx,k,mode='edge'),w,mode='valid'); cy=np.convolve(np.pad(fy,k,mode='edge'),w,mode='valid')
OFF=(0.0,-0.15,9.0); PITCH=math.atan2(9.0,0.15); CYAW=math.pi/2

def quat(r,p,yw):
    cr,sr,cp,sp,cy_,sy=math.cos(r/2),math.sin(r/2),math.cos(p/2),math.sin(p/2),math.cos(yw/2),math.sin(yw/2)
    return (sr*cp*cy_-cr*sp*sy, cr*sp*cy_+sr*cp*sy, cr*cp*sy-sr*sp*cy_, cr*cp*cy_+sr*sp*sy)

node=Node(); latest={'stamp':-1,'data':None,'w':0,'h':0}; lock=threading.Lock()
def on_img(msg):
    with lock:
        latest.update(stamp=msg.header.stamp.sec+msg.header.stamp.nsec*1e-9,data=msg.data,w=msg.width,h=msg.height)
assert node.subscribe(Image,'/world/replay/model/cam/link/l/sensor/c/image',on_img)

def set_pose(name,px,py,pz,r,p,yw):
    m=Pose(); m.name=name; m.position.x,m.position.y,m.position.z=px,py,pz
    m.orientation.x,m.orientation.y,m.orientation.z,m.orientation.w=quat(r,p,yw)
    ok,rep=node.request('/world/replay/set_pose',m,Pose,Boolean,2000); assert ok and rep.data,name
def step(n):
    m=WorldControl(); m.pause=True; m.multi_step=n
    ok,rep=node.request('/world/replay/control',m,WorldControl,Boolean,2000); assert ok

ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','960x540','-r',str(FPS),'-i','-',
    '-c:v','libx264','-crf','16','-preset','fast','-pix_fmt','yuv420p','gz_raw.mp4'],stdin=subprocess.PIPE)
time.sleep(1.0)
for i in range(len(ft)):
    set_pose('burger',fx[i],fy[i],0.01,0,0,fyaw[i])
    set_pose('marker',fx[i],fy[i],0.004,0,0,0)
    set_pose('cam',cx[i]+OFF[0],cy[i]+OFF[1],OFF[2],0,PITCH,CYAW)
    with lock: before=latest['stamp']
    got=False
    for attempt in range(6):
        step(100)
        t_end=time.time()+1.5
        while time.time()<t_end:
            with lock:
                if latest['stamp']>before+1e-6: got=True; data=latest['data']; break
            time.sleep(0.005)
        if got: break
    assert got, f'no frame at {i}'
    # poses are applied during the step, so render once more with the pose already in place
    with lock: before=latest['stamp']
    step(100); t_end=time.time()+1.5
    while time.time()<t_end:
        with lock:
            if latest['stamp']>before+1e-6: data=latest['data']; break
        time.sleep(0.005)
    ff.stdin.write(data)
    if i%50==0: print('frame',i,'/',len(ft),flush=True)
ff.stdin.close(); ff.wait()
np.save('frame_times.npy',ft)
print('done',len(ft))
