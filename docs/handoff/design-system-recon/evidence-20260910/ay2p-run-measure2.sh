#!/bin/bash
# usage: run-measure.sh <LABEL> <PORT>
W=/Users/tanizawashingo/worktrees/salesanchor/release-list-search-inputs
L=$1; P=$2
D=/tmp/CC報告ファイル/ssot-ay2p
cd $W/frontend
export VITE_FIREBASE_API_KEY=dummy VITE_FIREBASE_AUTH_DOMAIN=dummy.example VITE_FIREBASE_PROJECT_ID=dummy VITE_FIREBASE_APP_ID=dummy VITE_FIREBASE_STORAGE_BUCKET=dummy VITE_FIREBASE_MESSAGING_SENDER_ID=1 VITE_GCP_PROJECT_ID=dummy
NODE_ENV=development npx vite build --mode development > $D/vitebuild-$L.log 2>&1; echo "build exit $?"
(npx vite preview --port $P --strictPort > $D/preview-$L.log 2>&1 &)
for i in $(seq 1 30); do curl -s -o /dev/null http://localhost:$P/ && break; /bin/sleep 1; done
node $D/ay2p-measure2.cjs $L $W http://localhost:$P; echo "measure exit $?"
lsof -ti tcp:$P | xargs -r kill
