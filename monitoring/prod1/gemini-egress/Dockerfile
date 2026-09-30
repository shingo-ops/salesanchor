# Gemini egress relay (prod1 backnet). design: docs/handoff/gemini-egress-via-prod2/design.md §5-4
# openssh-client はビルド時に入れる（起動のたびに apk CDN へ取りに行かない）
FROM alpine:3.24
RUN apk add --no-cache openssh-client
ENTRYPOINT ["ssh"]
