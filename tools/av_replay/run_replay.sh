#!/bin/bash
# Headless Gazebo replay of the logged mapping run -> images/av_projects/p2_gazebo.mp4
# Needs: ROS 2 Jazzy + Gazebo Harmonic, the turtlebot3_gazebo models, and AV_P2 pointing at the course project-2
# folder (logs/video/mapping_trajectory.csv, logs/bags/archive/run3_drive, maps/house_final.*).
# Optional AV_P2_MAP=<path to house_final without extension> when the map is stored elsewhere.
#   AV_P2=... TB3_MODELS=.../turtlebot3_gazebo/models ./run_replay.sh 410 730 16
set -e
cd "$(dirname "$0")"
source /opt/ros/jazzy/setup.bash
export GZ_PARTITION=homepage_replay GZ_SIM_RESOURCE_PATH="$TB3_MODELS"
gz sim -s --headless-rendering replay.sdf > gz_replay.log 2>&1 &
GZPID=$!
sleep 10
python3 replay.py "$@" || true          # -> gz_raw.mp4, frame_times.npy
pkill -9 -P $GZPID 2>/dev/null || true; kill -9 $GZPID 2>/dev/null || true
python3 inset.py                        # -> inset.mp4
ffmpeg -v error -y -i gz_raw.mp4 -i inset.mp4 -filter_complex "[1:v]pad=iw+6:ih+6:3:3:color=white[in];[0:v][in]overlay=W-w-16:16,fps=20"   -c:v libx264 -crf 27 -preset slow -pix_fmt yuv420p -movflags +faststart -an ../../images/av_projects/p2_gazebo.mp4
