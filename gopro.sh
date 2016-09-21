#!/usr/bin/env bash
start(){
  nohup ./monitor.py -i enp0s25 -m e3276 >/dev/null 2>&1 &
  sleep 1
  nohup ./rtmpPusher -c conf/encoder.conf >trace.log 2>&1 &
  echo "Process startup ... "
}

stop() {
  ps w | egrep "rtmpPusher|monitor.py" | grep -v grep | awk '{print $5,$1}' | while read proc pid
  do
      kill -9 $pid
      echo "Process $proc [$pid] stoped."
  done
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
else
  echo "Usage: ./gopro.sh [start|stop|restart]"
fi