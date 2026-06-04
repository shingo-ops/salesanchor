FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新とビルドツールのインストール
# fonts-noto-cjk: 発注書PDF(po_renderer)の日本語フォント。未インストールだと
#   Helvetica にフォールバックし日本語が ■ に化ける。インストールすると
#   /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc に配置され、
#   po_renderer の font 候補先頭に一致する。
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    fonts-noto-cjk \
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
# workers=2: 512MB VPSでの上限（メモリ制限による）
# workers=1に戻す場合はメモリ確認後に判断すること
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
