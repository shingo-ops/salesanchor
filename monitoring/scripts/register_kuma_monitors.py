#!/usr/bin/env python3
"""正本 yml（monitoring/uptime-kuma-monitors.yml）の見張りを Uptime Kuma に足す。

- 本番に同じ名前があれば「有り」、無くて register: true なら「足す」、
  無くて register: false なら「欠落」。
- --apply が無ければ判定表を出すだけで何も変更しない。
- 何度実行しても同じ結果（同名の見張りは作らない）。消す動きは持たない。
- 認証ファイルの中身（ユーザー:パスワード）は出力・例外文面に出さない。

依存: uptime-kuma-api（monitoring/scripts/requirements-kuma.txt）と PyYAML。
"""
import argparse
import sys

import yaml


def read_cred(path):
    with open(path, encoding="utf-8") as f:
        line = f.readline().rstrip("\r\n")
    if ":" not in line:
        raise ValueError("cred format")
    user, password = line.split(":", 1)
    return user, password


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yml", required=True)
    ap.add_argument("--url", required=True, help="Kuma の宛先")
    ap.add_argument("--cred-file", required=True)
    ap.add_argument("--apply", action="store_true", help="足す。無ければ確認のみ")
    args = ap.parse_args()

    with open(args.yml, encoding="utf-8") as f:
        wanted = yaml.safe_load(f)["monitors"]

    try:
        user, password = read_cred(args.cred_file)
    except Exception as e:
        print(f"認証ファイルを読めません: {type(e).__name__}")
        return 1

    from uptime_kuma_api import MonitorType, UptimeKumaApi

    try:
        api = UptimeKumaApi(args.url)
        api.login(user, password)
    except Exception as e:
        print(f"Kuma へのログインに失敗: {type(e).__name__}")
        return 1

    try:
        existing = {m["name"] for m in api.get_monitors()}

        rows = []
        for m in wanted:
            if m["name"] in existing:
                verdict = "有り"
            elif m.get("register"):
                verdict = "足す"
            else:
                verdict = "欠落"
            rows.append((m, verdict))

        print("名前\t判定")
        for m, v in rows:
            print(f"{m['name']}\t{v}")
        counts = {v: sum(1 for _, x in rows if x == v) for v in ("有り", "足す", "欠落")}
        print(f"集計: 有り {counts['有り']}・足す {counts['足す']}・欠落 {counts['欠落']}")

        if args.apply:
            for m, v in rows:
                if v != "足す":
                    continue
                api.add_monitor(
                    type=MonitorType.HTTP,
                    name=m["name"],
                    url=m["url"],
                    interval=m["interval"],
                    retryInterval=m["interval"],
                    maxretries=1,
                    accepted_statuscodes=["200-299"],
                    notificationIDList=[],
                )
                print(f"登録: {m['name']}")
            after = {m["name"] for m in api.get_monitors()}
            wanted_names = [m["name"] for m in wanted]
            missing = [n for n in wanted_names if n not in after]
            extra = sorted(after - set(wanted_names))
            print(f"登録後: yml の名前 {len(wanted_names) - len(missing)}/{len(wanted_names)} が本番にある")
            for n in missing:
                print(f"欠け: {n}")
            for n in extra:
                print(f"正本外: {n}")
            if missing:
                return 1
        else:
            extra = sorted(existing - {m["name"] for m in wanted})
            for n in extra:
                print(f"正本外: {n}")

        return 1 if counts["欠落"] else 0
    except Exception as e:
        print(f"処理中にエラー: {type(e).__name__}")
        return 1
    finally:
        try:
            api.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
