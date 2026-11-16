"""One-command setup for Counterpoint: runs every preliminary step in order, skipping what is already done.
app.py starts it in a background thread on launch; you can also run `python pipeline.py` to do it in the terminal.
Real NASA data only. Needs an Earthdata login (env vars, ~/.netrc, or .env) for GRACE; everything else is optional."""
import datetime, glob, netrc, os, subprocess, sys, threading, time, json

ROOT = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(ROOT, "output"); V = os.path.join(O, "vars"); LOG = os.path.join(O, "pipeline.log")
PY = sys.executable; JOBS = str(max(1, (os.cpu_count() or 2)-1))
_lock = threading.Lock(); _state = {}; _thread = None; _ran = False

# ---------------- settings (.env + environment)
def load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
def save_env(**kv):
    p = os.path.join(ROOT, ".env"); lines = open(p).read().splitlines() if os.path.exists(p) else []
    for k, v in kv.items():
        v = str(v).strip(); lines = [l for l in lines if not l.startswith(k+"=")] + [f"{k}={v}"]; os.environ[k] = v
    open(p, "w").write("\n".join(lines)+"\n")
def creds():
    load_env()
    if not (os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD")):
        try:
            a = netrc.netrc().authenticators("urs.earthdata.nasa.gov")
            if a: os.environ["EARTHDATA_USERNAME"], os.environ["EARTHDATA_PASSWORD"] = a[0], a[2]
        except Exception: pass
    return bool(os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"))

# ---------------- done-checks
def has(var):
    """A feature is ready only when results.csv exists AND meta.json (written last) parses."""
    d = os.path.join(V, var)
    try:
        with open(os.path.join(d, "meta.json")) as f: json.load(f)
        return os.path.exists(os.path.join(d, "results.csv"))
    except Exception: return False
def find_grace():
    f = glob.glob(os.path.join(ROOT, "data", "GRCTellus*.nc")) or glob.glob(os.path.join(ROOT, "data", "*MSCN*.nc"))
    return max(f, key=os.path.getsize) if f else None
def grace_done():
    try: return os.path.exists(f"{O}/results.csv") and os.path.exists(f"{O}/series.csv") and "JPL GRACE" in open(f"{O}/sources.json").read()
    except Exception: return False
def register_done():
    try: return has("grace_lwe") and os.path.getmtime(f"{V}/grace_lwe/results.csv") >= os.path.getmtime(f"{O}/results.csv")
    except Exception: return has("grace_lwe")
def _bbox(): return os.environ.get("FIRMS_BBOX", "-125 30 -110 45").split()

STEPS = [
 dict(id="fetch", title="Download GRACE/GRACE-FO mascons (NASA Earthdata)", core=True, needs="creds", done=lambda: bool(find_grace()), cmd=lambda: [PY, "counterpoint.py", "fetch"]),
 dict(id="grace", title="Grade every trend, find mirror pairs, score the benchmark", core=True, done=grace_done,
      cmd=lambda: [PY, "counterpoint.py", "run", "--grace", find_grace(), "--jobs", JOBS, "--driver-var", "PRECTOTCORR", "--top", "10"]),
 dict(id="register", title="Make GRACE visible to the dashboard", core=True, done=register_done, cmd=lambda: [PY, "features.py", "register-grace"]),
 dict(id="power", title="Water and fire-weather variables (NASA POWER / MERRA-2)", core=False, done=lambda: has("PRECTOTCORR"),
      cmd=lambda: [PY, "features.py", "power", "--stride", os.environ.get("CP_POWER_STRIDE", "2"), "--jobs", JOBS]),
 dict(id="fires", title="Wildfire detections, intensity and peak season (NASA FIRMS)", core=False, needs="firms", done=lambda: has("FIRE_COUNT"),
      cmd=lambda: [PY, "features.py", "fires", "--map-key", os.environ["FIRMS_MAP_KEY"], "--bbox", *_bbox(), "--start", "2002", "--end", "2025", "--jobs", JOBS]),
 dict(id="groundwater", title="Groundwater-style anomaly (GRACE minus GLDAS; large download)", core=False, needs="creds", optin="CP_GROUNDWATER", done=lambda: has("GW_ANOM"),
      cmd=lambda: [PY, "features.py", "groundwater", "--fetch", "--jobs", JOBS]),
]

def _set(i, state, detail=""):
    with _lock: _state[i] = dict(state=state, detail=detail)
def _blocker(s):
    if s.get("optin") and os.environ.get(s["optin"]) != "1": return "Optional: switch on in the sidebar (big download)."
    if s.get("needs") == "creds" and not creds(): return "Needs your free Earthdata login (urs.earthdata.nasa.gov)."
    if s.get("needs") == "firms":
        os.environ["FIRMS_MAP_KEY"] = os.environ.get("FIRMS_MAP_KEY", "").strip().strip("\"'")   # stray spaces/quotes cause "Invalid MAP_KEY"
        if not os.environ["FIRMS_MAP_KEY"]: return "Optional: add a free FIRMS MAP_KEY to enable wildfire layers."
    return None
def _run(s):
    cmd = s["cmd"](); shown = " ".join("***" if c == os.environ.get("FIRMS_MAP_KEY") else str(c) for c in cmd); os.makedirs(O, exist_ok=True)
    with open(LOG, "a") as lg:
        lg.write(f"\n=== {s['title']}  [{datetime.datetime.now():%H:%M:%S}] ===\n$ {shown}\n"); lg.flush()
        return subprocess.Popen(cmd, cwd=ROOT, stdout=lg, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONUNBUFFERED": "1"}).wait()

def _worker():
    global _ran
    load_env(); stop = False
    for s in STEPS:
        i = s["id"]
        if s["done"](): _set(i, "done", "already complete"); continue
        if stop: _set(i, "blocked", "Waiting on an earlier required step."); continue
        why = _blocker(s)
        if why: _set(i, "blocked" if s["core"] else "skipped", why); stop = stop or s["core"]; continue
        _set(i, "running", "Working... (see log)")
        try:
            rc = _run(s)
        except Exception as e:
            rc = f"error: {e}"

        # Clean non-core warning handling
        if rc == 0 and s["done"]():
            _set(i, "done", "finished")
        else:
            if s["core"]:
                _set(i, "failed", f"exit {rc}. See the log below.")
                stop = True
            else:
                _set(i, "blocked", "unavailable currently")

    _ran = True

def start(force=False):
    """Idempotent: starts the background worker once per process (or again when force=True)."""
    global _thread, _ran
    with _lock:
        if _thread and _thread.is_alive(): return
        if _ran and not force: return
        _ran = False; _thread = threading.Thread(target=_worker, daemon=True); _thread.start()
def running(): return bool(_thread and _thread.is_alive())
def core_ready(): return has("grace_lwe")
def status():
    out = []
    for s in STEPS:
        st = _state.get(s["id"]) or dict(state="done" if s["done"]() else "pending", detail="")
        out.append(dict(id=s["id"], title=s["title"], core=s["core"], **st))
    return out
def log_tail(n=25):
    try: return "".join(open(LOG).readlines()[-n:])
    except Exception: return "(no log yet)"

# ---------------- Streamlit UI helpers
ICON = dict(done="✅", running="⏳", pending="⚪", blocked="⚠️", failed="❌", skipped="➖")
def _rows(st):
    for r in status(): st.markdown(f"{ICON[r['state']]} **{r['title']}**" + (f"  \n<span style='color:#888'>{r['detail']}</span>" if r["detail"] and r["state"] != "done" else ""), unsafe_allow_html=True)
def render(st):
    """Full-page setup screen shown until GRACE is ready."""
    st.title("Setting up Counterpoint")
    st.caption("First launch only: downloading real NASA data and running the analysis. This page updates by itself; the dashboard opens when GRACE is ready.")
    rows = status(); _rows(st)
    if any(r["id"] == "fetch" and r["state"] == "blocked" for r in rows) and not creds():
        with st.form("cred"):
            u = st.text_input("Earthdata username"); p = st.text_input("Earthdata password", type="password"); keep = st.checkbox("Save to .env on this computer (plain text; do not commit it)")
            if st.form_submit_button("Save and continue") and u and p:
                os.environ["EARTHDATA_USERNAME"], os.environ["EARTHDATA_PASSWORD"] = u, p
                if keep: save_env(EARTHDATA_USERNAME=u, EARTHDATA_PASSWORD=p)
                start(force=True); st.rerun()
    if any(r["state"] == "failed" for r in rows) and not running():
        if st.button("Retry"): start(force=True); st.rerun()
    with st.expander("Log", expanded=any(r["state"] == "failed" for r in rows)): st.code(log_tail(40))
    if running(): time.sleep(3); st.rerun()
def sidebar_status(st, known, allowed):
    """Sidebar panel for background layers (power, fires, groundwater). Reruns the app when a new feature appears."""
    def body():
        have = {d for d in (os.listdir(V) if os.path.isdir(V) else []) if has(d)} & set(allowed)
        if have != set(known): st.rerun()
        with st.expander("Background setup" + (" (running)" if running() else ""), expanded=running()):
            _rows(st)
            with st.form("bg"):
                key = st.text_input("FIRMS MAP_KEY (free, optional)", os.environ.get("FIRMS_MAP_KEY", ""), type="password")
                bb = st.text_input("Fire area: West South East North", " ".join(_bbox())); gw = st.checkbox("Groundwater-style anomaly (large download)", os.environ.get("CP_GROUNDWATER") == "1")
                if st.form_submit_button("Apply and run"):
                    save_env(FIRMS_MAP_KEY=key, FIRMS_BBOX=bb, CP_GROUNDWATER="1" if gw else "0"); start(force=True); st.rerun()
            if any(r["state"] == "failed" for r in status()): st.code(log_tail(15))
    frag = st.fragment(run_every=5 if running() else None)(body) if hasattr(st, "fragment") else body
    with st.sidebar: frag()

if __name__ == "__main__":
    os.chdir(ROOT); _worker()
    for r in status(): print(f"{ICON[r['state']]} {r['title']}: {r['state']} {r['detail']}")