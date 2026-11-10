# card: 段 A 入口の係（nginx）を作り直すとき、10 秒待たずにすぐ止める

状態: カード発行（Opus、2026-11-10）。PO 承認（2026-11-10 チャット「1」＝設計を承認し段 A から作り始める）。設計: [design.md](./design.md) §4 段 A。根拠: [recon.md](./recon.md) §3-1・§3-2。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番には触らない。PR は作らない（Opus が作る）。
基準: origin/main `96a63df05`（この枝の起点）。下の行番号はこの時点のもの。行がずれていたら、行番号ではなく「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。
画面（`frontend/`）・`nginx/`・`.github/workflows/`・ほかのサービスの定義には触らない。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルは §1 の 1 つだけ。新しいファイルは無し。PR は Opus が作る（Sonnet は push まで）。○
- guards/08-vps.md: 本番（VPS）には触らない。反映は合流後の配備が行う。○
- guards/10-executor.md: 散文で組み立てを頼まない（§2 に変更前と変更後の文を書いた）。○

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED nginx-stop-fast HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/nginx-stop-fast` を origin から取り、`docs/handoff/nginx-reload-no-downtime/card-A.md` が在ること。
- P2 `sha256sum docker-compose.yml` の 1 列目が `4bff4bef353030978f460ebfa3cc43c4315ef9ecf70d4163ea3b26e324f92935`。
- P3 `grep -c 'image: nginx:1.31.1' docker-compose.yml` が `1`。
- P4 `sed -n '5,6p' docker-compose.yml` が次の 2 行。
```
  nginx:
    image: nginx:1.31.1
```

## 1. 触るファイル
- `docker-compose.yml`（4 行を足すだけ。消す行は無し）

## 2. 変更の中身

`docker-compose.yml:6` の `    image: nginx:1.31.1` の直後（:7 の `    ports:` の前）に、次の 4 行を足す。字下げは空白 4 つ（tab は使わない）。

変更前（:5-7）:
```yaml
  nginx:
    image: nginx:1.31.1
    ports:
```

変更後（:5-11）:
```yaml
  nginx:
    image: nginx:1.31.1
    # 作り直しのときに丁寧な停止（SIGQUIT）で 10 秒待たない。流れ続ける接続が終わらず、
    # 毎回 10 秒待ってから力ずくで止めていた（docs/handoff/nginx-reload-no-downtime/recon.md §3-2）
    stop_signal: SIGTERM
    stop_grace_period: 3s
    ports:
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/nginx-stop-fast && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P4 を流し、結果をそのまま報告に貼る
    cd ~/sa && ls docs/handoff/nginx-reload-no-downtime/card-A.md | tail -1
    cd ~/sa && sha256sum docker-compose.yml | tail -1
    cd ~/sa && grep -c 'image: nginx:1.31.1' docker-compose.yml | tail -1
    cd ~/sa && sed -n '5,6p' docker-compose.yml | tail -2

手順3 §2 の変更をする

手順4 変わった所の確かめ
    cd ~/sa && sed -n '5,11p' docker-compose.yml | tail -7
    cd ~/sa && git diff --numstat | tail -3
期待: 1 つ目は §2 の変更後と同じ 7 行。2 つ目は `4	0	docker-compose.yml` の 1 行だけ。

手順5 形の確かめ（YAML として読めて、nginx の 2 つの値が入っていること）
    cd ~/sa && python3 -c "import yaml; d=yaml.safe_load(open('docker-compose.yml')); n=d['services']['nginx']; print(n['stop_signal'], n['stop_grace_period'], n['image'])" | tail -1
期待: `SIGTERM 3s nginx:1.31.1`。
`yaml` が無いときは `pip install -q pyyaml 2>&1 | tail -2` の後にもう一度流す。

手順6 docker が使えるときだけ（無ければ「無し」と報告して進む）
    cd ~/sa && (command -v docker >/dev/null && docker compose -f docker-compose.yml config --services 2>&1 | tail -3 || echo "docker 無し") | tail -3

手順7 記録して送る
    cd ~/sa && git add docker-compose.yml && git commit -q -m "fix(nginx): stop immediately on recreate instead of waiting 10s (nginx-reload-no-downtime stage A)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/nginx-stop-fast 2>&1 | tail -3

## 4. 想定される分かれ道

BLOCKED: に入ったら、その場で作業を停止し、それまでの出力と §5 の形の報告を返して終わる（直さずに先へ進まない・別のやり方を試さない）。

- P1〜P4 のどれかが外れた → 実装せず `BLOCKED: P番号 と見えたもの`。
- 手順4 が期待と違う → 出力を報告し、§2 のとおりに直せるなら直してもう一度流す。直らなければ `BLOCKED: 形`。
- 手順5 が期待と違う・YAML として読めない → 出力の最後の 5 行を報告して `BLOCKED: YAML`。
- 手順6 で docker が赤（終了コードが 0 でない）→ 出力の最後の 5 行を報告して進む（環境変数が無いことによる警告は想定内。CI と配備で確かめる）。
- push が拒まれた → 出力の最後の 3 行を報告して `BLOCKED: push`（force はしない）。

## 5. 報告の形

- 1 行目: 受領確認（`RECEIVED nginx-stop-fast HEAD=…`）。
- 手順2・4〜7 の出力（tail の範囲）をそのまま貼る。
- §4 の分かれ道に入ったら、どれに入ったかと見えたもの。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

END OF CARD
