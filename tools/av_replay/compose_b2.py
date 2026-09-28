"""Add the 2-D map inset and the state label to gz_raw_b2.mp4 -> ../../images/av_projects/p2_replan3d.mp4,
and cut the plain centre crop used as the home-page thumbnail -> ../../images/av_projects/teaser.mp4."""
import csv, os, subprocess, numpy as np, yaml
from PIL import Image, ImageDraw, ImageFont
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import LaserScan

A=os.environ['AV_P2'].rstrip('/')+'/'; P=os.environ.get('AV_P2_MAP',A+'maps/house_final')
OUT='../../images/av_projects/'; W0,H0,FPS=960,540,20
T_SPAWN,T_EVID,T_STOP,T_RESUME=143.18,147.10,147.48,148.54
meta=yaml.safe_load(open(P+'.yaml')); res=meta['resolution']; ox,oy=meta['origin'][:2]
pgm=np.array(Image.open(P+'.pgm')); H,W=pgm.shape; occ=pgm<100; free=pgm>250
def load(path,cols):
    rows=[l.strip().split(',') for l in open(path) if l.strip() and l[0] not in '#xr']
    return np.array([[float(r[c]) for c in cols] for r in rows])
route=load(A+'logs/m4v2_planned_path.csv',(0,1)); replan=load(A+'logs/m5v2/replanned_path.csv',(1,2))
tr=[r for r in csv.DictReader(l for l in open(A+'logs/m5v2/follower_trace.csv') if not l.startswith('#'))]
t=np.array([float(r['t_sim']) for r in tr]); x=np.array([float(r['x']) for r in tr]); y=np.array([float(r['y']) for r in tr])
yaw=np.unwrap(np.array([float(r['yaw']) for r in tr])); ft=np.load('frame_times_b2.npy'); BOX=(3.150,4.423)

rd=rosbag2_py.SequentialReader()
rd.open(rosbag2_py.StorageOptions(uri=A+'logs/bags/m5v2_official',storage_id=''),rosbag2_py.ConverterOptions('',''))
rd.set_filter(rosbag2_py.StorageFilter(topics=['/scan'])); scans=[]
while rd.has_next():
    _,data,_=rd.read_next(); m=deserialize_message(data,LaserScan)
    scans.append((m.header.stamp.sec+m.header.stamp.nanosec*1e-9,np.array(m.ranges,dtype=np.float32),m.angle_min,m.angle_increment))
st=np.array([s[0] for s in scans]); print('scans',len(scans),st[0],st[-1])

# inset: the part of the map around the route
x0m,x1m=route[:,0].min()-1.3,route[:,0].max()+1.3; y0m,y1m=route[:,1].min()-1.0,route[:,1].max()+0.9
c0,c1=int((x0m-ox)/res),int((x1m-ox)/res); r0,r1=int(H-1-(y1m-oy)/res),int(H-1-(y0m-oy)/res)
c0,c1,r0,r1=max(c0,0),min(c1,W),max(r0,0),min(r1,H); IW=280; sc=IW/(c1-c0); IH=int(round((r1-r0)*sc/2))*2
base=np.full((H,W,3),(226,229,235),np.uint8); base[free]=(255,255,255); base[occ]=(30,32,38)
base=Image.fromarray(np.ascontiguousarray(base[r0:r1,c0:c1])).resize((IW,IH),Image.LANCZOS)
def px(X,Y): return ((np.asarray(X)-ox)/res-c0)*sc, ((H-1-(np.asarray(Y)-oy)/res)-r0)*sc
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',19)
def label(tt):
    if tt<T_EVID: return 'Following the planned route',(40,48,66)
    if tt<T_RESUME: return 'Obstacle detected: stop and replan',(200,80,20)
    return 'Following the replanned path',(120,20,190)

src=subprocess.Popen(['ffmpeg','-v','error','-i','gz_raw_b2.mp4','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
enc=lambda path,size,crf: subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',size,'-r',str(FPS),'-i','-',
    '-c:v','libx264','-crf',str(crf),'-preset','slow','-pix_fmt','yuv420p','-movflags','+faststart','-an',path],stdin=subprocess.PIPE)
full=enc(OUT+'p2_replan3d.mp4',f'{W0}x{H0}',27); thumb=enc(OUT+'teaser.mp4','640x360',28)
for i,tf in enumerate(ft):
    raw=src.stdout.read(W0*H0*3)
    if len(raw)<W0*H0*3: break
    fr=Image.frombytes('RGB',(W0,H0),raw)
    thumb.stdin.write(fr.crop((160,90,800,450)).tobytes())
    im=base.copy(); d=ImageDraw.Draw(im)
    d.line(list(zip(*px(route[:,0],route[:,1]))),fill=(150,156,170),width=2)
    if tf>=T_STOP+0.3: d.line(list(zip(*px(replan[:,0],replan[:,1]))),fill=(150,40,215),width=2)
    k=np.searchsorted(t,tf)
    if k>1: d.line(list(zip(*px(x[:k:3],y[:k:3]))),fill=(40,120,255),width=2)
    j=min(np.searchsorted(st,tf),len(scans)-1); _,r,a0,da=scans[j]
    rx,ry,ryaw=np.interp(tf,t,x),np.interp(tf,t,y),np.interp(tf,t,yaw); ok=np.isfinite(r)&(r<3.5); ang=ryaw+a0+da*np.arange(len(r))
    for a,b in zip(*px(rx+r[ok]*np.cos(ang[ok]),ry+r[ok]*np.sin(ang[ok]))): d.point((a,b),fill=(230,60,50))
    if tf>=T_SPAWN:
        bx,by=px(BOX[0],BOX[1]); h=0.15/res*sc; d.rectangle((bx-h,by-h,bx+h,by+h),fill=(240,130,30),outline=(120,60,10))
    qx,qy=px(rx,ry); d.ellipse((qx-4,qy-4,qx+4,qy+4),fill=(20,90,230),outline=(255,255,255))
    fr.paste((255,255,255),(W0-IW-19,13,W0-13,IH+19)); fr.paste(im,(W0-IW-16,16))
    txt,col=label(tf); dd=ImageDraw.Draw(fr,'RGBA'); tw=dd.textlength(txt,font=font)
    dd.rounded_rectangle((16,H0-54,16+tw+28,H0-16),radius=8,fill=(255,255,255,225)); dd.text((30,H0-47),txt,font=font,fill=col)
    full.stdin.write(fr.tobytes())
for p in (full,thumb): p.stdin.close(); p.wait()
print('frames',i+1,'inset',IW,IH)
