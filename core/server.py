"""
NexFetch Web Server — serves the HTML UI and bridges download commands to the Python engine.
Runs as a thread inside NexFetchApp. Browser talks to localhost:7432.
"""
import json, os, sys, subprocess, threading, time, datetime, re, hashlib, random
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
_app_ref = None          # set to NexFetchApp instance when server starts
_job_store = {}          # job_id -> {status, log, progress}
_job_lock  = threading.Lock()


def _jid():
    return hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:12]


def _ff_exe(app_dir):
    d = Path(app_dir) / "ffmpeg_bin"
    return str(d / "ffmpeg.exe") if (d / "ffmpeg.exe").exists() else "ffmpeg"


def _ff_args(app_dir):
    d = Path(app_dir) / "ffmpeg_bin"
    return ["--ffmpeg-location", str(d)] if (d / "ffmpeg.exe").exists() else []


def _parse_time(t):
    if not t: return None
    try:
        p = t.strip().split(":")
        if len(p) == 2: return int(p[0]) * 60 + float(p[1])
        if len(p) == 3: return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])
        return float(t)
    except: return None


def _run_job(jid, cmd, save_path):
    """Run a subprocess job and stream output into _job_store."""
    with _job_lock:
        _job_store[jid] = {"status": "running", "log": [], "progress": 0, "save": save_path}
    log = _job_store[jid]["log"]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", creationflags=FLAGS
        )
        for line in proc.stdout:
            l = line.rstrip()
            if not l: continue
            log.append(l)
            # Parse progress from yt-dlp output
            m = re.search(r'(\d+\.?\d*)%', l)
            if m:
                pct = min(int(float(m.group(1))), 99)
                _job_store[jid]["progress"] = pct
        proc.wait()
        _job_store[jid]["status"] = "done" if proc.returncode == 0 else "failed"
        _job_store[jid]["progress"] = 100 if proc.returncode == 0 else _job_store[jid]["progress"]
    except Exception as e:
        log.append(f"ERROR: {e}")
        _job_store[jid]["status"] = "failed"


# ── API handlers ──────────────────────────────────────────────────────────────

def api_download(body, app_dir, dl_base):
    """Handle /api/download — video, audio, images, clips."""
    url      = body.get("url", "").strip()
    fmt      = body.get("fmt", "mp4")
    qual     = body.get("quality", "720p")
    save     = body.get("save", "") or os.path.join(dl_base, "Videos")
    start    = body.get("start", "").strip()
    end      = body.get("end", "").strip()
    ratio    = body.get("ratio", "original")
    is_audio = any(x in fmt for x in ["mp3", "m4a", "opus", "wav", "flac"])
    is_img   = fmt == "images"

    if not url:
        return {"error": "No URL provided"}, 400

    os.makedirs(save, exist_ok=True)
    ff = _ff_args(app_dir)

    cmd = ["yt-dlp", "--no-playlist"] + ff

    if is_img:
        cmd += ["-f", "best[ext=jpg]/best[ext=png]/best[ext=webp]/best",
                "-o", os.path.join(save, "%(uploader)s_%(id)s.%(ext)s"),
                "--no-warnings", url]
    elif is_audio:
        af = fmt if fmt in ("mp3","m4a","opus","wav","flac") else "mp3"
        br = qual.replace("k","") if qual.endswith("k") else "320"
        cmd += ["-x", "--audio-format", af, "--audio-quality", br,
                "--embed-thumbnail", "--add-metadata",
                "--retries", "3", "--newline",
                "-o", os.path.join(save, "%(title)s.%(ext)s"),
                "--no-warnings", "--progress", url]
    else:
        if qual == "best":
            cmd += ["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"]
        else:
            h = qual.replace("p","")
            cmd += ["-f", f"bestvideo[height<={h}]+bestaudio/best", "--merge-output-format", "mp4"]

        # Clip support
        if start or end:
            s_s = _parse_time(start); e_s = _parse_time(end)
            if start and "-" in start and not end:
                parts = start.split("-", 1)
                s_s = _parse_time(parts[0]); e_s = _parse_time(parts[1])
            if s_s is not None or e_s is not None:
                t0 = f"{int((s_s or 0)//60)}:{int((s_s or 0)%60):02d}"
                t1 = f"{int(e_s//60)}:{int(e_s%60):02d}" if e_s else "inf"
                cmd += ["--download-sections", f"*{t0}-{t1}", "--force-keyframes-at-cuts"]

        # Ratio crop
        if ratio and ratio != "original":
            ratio_map = {"16:9":"16/9","9:16":"9/16","1:1":"1/1","4:3":"4/3"}
            rv = ratio_map.get(ratio, "")
            if rv:
                w, h = rv.split("/")
                cmd += ["--ppa", f"Merger+ffmpeg_o:-vf crop=min(iw\\,ih*{w}/{h}):min(ih\\,iw*{h}/{w})"]

        cmd += ["--retries","3","--newline",
                "-o", os.path.join(save,"%(title)s.%(ext)s"),
                "--no-warnings","--progress", url]

    jid = _jid()
    t = threading.Thread(target=_run_job, args=(jid, cmd, save), daemon=True)
    t.start()
    return {"job_id": jid, "save": save}, 200


def api_music(body, app_dir, dl_base):
    """Handle /api/music — YouTube Music + Spotify via spotdl."""
    query  = body.get("query", "").strip()
    fmt    = body.get("fmt", "mp3")
    src    = body.get("src", "youtube-music")
    save   = body.get("save", "") or os.path.join(dl_base, "Music")
    lyrics = body.get("lyrics", True)
    poster = body.get("poster", True)
    meta   = body.get("meta", True)

    if not query:
        return {"error": "No query"}, 400
    os.makedirs(save, exist_ok=True)

    if "open.spotify.com" in query:
        ff = _ff_exe(app_dir)
        cmd = [sys.executable, "-m", "spotdl", "download", query,
               "--output", os.path.join(save, "{title}.{output-ext}"),
               "--format", fmt, "--ffmpeg", ff, "--print-errors"]
        jid = _jid()
        threading.Thread(target=_run_job, args=(jid, cmd, save), daemon=True).start()
        return {"job_id": jid, "save": save}, 200

    is_url   = query.startswith("http")
    is_pl    = is_url and ("playlist" in query or "list=" in query)
    src_map  = {"youtube-music":"ytmsearch","youtube":"ytsearch","youtube-music youtube":"ytmsearch"}
    prefix   = src_map.get(src, "ytmsearch")
    arg      = query if is_url else f"{prefix}:{query}"
    ff       = _ff_args(app_dir)

    cmd = ["yt-dlp"] + ([] if is_pl else ["--no-playlist"]) + ff
    cmd += ["-x", "--audio-format", fmt, "--audio-quality", "0"]
    if poster:
        cmd += ["--embed-thumbnail", "--convert-thumbnails", "jpg",
                "--ppa", "EmbedThumbnail+ffmpeg_o:-vf crop=min(iw\\,ih):min(iw\\,ih),setsar=1"]
    if meta:
        cmd += ["--add-metadata"]
    if lyrics:
        cmd += ["--write-subs","--write-auto-subs","--sub-langs","en.*","--convert-subs","lrc"]
    cmd += ["--retries","3","--newline",
            "-o", os.path.join(save,"%(title)s.%(ext)s"),
            "--no-warnings","--progress", arg]

    jid = _jid()
    threading.Thread(target=_run_job, args=(jid, cmd, save), daemon=True).start()
    return {"job_id": jid, "save": save}, 200


def api_scrape(body, app_dir, dl_base):
    """Handle /api/scrape — return list of links."""
    platform = body.get("platform", "youtube")
    inp      = body.get("input", "").strip()
    limit    = body.get("limit", 100)
    if not inp:
        return {"error": "No input"}, 400

    jid = _jid()
    with _job_lock:
        _job_store[jid] = {"status":"running","log":[],"progress":0,"links":[],"save":""}

    def run():
        links = []
        log   = _job_store[jid]["log"]
        try:
            if platform == "youtube":
                url = inp
            elif platform == "instagram":
                u = inp.lstrip("@")
                if "instagram.com/" in u:
                    u = re.sub(r".*/([^/?#]+).*", r"\1", u).strip("/")
                url = f"https://www.instagram.com/{u}/"
            elif platform == "facebook":
                url = inp if inp.startswith("http") else \
                    f"https://www.facebook.com/{urllib.parse.quote(inp.lstrip('@'),safe='')}"
            elif platform == "tiktok":
                u = inp.lstrip("@")
                url = inp if inp.startswith("http") else f"https://www.tiktok.com/@{u}"
            elif platform == "reddit":
                u = inp.lstrip("r/").lstrip("u/").lstrip("/")
                url = inp if inp.startswith("http") else f"https://www.reddit.com/r/{u}"
            elif platform == "twitter":
                u = inp.lstrip("@")
                url = inp if inp.startswith("http") else f"https://twitter.com/{u}/media"
            elif platform == "adult":
                url = inp if inp.startswith("http") else f"https://{inp}"
            else:
                url = inp

            cmd = ["yt-dlp","--flat-playlist","--print","url",
                   "--no-warnings","--yes-playlist", url]
            if limit and limit != "all":
                cmd += ["--playlist-end", str(limit)]
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=180, creationflags=FLAGS)
            links = [l.strip() for l in r.stdout.splitlines() if l.strip()]

            if not links:
                cmd2 = ["yt-dlp","--flat-playlist","--print","webpage_url",
                        "--no-warnings", url]
                if limit and limit != "all":
                    cmd2 += ["--playlist-end", str(limit)]
                r2 = subprocess.run(cmd2, capture_output=True, text=True,
                                    timeout=180, creationflags=FLAGS)
                links = [l.strip() for l in r2.stdout.splitlines() if l.strip()]

            # Instagram fallback via instaloader
            if not links and platform == "instagram":
                try:
                    import instaloader
                    L = instaloader.Instaloader(sleep=False, quiet=True,
                        download_pictures=False, download_videos=False,
                        download_video_thumbnails=False, download_geotags=False,
                        download_comments=False, save_metadata=False)
                    u2 = inp.lstrip("@")
                    if "instagram.com/" in u2:
                        u2 = re.sub(r".*/([^/?#]+).*",r"\1",u2).strip("/")
                    profile = instaloader.Profile.from_username(L.context, u2)
                    for post in profile.get_posts():
                        links.append(f"https://www.instagram.com/p/{post.shortcode}/")
                        if limit and limit != "all" and len(links) >= int(limit): break
                except Exception as e2:
                    log.append(f"instaloader: {e2}")

            _job_store[jid]["links"]  = links
            _job_store[jid]["status"] = "done"
            _job_store[jid]["progress"] = 100
        except Exception as e:
            log.append(f"Error: {e}")
            _job_store[jid]["status"] = "failed"

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": jid}, 200


def api_job_status(jid):
    """Poll job status."""
    with _job_lock:
        job = _job_store.get(jid)
    if not job:
        return {"error": "Job not found"}, 404
    return {
        "status":   job.get("status","unknown"),
        "progress": job.get("progress", 0),
        "log":      job.get("log", [])[-30:],   # last 30 lines
        "links":    job.get("links", []),
        "save":     job.get("save",""),
    }, 200


def api_open_folder(body):
    """Open folder in Explorer."""
    path = body.get("path","")
    if path and os.path.exists(path):
        if sys.platform == "win32":
            os.startfile(path)
        return {"ok": True}, 200
    return {"error": "Path not found"}, 404


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    app_dir = "."
    dl_base = str(Path.home() / "Downloads" / "NexFetch")

    def log_message(self, fmt, *args): pass  # silence request logs

    def _send(self, data, code=200, ct="application/json"):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_bytes)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(html_bytes)

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0: return {}
        raw = self.rfile.read(length)
        try: return json.loads(raw)
        except: return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/" or path == "/index.html":
            html_path = Path(self.app_dir) / "web" / "index.html"
            if html_path.exists():
                self._send_html(html_path.read_bytes())
            else:
                self._send({"error": "Web UI not found"}, 404)
        elif path.startswith("/api/job/"):
            jid = path.split("/")[-1]
            data, code = api_job_status(jid)
            self._send(data, code)
        elif path == "/api/config":
            from core.app import load_cfg, load_users
            cfg = load_cfg()
            data = {
                "tool_name": cfg.get("tool_name","NexFetch"),
                "version":   cfg.get("version","2.9"),
                "dl_path":   cfg.get("dl_path", self.dl_base),
                "invite_codes": cfg.get("invite_codes",["NEXFETCH2024"]),
            }
            self._send(data)
        elif path == "/api/users":
            from core.app import load_users
            users = load_users()
            # Return sanitised user list (no passwords)
            safe = {u: {k:v for k,v in d.items() if k!="pw"} for u,d in users.items()}
            self._send(safe)
        else:
            self._send({"error": "Not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._body()

        if path == "/api/download":
            data, code = api_download(body, self.app_dir, self.dl_base)
            self._send(data, code)
        elif path == "/api/music":
            data, code = api_music(body, self.app_dir, self.dl_base)
            self._send(data, code)
        elif path == "/api/scrape":
            data, code = api_scrape(body, self.app_dir, self.dl_base)
            self._send(data, code)
        elif path == "/api/open_folder":
            data, code = api_open_folder(body)
            self._send(data, code)
        elif path == "/api/login":
            from core.app import load_users, hpw, load_saved_logins, save_saved_logins
            u = body.get("username","").strip()
            p = body.get("password","")
            users = load_users()
            if u not in users:
                self._send({"error":"Account not found"}, 401); return
            if users[u]["pw"] != hpw(p):
                self._send({"error":"Wrong password"}, 401); return
            ud = {k:v for k,v in users[u].items() if k!="pw"}
            # Save to saved logins
            saved = [s for s in load_saved_logins() if s.get("username")!=u]
            saved.insert(0, {"username":u}); save_saved_logins(saved)
            self._send({"ok":True,"user":ud,"username":u})
        elif path == "/api/register":
            from core.app import load_users, save_users, hpw, load_cfg, save_cfg, udir
            import random as _rand
            body_u = body.get("username","").strip()
            body_p = body.get("password","")
            body_n = body.get("full_name","").strip()
            body_e = body.get("email","").strip()
            body_c = body.get("invite_code","").strip()
            cfg    = load_cfg()
            codes  = cfg.get("invite_codes",["NEXFETCH2024"])
            if isinstance(codes,str): codes=[codes]
            if body_c not in codes:
                self._send({"error":"Invalid invite code"},401); return
            users = load_users()
            if body_u in users:
                self._send({"error":"Username taken"},409); return
            phrases = " ".join(_rand.choices([
                "apple","ocean","river","mountain","forest","thunder",
                "crystal","shadow","falcon","storm","ember","silver",
                "golden","cosmic","nexus","cipher"],k=12))
            role = "user"
            if not cfg.get("admin_username",""):
                role="admin"; cfg["admin_username"]=body_u; save_cfg(cfg)
            import datetime as _dt
            users[body_u]={
                "pw":hpw(body_p),"pw_hint":"","role":role,
                "full_name":body_n,"display_name":body_n,
                "email":body_e,"bio":"","phone":"","dob":"","avatar":"",
                "recovery_phrases":phrases,"notes":"",
                "created":_dt.datetime.now().isoformat(),
            }
            save_users(users); udir(body_u)
            self._send({"ok":True,"phrases":phrases,"role":role})
        else:
            self._send({"error":"Not found"},404)


def start_server(app_dir, dl_base, port=7432):
    """Start the web server in a background thread. Returns the port used."""
    Handler.app_dir = str(app_dir)
    Handler.dl_base = dl_base
    for p in range(port, port+20):
        try:
            srv = HTTPServer(("127.0.0.1", p), Handler)
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            return p
        except OSError:
            continue
    return None
