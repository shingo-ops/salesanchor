FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新とビルドツールのインストール
# fonts-ipafont-gothic: 発注書/請求書PDF(po_renderer/invoice_renderer)の日本語フォント。
#   reportlab の TTFont は TrueType(glyf) のみ対応で、Noto CJK は CFF(PostScript
#   outlines)のため埋め込めず日本語が ■ に化ける。IPA ゴシックは TrueType のため
#   reportlab で埋め込め、/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf に配置される。
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    fonts-ipafont-gothic \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルをコピー
COPY requirements.txt .

# Pythonパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 非rootユーザーを作成して切り替え（Rootlessコンテナ）
# コンテナが侵害されてもroot権限を取得できないようにする
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# ポート8000を公開（コンテナ間通信用）
EXPOSE 8000

# Uvicornでアプリケーションを起動
# workers=1: ADR-081 C項（backend は workers=1 を標準）。
# ループを塞ぐ同期I/Oは #3912・#3934 でスレッドへ退避済み。2 に戻す条件は ADR-081 D項。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
