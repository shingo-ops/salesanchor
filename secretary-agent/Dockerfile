# ADR-1056 段2: チャット秘書の容器。Claude Code を 1 回だけ動かして、頼みの文を決まった形の JSON に書き換える。
# DB・redis を持たない。ログイン情報 CLAUDE_CODE_OAUTH_TOKEN は compose の env_file から実行時にだけ渡る（イメージに入れない）。
FROM node:22-bookworm-slim
RUN npm install -g @anthropic-ai/claude-code@2.1.314
ENV DISABLE_AUTOUPDATER=1 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
COPY server.mjs probe.mjs prompt.txt schema.json /app/
USER node
CMD ["node","/app/server.mjs"]
