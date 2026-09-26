#!/usr/bin/env python3
"""Linux/Docker-only PMG cutover isolation rehearsal."""

from __future__ import annotations
import hashlib, http.client, json, os, re, socket, ssl, subprocess, sys, tempfile, threading, time, traceback, uuid
from pathlib import Path

IMAGE = "nginx:1.31.1"
ROOT = Path(tempfile.mkdtemp(prefix="pmg-cutover-probe-", dir="/tmp"))
C = []
E = []


def run(*a, check=True, timeout=60):
    r = subprocess.run(a, text=True, capture_output=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError("$ " + " ".join(a) + "\n" + r.stdout + r.stderr)
    return r


def ok(n, v, d=""):
    C.append({"name": n, "passed": bool(v), "detail": d})
    if not v:
        raise AssertionError(n + ": " + d)


def wait(n, f, t=10):
    end = time.monotonic() + t
    last = None
    while time.monotonic() < end:
        try:
            x = f()
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(0.1)
            continue
        if x:
            return x
        time.sleep(0.1)
    raise AssertionError(f"{n} timeout; last transient failure: {last}")


def req(port, host, m, path):
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    s = c.wrap_socket(
        socket.create_connection(("127.0.0.1", port), timeout=30), server_hostname=host
    )
    h = http.client.HTTPSConnection(host, port, context=c, timeout=30)
    h.sock = s
    h.request(m, path, headers={"Host": host})
    r = h.getresponse()
    r.read()
    h.close()
    return r.status


FAKE = """from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import threading,json
n=0;l=threading.Lock();started=threading.Event();release=threading.Event()
class H(BaseHTTPRequestHandler):
 def log_message(self,*x):pass
 def do_GET(self):self.go()
 def do_POST(self):self.go()
 def go(self):
  global n
  if self.path=='/__control/count':self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'count':n}).encode());return
  if self.path=='/__control/slow-started':self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'started':started.is_set()}).encode());return
  if self.path=='/__control/release':release.set();self.send_response(204);self.end_headers();return
  with l:n+=1
  if self.path.endswith('/slow'):
   started.set()
   if not release.wait(60):self.send_response(504);self.end_headers();return
  self.send_response(200);self.end_headers()
ThreadingHTTPServer(('0.0.0.0',8080),H).serve_forever()"""


class P:
    def __init__(s):
        s.t = uuid.uuid4().hex
        s.n = "pmg-nginx-" + s.t[:12]
        s.f = "pmg-fake-" + s.t[:12]
        s.net = "pmg-net-" + s.t[:12]
        s.net_id = ""
        s.i = s.fi = ""
        s.ports = {}
        s.logs = {}
        s.state = ROOT / "htpasswd.d" / "pmg-cutover"
        s.state.mkdir(parents=True)
        (ROOT / "htpasswd.d").chmod(0o755)
        s.state.chmod(0o755)
        s.conf = ROOT / "nginx.conf"
        s.good = ROOT / "good"
        s.fake = ROOT / "fake.py"

    def d(s, *a, **k):
        return run("docker", *a, **k)

    def cfg(s, bad=False):
        sv = "\n".join(
            f"""server {{ listen {port} ssl;server_name {h};ssl_certificate /probe/cert;ssl_certificate_key /probe/key;set $allowed 0;if (-f /etc/nginx/htpasswd.d/pmg-cutover/allow-writes) {{ set $allowed 1; }}if ($deny) {{ return 503; }}location / {{proxy_pass http://{s.f}:8080;}}}}"""
            for h, port in (("app.probe.test", 443), ("api.probe.test", 444))
        )
        return f"""events {{}}\nhttp {{error_log /dev/stderr notice;open_file_cache off;map $uri $target {{default 0;~^/api/v1/(tcg|super-admin/tcg)(/|$) 1;}}map "$request_method:$target" $needs {{default 0;~^(GET|HEAD|OPTIONS):1$ 0;~:1$ 1;}}map "$needs:$allowed" $deny {{default 0;"1:0" 1;}}{sv}{"INVALID;" if bad else ""}}}"""

    def rewrite(s, x):
        ino = s.conf.stat().st_ino
        with s.conf.open("r+") as f:
            f.seek(0)
            f.write(x)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())
        ok("same inode", s.conf.stat().st_ino == ino)
        running = s.d("inspect", s.i, "--format", "{{.State.Running}}", check=False)
        if running.stdout.strip() == "true":
            s.verify_bind_view()

    def start(s):
        run(
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=x",
            "-keyout",
            str(ROOT / "key"),
            "-out",
            str(ROOT / "cert"),
        )
        s.conf.write_text(s.cfg())
        s.good.write_bytes(s.conf.read_bytes())
        s.fake.write_text(FAKE)
        s.net_id = s.d(
            "network",
            "create",
            "--label",
            "pmg.cutover.probe=" + s.t,
            s.net,
        ).stdout.strip()
        s.fi = s.d(
            "create",
            "--name",
            s.f,
            "--label",
            "pmg.cutover.probe=" + s.t,
            "--network",
            s.net,
            "-p",
            "127.0.0.1::8080",
            "-v",
            f"{s.fake}:/x.py:ro",
            "python:3.12-alpine",
            "python",
            "/x.py",
        ).stdout.strip()
        s.d("start", s.fi)
        s.i = s.d(
            "create",
            "--name",
            s.n,
            "--label",
            "pmg.cutover.probe=" + s.t,
            "--network",
            s.net,
            "-p",
            "127.0.0.1::444",
            "-p",
            "127.0.0.1::443",
            "-v",
            f"{s.conf}:/etc/nginx/nginx.conf:ro",
            "-v",
            f"{ROOT}/htpasswd.d:/etc/nginx/htpasswd.d:ro",
            "-v",
            f"{ROOT}:/probe:ro",
            IMAGE,
        ).stdout.strip()
        s.d("start", s.i)
        inspection = json.loads(s.d("inspect", s.i).stdout)[0]
        ports = inspection["NetworkSettings"].get("Ports") or {}
        if not {"443/tcp", "444/tcp"} <= set(ports):
            diagnostic = {
                "State": inspection.get("State"),
                "HostConfig.PortBindings": inspection.get("HostConfig", {}).get(
                    "PortBindings"
                ),
                "NetworkSettings.Ports": ports,
            }
            raise AssertionError(
                "missing TLS published binding: " + json.dumps(diagnostic)
            )
        ok(
            "one binding per TLS port",
            all(
                isinstance(ports.get(key), list) and len(ports[key]) == 1
                for key in ("443/tcp", "444/tcp")
            ),
            repr(ports),
        )
        b = [ports["443/tcp"][0], ports["444/tcp"][0]]
        ok(
            "two loopback random TLS ports",
            len(b) == 2
            and len({x["HostPort"] for x in b}) == 2
            and all(x["HostIp"] == "127.0.0.1" for x in b),
        )
        s.ports = dict(
            zip(("app.probe.test", "api.probe.test"), [int(x["HostPort"]) for x in b])
        )
        ok("published TLS bindings", True, json.dumps(s.ports, sort_keys=True))
        m = json.loads(s.d("inspect", s.i, "--format", "{{json .Mounts}}").stdout)
        q = [x for x in m if x["Source"] in (str(s.conf), str(ROOT / "htpasswd.d"))]
        ok(
            "readonly bind mounts",
            len(q) == 2 and all(x["Type"] == "bind" and not x["RW"] for x in q),
        )
        wait("TLS readiness", lambda: s.get("app.probe.test", "GET", "/") == 200)
        s.verify_bind_view()

    def verify_bind_view(s):
        config_inode = int(
            s.d("exec", s.i, "stat", "-c", "%i", "/etc/nginx/nginx.conf").stdout
        )
        state_inode = int(
            s.d(
                "exec", s.i, "stat", "-c", "%i", "/etc/nginx/htpasswd.d/pmg-cutover"
            ).stdout
        )
        container_digest = s.d(
            "exec", s.i, "sha256sum", "/etc/nginx/nginx.conf"
        ).stdout.split()[0]
        ok(
            "config host/container inode",
            config_inode == s.conf.stat().st_ino,
            str(config_inode),
        )
        ok(
            "state host/container inode",
            state_inode == s.state.stat().st_ino,
            str(state_inode),
        )
        ok(
            "config host/container SHA256",
            container_digest == hashlib.sha256(s.conf.read_bytes()).hexdigest(),
            container_digest,
        )

    def refresh_ports(s):
        inspection = json.loads(s.d("inspect", s.i).stdout)[0]
        ports = inspection["NetworkSettings"].get("Ports") or {}
        ok(
            "restart has TLS bindings",
            {"443/tcp", "444/tcp"} <= set(ports),
            repr(ports),
        )
        ok(
            "restart one binding per TLS port",
            all(
                isinstance(ports.get(key), list) and len(ports[key]) == 1
                for key in ("443/tcp", "444/tcp")
            ),
            repr(ports),
        )
        bindings = [ports["443/tcp"][0], ports["444/tcp"][0]]
        ok(
            "restart TLS bindings are unique loopback",
            len({item["HostPort"] for item in bindings}) == 2
            and all(item["HostIp"] == "127.0.0.1" for item in bindings),
            repr(bindings),
        )
        s.ports = dict(
            zip(
                ("app.probe.test", "api.probe.test"),
                (int(item["HostPort"]) for item in bindings),
            )
        )
        ok(
            "refreshed published TLS bindings",
            True,
            json.dumps(s.ports, sort_keys=True),
        )

    def get(s, h, m, p):
        return req(s.ports[h], h, m, p)

    def all(s, m, p, w):
        for h in s.ports:
            ok(f"{h} {m} {p}", s.get(h, m, p) == w)

    def ctl(s, p):
        port = int(s.d("port", s.fi, "8080").stdout.rsplit(":", 1)[1])
        h = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        h.request("GET", p)
        r = h.getresponse()
        b = r.read()
        h.close()
        return r.status, b

    def count(s):
        status, body = s.ctl("/__control/count")
        ok("fake count control", status == 200)
        return json.loads(body)["count"]

    def process_facts(s):
        script = "for p in /proc/[0-9]*; do x=$(tr '\\0' ' ' < $p/cmdline); case \"$x\" in 'nginx: master process'*) echo M:${p##*/};; 'nginx: worker process'*) echo W:${p##*/};; esac; done"
        out = s.d("exec", s.i, "sh", "-c", script).stdout.split()
        return next((x[2:] for x in out if x.startswith("M:")), ""), {
            x[2:] for x in out if x.startswith("W:")
        }

    def log(s):
        r = s.d("logs", s.i, check=False)
        s.logs[s.i] = r.stdout + r.stderr
        return r.stderr

    def new_error(s, before):
        fresh = s.log()[len(before) :]
        return fresh if re.search(r"invalid|emerg|error", fresh, re.I) else False

    def new_workers(s, master, workers):
        now_master, now_workers = s.process_facts()
        return now_workers - workers if now_master == master else False

    def exited_state(s):
        state = json.loads(s.d("inspect", s.i, "--format", "{{json .State}}").stdout)
        return state if state["Status"] == "exited" else False

    def hup(s, expect_invalid=False):
        master, workers = s.process_facts()
        ok("master exists before HUP", bool(master))
        ok("workers exist before HUP", bool(workers))
        before = s.log()
        r = s.d("kill", "--signal=HUP", s.i, check=False)
        ok("actual Docker HUP delivered", r.returncode == 0, r.stderr)
        if expect_invalid:
            wait("new invalid-HUP error log", lambda: s.new_error(before))
            now_master, now_workers = s.process_facts()
            ok("invalid HUP retains master", now_master == master)
            ok("invalid HUP retains prior workers", workers <= now_workers)
            s.all("POST", "/api/v1/tcg/", 503)
            return r
        new = wait(
            "new worker after HUP",
            lambda: s.new_workers(master, workers),
        )
        ok("new workers recorded", bool(new), repr(new))
        return r

    def clean(s):
        for x in (s.i, s.fi):
            if x:
                inspected = s.d(
                    "inspect",
                    x,
                    "--format",
                    '{{index .Config.Labels "pmg.cutover.probe"}}',
                    check=False,
                )
                if inspected.returncode or inspected.stdout.strip() != s.t:
                    E.append("container cleanup identity check failed: " + x)
                    continue
                result = s.d("rm", "-f", x, check=False)
                if result.returncode:
                    E.append("container cleanup: " + result.stderr)
        if s.net_id:
            inspected = s.d(
                "network",
                "inspect",
                s.net_id,
                "--format",
                '{{index .Labels "pmg.cutover.probe"}}',
                check=False,
            )
            if inspected.returncode or inspected.stdout.strip() != s.t:
                E.append("network cleanup identity check failed: " + s.net_id)
                return
            result = s.d("network", "rm", s.net_id, check=False)
            if result.returncode:
                E.append("network cleanup: " + result.stderr)


def main():
    p = P()
    good = False
    digest = ""
    try:
        dv = run("docker", "--version").stdout.strip()
        run("docker", "pull", IMAGE)
        digest = run(
            "docker", "image", "inspect", IMAGE, "--format", "{{index .RepoDigests 0}}"
        ).stdout.strip()
        p.start()
        paths = ("/api/v1/tcg/", "/api/v1/super-admin/tcg/")
        base = p.count()
        for x in paths:
            p.all("POST", x, 503)
        ok("absent no forwarding", p.count() == base)
        p.all("GET", paths[0], 200)
        p.all("POST", "/other", 200)
        (p.state / "allow-writes").write_text("x")
        for x in paths:
            p.all("POST", x, 200)
        n = p.count()
        (p.state / "allow-writes").unlink()
        for x in paths:
            p.all("POST", x, 503)
        ok("cancel no forwarding", p.count() == n)
        (p.state / "allow-writes").mkdir()
        p.all("POST", paths[0], 503)
        (p.state / "allow-writes").rmdir()
        p.rewrite(p.cfg() + "\n# bytes changed\n")
        ok(
            "valid nginx t",
            p.d("exec", p.i, "nginx", "-t", check=False).returncode == 0,
        )
        ok("HUP valid", p.hup().returncode == 0)
        for path in paths:
            p.all("POST", path, 503)
        p.rewrite(p.cfg(True))
        ok("bad nginx t", p.d("exec", p.i, "nginx", "-t", check=False).returncode != 0)
        ok("HUP bad retained", p.hup(expect_invalid=True).returncode == 0)
        p.rewrite(p.good.read_text())
        ok("restore t", p.d("exec", p.i, "nginx", "-t", check=False).returncode == 0)
        p.hup()
        for path in paths:
            p.all("POST", path, 503)
        p.rewrite("events {")
        p.d("stop", p.i)
        restart_log = p.log()
        ok("start submits bad config", p.d("start", p.i, check=False).returncode == 0)
        exited = wait("bad restart exited", p.exited_state)
        ok("bad restart nonzero exit", int(exited["ExitCode"]) != 0, repr(exited))
        ok("bad restart logs invalid config", bool(p.new_error(restart_log)))
        p.rewrite(p.good.read_text())
        p.d("start", p.i)
        p.refresh_ports()
        wait("restart TLS", lambda: p.get("app.probe.test", "GET", "/") == 200)
        p.verify_bind_view()
        for path in paths:
            p.all("POST", path, 503)
        (p.state / "allow-writes").write_text("x")
        out = []
        th = threading.Thread(
            target=lambda: out.append(
                p.get("app.probe.test", "POST", "/api/v1/tcg/slow")
            )
        )
        th.start()
        wait(
            "slow started",
            lambda: json.loads(p.ctl("/__control/slow-started")[1])["started"],
        )
        (p.state / "allow-writes").unlink()
        p.hup()
        p.all("POST", paths[0], 503)
        release_status, _ = p.ctl("/__control/release")
        ok("fake release control", release_status == 204)
        th.join(35)
        ok("slow thread joined", not th.is_alive())
        ok("slow completes", out == [200])
        good = True
    except BaseException:
        E.append(traceback.format_exc())
    finally:
        for container_id in (p.i, p.fi):
            if container_id:
                try:
                    result = p.d("logs", container_id, check=False)
                    p.logs[container_id] = result.stdout + result.stderr
                except BaseException:
                    E.append(traceback.format_exc())
        try:
            p.clean()
        except BaseException:
            E.append(traceback.format_exc())
        good = good and not E
        data = {
            "passed": good,
            "commit": os.getenv("GITHUB_SHA", "local"),
            "docker": locals().get("dv", ""),
            "image": IMAGE,
            "image_actual_digest": digest,
            "names": {"nginx": p.n, "fake": p.f, "network": p.net},
            "checks": C,
            "errors": E,
            "logs": p.logs,
        }
        (ROOT / "results.json").write_text(json.dumps(data, indent=2))
        print(json.dumps(data, indent=2))
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())
