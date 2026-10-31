"""ADR-1052 段2: nginx.conf の case-api の守りの数え合わせ（ファイルを読むだけ。DB も docker も要らない）。

- 443 を受ける server のうち case-api でないものの数 ＝ `if ($is_case_api_sni) { return 421; }` を持つ server の数
  （新しい入口を足したときの 421 の書き忘れを止める）。
- map は 1 つ・case-api の server は 1 つで、SNI と Host の 421 と道の 400 を持つ。
- case-api の location は決まった 5 つと内部の 1 つだけ。管理の口の文字を含む location が無い。
標準の python と pytest だけで動く（.github/workflows/nginx-config-check.yml から走らせる）。
"""

from __future__ import annotations

import re
from pathlib import Path

NGINX_CONF = Path(__file__).resolve().parents[3] / "nginx" / "nginx.conf"

SNI_LINE = "if ($is_case_api_sni) { return 421; }"
CASE_SNI_LINE = "if ($is_case_api_sni = 0) { return 421; }"
CASE_HOST_LINE = 'if ($host != "case-api.salesanchor.jp") { return 421; }'
CASE_400_LINE = 'if ($request_uri ~* "(%2e|%2f|\\.\\.|//)") { return 400; }'
CASE_NAME = "case-api.salesanchor.jp"
MAP_HEAD = "map $ssl_server_name $is_case_api_sni {"
ADMIN_WORDS = ("pending", "ticket", "decision", "audits", "audit-inputs")

_UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# case-api の server が持ってよい location（種類と道の写し）。5 つ + 内部の 1 つ
ALLOWED_LOCATIONS = (
    "= /api/v1/ops/read-window/query",
    f'~ "^/api/v1/ops/case/{_UUID}/(report|unmask-requests)$"',
    f'~ "^/api/v1/ops/case/unmask-requests/{_UUID}$"',
    "= /ops/unmask/read",
    "= /__case_unavailable",
    "/",
)


def strip_comments(text: str) -> str:
    """# から行末までを外す（引用符の中の # は残す）。"""
    out_lines = []
    for line in text.split("\n"):
        quote = None
        cut = len(line)
        for i, ch in enumerate(line):
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
            elif ch == "#":
                cut = i
                break
        out_lines.append(line[:cut].rstrip())
    return "\n".join(out_lines)


def _matching_brace(text: str, open_idx: int) -> int:
    """text[open_idx] の { に対応する } の位置（引用符の中の波かっこは数えない）。"""
    depth = 0
    quote = None
    for i in range(open_idx, len(text)):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("波かっこが閉じていない")


def split_blocks(text: str, head_re: str) -> list[tuple[str, str]]:
    """text の直下にある `<head> { ... }` を (見出し, 中身) の一覧にする（入れ子の中は探さない）。"""
    result = []
    pattern = re.compile(head_re)
    quote = None
    boundary = 0  # 直前の ; { } の次（引用符の中の波かっこ・セミコロンは境にしない）
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == ";":
            boundary = i + 1
        elif ch == "{":
            head = text[boundary:i].strip()
            end = _matching_brace(text, i)
            if pattern.fullmatch(head):
                result.append((head, text[i + 1 : end]))
            i = end
            boundary = end + 1
        elif ch == "}":
            boundary = i + 1
        i += 1
    return result


def server_blocks(conf: str) -> list[str]:
    return [body for _head, body in split_blocks(strip_comments(conf), r"server")]


def _directive_values(body: str, name: str) -> list[str]:
    return re.findall(rf"(?m)^\s*{name}\s+([^;]+);", body)


def listens_443(body: str) -> bool:
    return any(re.match(r"(\[::\]:)?443\b", v.strip()) for v in _directive_values(body, "listen"))


def server_names(body: str) -> list[str]:
    return [n for v in _directive_values(body, "server_name") for n in v.split()]


def location_heads(body: str) -> list[str]:
    # server の直下の location だけ（入れ子の if の中は見ない）
    return [head[len("location") :].strip() for head, _b in split_blocks(body, r"location\s+.+")]


def check_conf(conf: str) -> list[str]:
    """守りの数え合わせ。問題の一覧を返す（空なら合格）。"""
    problems: list[str] = []
    stripped = strip_comments(conf)
    blocks = server_blocks(conf)
    tls = [b for b in blocks if listens_443(b)]
    case_blocks = [b for b in tls if CASE_NAME in server_names(b)]
    other_tls = [b for b in tls if CASE_NAME not in server_names(b)]

    with_line = [b for b in other_tls if SNI_LINE in b]
    if len(other_tls) != len(with_line):
        missing = [server_names(b) for b in other_tls if SNI_LINE not in b]
        problems.append(
            f"443 を受ける case-api 以外の server {len(other_tls)} 個のうち、421 の行を持つのは {len(with_line)} 個"
            f"（足りない server_name: {missing}）"
        )
    if len(other_tls) < 5:
        problems.append(f"443 を受ける case-api 以外の server が {len(other_tls)} 個しかない（今は 5 個）")

    if stripped.count(MAP_HEAD) != 1:
        problems.append(f"map $ssl_server_name $is_case_api_sni の行が {stripped.count(MAP_HEAD)} 個（ちょうど 1 個のはず）")
    if len(case_blocks) != 1:
        problems.append(f"case-api の server が {len(case_blocks)} 個（ちょうど 1 個のはず）")
        return problems

    case = case_blocks[0]
    for label, line in (("SNI の 421", CASE_SNI_LINE), ("Host の 421", CASE_HOST_LINE), ("道の 400", CASE_400_LINE)):
        if line not in case:
            problems.append(f"case-api の server に {label} の行が無い: {line}")
    if SNI_LINE in case:
        problems.append("case-api の server に、他の server 用の 421 の行（$is_case_api_sni を見て返す）がある")

    heads = location_heads(case)
    if sorted(heads) != sorted(ALLOWED_LOCATIONS):
        extra = [h for h in heads if h not in ALLOWED_LOCATIONS]
        lacking = [h for h in ALLOWED_LOCATIONS if h not in heads]
        problems.append(f"case-api の location が決まった 6 個と違う（余分: {extra} / 不足: {lacking}）")
    for head in heads:
        for word in ADMIN_WORDS:
            if word in head:
                problems.append(f"case-api の location に管理の口の文字 {word!r} がある: {head}")
    return problems


def _conf() -> str:
    return NGINX_CONF.read_text("utf-8")


def test_current_nginx_conf_passes_the_count():
    assert check_conf(_conf()) == []


def test_there_are_five_other_tls_servers_and_one_case_api_server():
    blocks = server_blocks(_conf())
    tls = [b for b in blocks if listens_443(b)]
    assert len([b for b in tls if CASE_NAME in server_names(b)]) == 1
    assert len([b for b in tls if CASE_NAME not in server_names(b)]) == 5
    assert all(SNI_LINE in b for b in tls if CASE_NAME not in server_names(b))


def test_removing_one_421_line_makes_the_count_fail():
    """T7 の CI 側: 421 の行を 1 つ消した文字列を渡すと落ちる。"""
    conf = _conf()
    assert SNI_LINE in conf
    broken = conf.replace(SNI_LINE, "", 1)
    problems = check_conf(broken)
    assert problems and any("421 の行を持つのは" in p for p in problems)


def test_removing_each_421_line_one_by_one_fails_every_time():
    conf = _conf()
    n = conf.count(SNI_LINE)
    assert n == 5
    for k in range(n):
        idx = -1
        for _ in range(k + 1):
            idx = conf.index(SNI_LINE, idx + 1)
        broken = conf[:idx] + conf[idx + len(SNI_LINE) :]
        assert check_conf(broken), f"{k + 1} 個目の 421 の行を消しても落ちなかった"


def test_adding_a_new_tls_server_without_the_line_fails():
    conf = _conf()
    extra = (
        "\nserver {\n    listen 443 ssl;\n    listen [::]:443 ssl;\n    server_name new.salesanchor.jp;\n"
        "    location / { return 404; }\n}\n"
    )
    problems = check_conf(conf + extra)
    assert problems and any("new.salesanchor.jp" in p for p in problems)
    # 80 番だけの server は数えない
    only80 = "\nserver {\n    listen 80;\n    server_name x.salesanchor.jp;\n    location / { return 404; }\n}\n"
    assert check_conf(conf + only80) == []


def test_commented_out_line_does_not_count():
    conf = _conf()
    broken = conf.replace(SNI_LINE, "# " + SNI_LINE, 1)
    assert check_conf(broken)


def test_second_map_or_second_case_api_server_fails():
    conf = _conf()
    assert any("map" in p for p in check_conf(conf + "\nmap $ssl_server_name $is_case_api_sni {\n default 0;\n}\n"))
    case_start = conf.index("server_name case-api.salesanchor.jp;")
    block_start = conf.rfind("server {", 0, case_start)
    block_end = _matching_brace(conf, conf.index("{", block_start))
    dup = conf[block_start : block_end + 1]
    assert any("case-api の server が 2 個" in p for p in check_conf(conf + "\n" + dup + "\n"))


def test_case_api_server_needs_its_three_guards():
    conf = _conf()
    for line in (CASE_SNI_LINE, CASE_HOST_LINE, CASE_400_LINE):
        assert line in conf, line
        assert check_conf(conf.replace(line, "", 1)), f"{line} を消しても落ちなかった"


def test_case_api_locations_are_exactly_the_allowed_ones_and_no_admin_path():
    case = [b for b in server_blocks(_conf()) if CASE_NAME in server_names(b)][0]
    heads = location_heads(case)
    assert sorted(heads) == sorted(ALLOWED_LOCATIONS)
    assert len(heads) == 6
    for head in heads:
        assert not any(w in head for w in ADMIN_WORDS)


def test_adding_an_admin_location_to_case_api_fails():
    conf = _conf()
    marker = "    # 上の道以外は 404\n"
    assert marker in conf
    broken = conf.replace(marker, "    location = /api/v1/ops/case/pending { return 200; }\n" + marker, 1)
    problems = check_conf(broken)
    assert any("pending" in p for p in problems)
    broken2 = conf.replace(marker, "    location /api/ { return 200; }\n" + marker, 1)
    assert check_conf(broken2)


def test_case_name_is_written_only_in_known_places():
    """名前の判定の正本は map の 1 か所。case-api の server の中の SNI の判定も同じ変数を使う。"""
    stripped = strip_comments(_conf())
    # 正規表現の形の名前（map のキー）は 1 か所だけ
    assert stripped.count(r"case-api\.salesanchor\.jp") == 1
