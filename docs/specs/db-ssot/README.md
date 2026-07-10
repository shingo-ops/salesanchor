# DB設計のSSOT化（db-ssot）— 設計仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> アプリの全データについて「同じ事実は1か所だけ」を徹底し、データの分散・二重管理を防ぐための正本。会話・予測値・金額・分類などの重複をなくし、正本を1つに定める設計を集約する親テーマ。

- あるべき姿（PO承認・正本）: ./ideal-state.md
- KGIと運用: ./kgi.md
- 親: 索引 ../README.md

## 境界（他テーマとの取り決め）

- 取引フロー（transaction-flow）: データ構造の正本は取引フロー側。本テーマは「重複をなくし正本を1か所に定める」原則と、その適用（会話・予測値・金額等）を扱う。
- 受信箱（inbox）: 会話の見せ方はinbox。会話データの正本一元化（conversation_logs / meta_messages 統合）は本テーマで扱う。
- 個別マスタ（商品・国・状態など）: 分類値の台帳化の原則は本テーマ、各マスタの中身は各仕様書。

## 子（適用対象・順次ぶら下げ）

- 会話データの一元化（conversation_logs / meta_messages を1つに）: recon済み・design済 → ./conversation-unification/design.md
- 予測値の分離（手入力の見立てと自動計算の実績値を分ける）: design済 → ./forecast-separation/design.md
- 予測値の整理（手入力=営業優先度／自動計算=CRM本命の2種を分離）: 一部recon済み
- 金額の集約（複数伝票の重複解消）: 未調査
- 分類値の台帳化（表記ゆれ防止）: 未着手

## 維持の仕組み

- 本テーマのファイル変更はPR＋PO承認のみ。process-artifacts gate が通過を管理。
- ideal-state.md の中身はPOの承認した願いであり、Planner・Generatorは勝手に書き換えない。

## 引き継ぎ

- 次回の続き・残り宿題: ./handover.md

## ステータス

あるべき姿・KGI 確定（PlannerがまとめPOが承認・2026-07-09）。子の設計は順次。
