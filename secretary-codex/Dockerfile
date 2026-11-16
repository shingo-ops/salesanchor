# ADR-1058 段3: ChatGPT の秘書の容器。Codex CLI を 1 回だけ動かして、頼みの文を決まった形の JSON に書き換える。
# build はリポジトリの根を context にする: DOCKER_BUILDKIT=1 docker build -f secretary-codex/Dockerfile .
# 入れる物は secretary-codex/Dockerfile.dockerignore の許す一覧の5つだけ（指示文・答えの形・つながりの試し・頼みの文の組み立ては secretary-agent と同じファイル）。
# DB・redis を持たない。ログインの鍵は名前付きボリューム（/home/node/.codex）の auth.json だけで、イメージに入れない。
FROM node:22-bookworm-slim
# codex（Rust）は OS の証明書置き場から根の証明書を読む。slim には無いので入れる（card-3e・一時 VM で UnknownIssuer を観測）
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
RUN npm install -g @openai/codex@0.162.1 && npm cache clean --force
ENV CODEX_HOME=/home/node/.codex
# 空の名前付きボリュームは初回にここの持ち主と権限を写す（design.md §5-1）
RUN mkdir -p /home/node/.codex && chown node:node /home/node/.codex && chmod 700 /home/node/.codex
COPY secretary-agent/prompt.txt secretary-agent/schema.json secretary-agent/probe.mjs secretary-agent/compose.mjs secretary-codex/server.mjs /app/
USER node
CMD ["node","/app/server.mjs"]
