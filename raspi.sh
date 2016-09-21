#!/usr/bin/env bash

push_start() {
  nohup ./armv7/rtmpPusher -c conf/cam.conf >trace.log 2>&1 &
}

push_stop() {
  ps -ef | egrep "rtmpPusher" | grep -v grep | awk '{print $8,$2}' | while read proc pid
  do
      kill -9 $pid
      echo "MediaServer $proc [$pid] stoped."
  done
}

start(){
  nohup raspivid -o - -t 0 -n -pf high -w 1280 -h 720 -fps 25 -b 2048000 -g 50 -rot 180 -ex antishake | \
     cvlc --network-caching=300 stream:///dev/stdin --sout '#rtp{sdp=rtsp://:8554/cam}' \
     :demux=h264 >/dev/null 2>&1 &
  nohup ./monitor.py -i enp0s25 -m u8300w >/dev/null 2>&1 &
  sleep 1
  push_start
  echo "MediaServer startup. playback: rtsp://10.0.0.1:8554/cam"
}

stop() {
  ps -ef | egrep "raspivid|vlc|monitor.py" | grep -v grep | awk '{print $8,$2}' | while read proc pid
  do
      kill -9 $pid
      echo "MediaServer $proc [$pid] stoped."
  done
  push_stop
}

if [ "$1" = "start" ];
then
  start
elif [ "$1" = "stop" ];
then
  stop
elif [ "$1" = "restart" ];
then
  stop
  sleep 1
  start
elif [ "$1" = "rtmp" ];
then
  if [ "$2" = "stop" ]; then
    push_stop
  else
    push_start
  fi
  exit 0
else
  echo "Usage: ./raspi.sh [start|stop|restart|rtmp <start|stop>]"
fi