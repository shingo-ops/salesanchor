# LINE export UI trial: home shortcut -> Menu -> 設定 -> トーク履歴を送信 -> share sheet (Termux shown), then close.
# Prints only step names, timings and window class names; never message content.
X=/data/local/tmp/flow-ui.xml
N=${1:-10}

now() { cut -d' ' -f1 /proc/uptime; }
focus() { dumpsys window | grep mCurrentFocus | sed -E 's/.* ([^ ]+)\}.*/\1/'; }
dump() {
  i=0
  while [ $i -lt 5 ]; do
    uiautomator dump $X 2>/dev/null | grep -q 'dumped to' && return 0
    i=$((i+1)); sleep 1
  done
  return 1
}
# tap_by <regex matched against one node line>; returns 1 if not found
tap_by() {
  dump || return 2
  b=$(tr '>' '\n' < $X | grep -E "$1" | head -1 | sed -E 's/.*bounds="\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]".*/\1 \2 \3 \4/')
  rm -f $X
  [ -z "$b" ] && return 1
  set -- $b
  input tap $(( ($1+$3)/2 )) $(( ($2+$4)/2 ))
}
# find_scroll <regex>: look first, then scroll a little at a time (max 4) until found
find_scroll() {
  k=0
  while [ $k -le 4 ]; do
    sleep 1
    tap_by "$1" && return 0
    input swipe 540 1700 540 1100 800
    k=$((k+1))
  done
  echo "  $(date +%T) not found: $1"
  return 1
}
wait_focus() {
  echo "  $(date +%T) wait $1 (now $(focus))"
  i=0
  while [ $i -lt 20 ]; do
    focus | grep -q "$1" && return 0
    i=$((i+1)); sleep 0.5
  done
  return 1
}

ok=0
r=1
while [ $r -le $N ]; do
  t0=$(now); step=""
  input keyevent KEYCODE_HOME; sleep 1.5
  if ! tap_by 'text="WeGo売ります・BOX'; then step=shortcut
  elif ! wait_focus ChatHistoryActivity; then step=open_chat
  elif ! tap_by 'content-desc="Menu ボタン"'; then step=menu_button
  elif ! wait_focus ChatMenuActivity; then step=open_menu
  else
    if ! find_scroll 'text="設定"'; then step=settings_item
    elif ! wait_focus ChatSettingActivity; then step=open_settings
    else
      if ! find_scroll 'text="トーク履歴を送信"'; then step=export_item
      elif ! wait_focus ChooserActivity; then step=share_sheet
      else
        sleep 1
        dump && tr '>' '\n' < $X | grep -q 'text="Termux"' || step=termux_target
        rm -f $X
      fi
    fi
  fi
  t1=$(now)
  echo "  t0=$t0 t1=$t1 final=$(focus)"
  if [ -z "$step" ]; then ok=$((ok+1)); echo "run $r OK sec=$(echo "$t1 $t0" | awk '{printf "%.1f",$1-$2}')"
  else echo "run $r FAIL at=$step focus=$(focus) sec=$(echo "$t1 $t0" | awk '{printf "%.1f",$1-$2}')"; fi
  [ "$2" = keep ] && { echo "result ok=$ok/$N (share sheet kept)"; exit 0; }
  # close share sheet / leave LINE screens
  input keyevent KEYCODE_BACK; sleep 0.5
  for k in 1 2 3; do
    focus | grep -qE 'ChatSettingActivity|ChatMenuActivity|ChooserActivity' && { input keyevent KEYCODE_BACK; sleep 0.7; }
  done
  r=$((r+1))
done
echo "result ok=$ok/$N"
input keyevent KEYCODE_HOME
