#!/usr/bin/env bash
# 使い方: count.sh <volume> <ラベル> ; volume 全体(/opt/data 以下の全ファイル)で MARK7735・SYS7735 を含む「行数」を数える（grep -a -c）。使い捨て容器・ネット無し・hermes 利用者で読む
V=$1; L=$2
D=nousresearch/hermes-agent@sha256:ef0650d523ee1b5ab32c779acabc446d9936869a9932591553688a62bcf0c42f
docker run --rm --network none --entrypoint sh -u 10000:10000 -v $V:/opt/data $D -c '
n=$(find /opt/data -type f | wc -l)
tm=0; ts=0
for f in $(find /opt/data -type f); do
  a=$(grep -a -c MARK7735 "$f" 2>/dev/null); b=$(grep -a -c SYS7735 "$f" 2>/dev/null)
  a=${a:-0}; b=${b:-0}
  [ "$a" != 0 ] || [ "$b" != 0 ] && echo "  $f MARK=$a SYS=$b"
  tm=$((tm+a)); ts=$((ts+b))
done
echo "合計 ファイル数=$n MARK7735行=$tm SYS7735行=$ts"' 2>&1 | sed "s#^#[$L] #"
