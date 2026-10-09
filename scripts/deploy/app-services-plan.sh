#!/usr/bin/env bash
# app-services-plan.sh : deploy の Step 3c で、各 app サービスを作り直す必要があるかを判定して出力する。
# 段階1（観測のみ）。docker は読み取りコマンド（ps / inspect / image inspect / compose config --hash）だけを使う。
# 設計: docs/handoff/deploy-selective-recreate/design.md
#
# 使い方:
#   app-services-plan.sh --observe <svc>...
#   app-services-plan.sh --verify
# 終了コード: --observe は常に 0。--verify は正常 0・違反 1。
# set -e は使わない（途中で失敗しても判定の行を最後まで出すため）。
set -u

PROJECT="astro-webapp"

observe_one() {
  local svc="$1"
  local keeper_name="${PROJECT}-${svc}-1"
  local keeper_id="" keeper_label_hash=""
  local candidates line id name project service hash

  candidates="$(docker ps -a --filter "name=${PROJECT}-${svc}" --format '{{.ID}}|{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.service"}}|{{.Label "com.docker.compose.config-hash"}}' 2>/dev/null)"

  # 1回目: keeper を決める
  while IFS='|' read -r id name project service hash; do
    [ -z "${id}" ] && continue
    if [ "${name}" = "${keeper_name}" ] && [ "${project}" = "${PROJECT}" ] && [ "${service}" = "${svc}" ]; then
      keeper_id="${id}"
      keeper_label_hash="${hash}"
      break
    fi
  done <<EOF
${candidates}
EOF

  # 2回目: keeper 以外は消す対象として出す
  while IFS='|' read -r id name project service hash; do
    [ -z "${id}" ] && continue
    if [ -n "${keeper_id}" ] && [ "${id}" = "${keeper_id}" ]; then
      continue
    fi
    local reason
    if [ "${project}" != "${PROJECT}" ]; then
      reason="project"
    elif [ "${service}" != "${svc}" ]; then
      reason="service"
    elif [ -n "${keeper_id}" ]; then
      reason="duplicate"
    else
      reason="name"
    fi
    echo "PLAN svc=${svc} stale=${name} reason=${reason}"
  done <<EOF
${candidates}
EOF

  if [ -z "${keeper_id}" ]; then
    echo "PLAN svc=${svc} decision=recreate reason=no_container"
    return 0
  fi

  local expected_hash expected_image current_image
  expected_hash="$(docker compose config --hash "${svc}" 2>/dev/null | awk 'NR==1 {print $2}')"
  expected_image="$(docker image inspect -f '{{.Id}}' "${PROJECT}-${svc}" 2>/dev/null)"
  current_image="$(docker inspect -f '{{.Image}}' "${keeper_id}" 2>/dev/null)"

  if [ -z "${expected_hash}" ] || [ -z "${keeper_label_hash}" ] || [ -z "${expected_image}" ] || [ -z "${current_image}" ]; then
    echo "PLAN svc=${svc} decision=recreate reason=unknown"
  elif [ "${expected_hash}" != "${keeper_label_hash}" ]; then
    echo "PLAN svc=${svc} decision=recreate reason=hash_diff"
  elif [ "${expected_image}" != "${current_image}" ]; then
    echo "PLAN svc=${svc} decision=recreate reason=image_diff"
  else
    echo "PLAN svc=${svc} decision=keep reason=same"
  fi
  return 0
}

observe() {
  local svc
  for svc in "$@"; do
    observe_one "${svc}"
  done
  return 0
}

verify() {
  local listing
  listing="$(docker ps -a --format '{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.service"}}' 2>/dev/null)"
  local ng=0
  local name project service
  local seen=""

  # (b) 名前が astro-webapp- で始まるのに project が違うもの
  while IFS='|' read -r name project service; do
    [ -z "${name}" ] && continue
    case "${name}" in
      "${PROJECT}-"*)
        if [ "${project}" != "${PROJECT}" ]; then
          echo "VERIFY ng stale=${name}"
          ng=1
        fi
        ;;
    esac
  done <<EOF
${listing}
EOF

  # (a) project が astro-webapp のコンテナについて、service ごとの件数
  local svc count
  while IFS='|' read -r name project service; do
    [ -z "${name}" ] && continue
    [ "${project}" = "${PROJECT}" ] || continue
    case " ${seen} " in
      *" ${service} "*) continue ;;
    esac
    seen="${seen} ${service}"
    count="$(printf '%s\n' "${listing}" | awk -F'|' -v p="${PROJECT}" -v s="${service}" '$2==p && $3==s {n++} END {print n+0}')"
    if [ "${count}" != "1" ]; then
      echo "VERIFY ng svc=${service} count=${count}"
      ng=1
    fi
  done <<EOF
${listing}
EOF

  if [ "${ng}" = "0" ]; then
    echo "VERIFY ok"
    return 0
  fi
  return 1
}

mode="${1:-}"
case "${mode}" in
  --observe)
    shift
    observe "$@"
    exit 0
    ;;
  --verify)
    verify
    exit $?
    ;;
  *)
    echo "usage: $0 --observe <svc>... | --verify" >&2
    exit 2
    ;;
esac
