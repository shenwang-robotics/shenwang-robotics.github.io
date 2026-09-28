"""Map inset: area covered so far by the recorded /scan messages, drawn on the final SLAM map."""
import csv, math, os, numpy as np, yaml, subprocess
from PIL import Image, ImageDraw
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import LaserScan

A=os.environ['AV_P2'].rstrip('/')+'/'  # course project-2 folder (logs/, maps/)
P=os.environ.get('AV_P2_MAP',A+'maps/house_final')  # path of the final map without extension
meta=yaml.safe_load(open(P+'.yaml')); res=meta['resolution']; ox,oy=meta['origin'][:2]
pgm=np.array(Image.open(P+'.pgm')); H,W=pgm.shape
occ=pgm<100; free=pgm>250

rows=[r for r in csv.DictReader(open(A+'logs/video/mapping_trajectory.csv')) if r['phase']=='main_drive']
tn=np.array([int(r['odom_header_ns']) for r in rows],dtype=np.float64)/1e9; t_first=tn[0]; tn-=t_first
mx=np.array([float(r['map_x_m']) for r in rows]); my=np.array([float(r['map_y_m']) for r in rows])
myaw=np.unwrap(np.array([float(r['map_yaw_rad']) for r in rows]))
ft=np.load('frame_times.npy')

# scans from the bag (header stamp = sim time, same clock as the odometry header in the CSV)
rd=rosbag2_py.SequentialReader()
rd.open(rosbag2_py.StorageOptions(uri=A+'logs/bags/archive/run3_drive',storage_id=''),rosbag2_py.ConverterOptions('',''))
rd.set_filter(rosbag2_py.StorageFilter(topics=['/scan']))
scans=[]; last=-1
while rd.has_next():
    _,data,_=rd.read_next(); m=deserialize_message(data,LaserScan)
    ts=m.header.stamp.sec+m.header.stamp.nanosec*1e-9-t_first
    if ts>ft[-1]+1: break
    if ts-last<0.5: continue
    last=ts; scans.append((ts,np.array(m.ranges,dtype=np.float32),m.angle_min,m.angle_increment,m.range_max))
print('scans',len(scans),'first',scans[0][0],'last',scans[-1][0])

def to_px(x,y): return (x-ox)/res, H-1-(y-oy)/res
seen=np.zeros((H,W),bool); steps=np.arange(0.0,3.5,res*0.8,dtype=np.float32)
def add(scan):
    ts,r,a0,da,rmax=scan
    px,py,pyaw=np.interp(ts,tn,mx),np.interp(ts,tn,my),np.interp(ts,tn,myaw)
    ang=pyaw+a0+da*np.arange(len(r)); rr=np.where(np.isfinite(r),np.minimum(r,3.5),3.5)
    d=np.minimum(steps[None,:],rr[:,None]+res)          # walk each ray up to its hit
    X=px+d*np.cos(ang)[:,None]; Y=py+d*np.sin(ang)[:,None]
    c,rw=to_px(X,Y); c=np.clip(c.astype(int),0,W-1); rw=np.clip(rw.astype(int),0,H-1); seen[rw,c]=True
    hit=np.isfinite(r)&(r<3.5)
    return px+r[hit]*np.cos(ang[hit]), py+r[hit]*np.sin(ang[hit])

# crop of the map shown in the inset: bounding box of known cells, padded
ys,xs=np.where(occ|free); x0,x1,y0,y1=max(xs.min()-6,0),min(xs.max()+6,W),max(ys.min()-6,0),min(ys.max()+6,H)
cw,ch=x1-x0,y1-y0; IW=300; IH=int(round(IW*ch/cw/2))*2; sc=IW/cw
ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{IW}x{IH}','-r','20','-i','-',
   '-c:v','libx264','-crf','14','-pix_fmt','yuv420p','inset.mp4'],stdin=subprocess.PIPE)
open('inset_size.txt','w').write(f'{IW} {IH}')
si=0; hits=(np.array([]),np.array([]))
for i,tf in enumerate(ft):
    while si<len(scans) and scans[si][0]<=tf: hits=add(scans[si]); si+=1
    img=np.full((H,W,3),(226,229,235),np.uint8)
    img[seen&free]=(255,255,255); img[seen&occ]=(30,32,38)
    im=Image.fromarray(img[y0:y1,x0:x1]).resize((IW,IH),Image.LANCZOS); d=ImageDraw.Draw(im)
    k=np.searchsorted(tn,tf); sel=slice(0,k,25)
    tx,ty=to_px(mx[sel],my[sel]); pts=list(zip((tx-x0)*sc,(ty-y0)*sc))
    if len(pts)>1: d.line(pts,fill=(40,120,255),width=2)
    hx,hy=to_px(*hits)
    for a,b in zip((hx-x0)*sc,(hy-y0)*sc): d.point((a,b),fill=(230,60,50))
    rx,ry=to_px(np.interp(tf,tn,mx),np.interp(tf,tn,my)); rx,ry=(rx-x0)*sc,(ry-y0)*sc
    d.ellipse((rx-4,ry-4,rx+4,ry+4),fill=(20,90,230),outline=(255,255,255))
    ff.stdin.write(np.asarray(im.convert('RGB')).tobytes())
ff.stdin.close(); ff.wait(); im.save('inset_last.png'); print('inset',IW,IH)
