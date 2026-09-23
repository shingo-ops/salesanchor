#!/bin/bash
# ワイヤレスデバッグの接続先を探して再接続する。
# Wi-Fi が切れて復帰すると Android はワイヤレスデバッグを新しいポートで起動し直すため、
# 保存済みの接続先では復帰できない（2026-09-23: 40359 -> 44861 に変わり約6時間停止した）。
# mDNS（adb mdns services）は同端末で何も返さず、getprop は proot から権限が無いため、
# ローカルのポート走査で探す（実測: 30000-55000 の走査で約64秒・候補2個）。
# 候補の検証に `adb shell` を使うと offline 相手で数分待たされるため、devices の状態で判定する。
set -u
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
DIR=/root/line-auto-export
FROM=${SCAN_FROM:-30000}
TO=${SCAN_TO:-55000}

candidates=$(timeout 180 python3 - "$FROM" "$TO" <<'PY'
import socket,sys
from concurrent.futures import ThreadPoolExecutor
lo,hi=int(sys.argv[1]),int(sys.argv[2])
def probe(p):
    s=socket.socket(); s.settimeout(0.15)
    try:
        s.connect(('127.0.0.1',p)); return p
    except Exception: return None
    finally: s.close()
with ThreadPoolExecutor(max_workers=600) as ex:
    print('\n'.join(str(r) for r in ex.map(probe,range(lo,hi+1)) if r))
PY
)
[ -z "$candidates" ] && exit 1

for p in $candidates; do
  timeout 15 adb connect "127.0.0.1:$p" >/dev/null 2>&1
  state=$(timeout 10 adb devices 2>/dev/null | awk -v d="127.0.0.1:$p" '$1==d{print $2}')
  if [ "$state" = "device" ]; then
    echo "127.0.0.1:$p" > "$DIR/endpoint"
    echo "127.0.0.1:$p"
    exit 0
  fi
  timeout 10 adb disconnect "127.0.0.1:$p" >/dev/null 2>&1
done
exit 1
