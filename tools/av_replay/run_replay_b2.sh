#!/bin/bash
# Headless Gazebo replay of the logged stop-and-replan run -> gz_raw_b2.mp4 (then compose_b2.py adds inset + label).
#   AV_P2=... AV_P2_MAP=... TB3_MODELS=.../turtlebot3_gazebo/models ./run_replay_b2.sh [NFRAMES]
cd "$(dirname "$0")"
source /opt/ros/jazzy/setup.bash
export GZ_PARTITION=homepage_replay GZ_SIM_RESOURCE_PATH="$TB3_MODELS"
python3 make_b2_world.py
gz sim -s --headless-rendering replay_b2.sdf > gz_replay_b2.log 2>&1 &
GZPID=$!
sleep 10
python3 replay_b2.py "$@"; RC=$?
pkill -9 -P $GZPID 2>/dev/null; kill -9 $GZPID 2>/dev/null
exit $RC
