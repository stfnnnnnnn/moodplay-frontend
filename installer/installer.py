#!/usr/bin/env python3
"""
MoodPlay Installer
Instance-Guided Semantic Video Colorization System
Silently installs all dependencies and clones the MoodPlay repository.
"""

import ctypes
import sys
import os
import subprocess
import threading
import urllib.request
import urllib.error
import tempfile
import shutil

try:
    import winreg
except ImportError:
    winreg = None

try:
    import webview
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "pywebview"], check=True)
    import webview

# ─── Configuration ─────────────────────────────────────────────────────────────

REPO_URL    = "https://huggingface.co/stfnnnnnnn/moodplay"
REPO_BRANCH = "working_uns"
CLONE_DIR   = r"C:\moodplay"

DOWNLOADS = {
    "miniconda": {
        "url":      "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe",
        "filename": "Miniconda3-latest-Windows-x86_64.exe",
    },
    "py310": {
        "url":      "https://www.python.org/ftp/python/3.10.9/python-3.10.9-amd64.exe",
        "filename": "python-3.10.9-amd64.exe",
    },
    "py311": {
        "url":      "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe",
        "filename": "python-3.11.9-amd64.exe",
    },
    "vsbuild": {
        "url":      "https://aka.ms/vs/17/release/vs_BuildTools.exe",
        "filename": "vs_BuildTools.exe",
    },
}

VS_COMPONENTS = [
    "Microsoft.VisualStudio.Workload.VCTools",
    "Microsoft.VisualStudio.Component.VC.143",
    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
    "Microsoft.VisualStudio.Component.Windows11SDK.26100",
]

# ─── UAC Elevation ─────────────────────────────────────────────────────────────

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def elevate():
    """Re-launch this process with administrator privileges."""
    if getattr(sys, "frozen", False):
        exe    = sys.executable
        params = ""
    else:
        exe    = sys.executable
        params = f'"{os.path.abspath(sys.argv[0])}"'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    sys.exit(0)

# ─── Embedded HTML/CSS/JS UI ───────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>MoodPlay Installer</title>
<style>
  :root {
    --bg:       #0d0d1a;
    --surface:  #12122a;
    --surface2: #1a1a35;
    --accent:   #7c3aed;
    --accent2:  #5b21b6;
    --glow:     rgba(124,58,237,0.4);
    --success:  #10b981;
    --error:    #ef4444;
    --warn:     #f59e0b;
    --text:     #e2e8f0;
    --muted:    #64748b;
    --border:   rgba(255,255,255,0.07);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; overflow: hidden; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 13px;
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  /* ── Header ── */
  .hdr {
    background: linear-gradient(135deg, #170d3b 0%, #0d0d1a 100%);
    border-bottom: 1px solid var(--border);
    padding: 16px 24px 14px;
    flex-shrink: 0;
  }
  .hdr-top { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
  .logo {
    width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
    background: linear-gradient(135deg, var(--accent), #2563eb);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; font-weight: 900; color: #fff;
    box-shadow: 0 0 22px var(--glow);
  }
  .hdr-title { font-size: 16px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.3px; }
  .hdr-sub   { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .prog-track {
    height: 5px; background: var(--surface2); border-radius: 3px; overflow: hidden;
  }
  .prog-fill {
    height: 100%; width: 0%;
    background: linear-gradient(90deg, var(--accent), #2563eb);
    border-radius: 3px;
    transition: width 0.5s ease;
    box-shadow: 0 0 10px var(--glow);
  }

  /* ── Main ── */
  .main { display: flex; flex: 1; overflow: hidden; }

  /* Steps panel */
  .steps-pane {
    width: 300px; flex-shrink: 0;
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 14px 10px;
    display: flex; flex-direction: column; gap: 3px;
  }
  .steps-pane::-webkit-scrollbar { width: 3px; }
  .steps-pane::-webkit-scrollbar-thumb { background: var(--surface2); border-radius: 2px; }
  .sec-lbl {
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 1px; color: var(--muted); padding: 4px 8px 10px;
  }
  .step {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 10px; border-radius: 8px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
  }
  .step.running { background: rgba(124,58,237,0.1); border-color: rgba(124,58,237,0.3); }
  .step.done    { background: rgba(16,185,129,0.07); border-color: rgba(16,185,129,0.25); }
  .step.error   { background: rgba(239,68,68,0.08);  border-color: rgba(239,68,68,0.25); }
  .step.skipped { background: rgba(245,158,11,0.07); border-color: rgba(245,158,11,0.25); }
  .step-ico {
    width: 26px; height: 26px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; font-size: 12px; font-weight: 700;
  }
  .step.pending .step-ico { background: var(--surface2); color: var(--muted); }
  .step.running .step-ico { background: rgba(124,58,237,0.2); color: var(--accent); }
  .step.done    .step-ico { background: rgba(16,185,129,0.2); color: var(--success); }
  .step.error   .step-ico { background: rgba(239,68,68,0.2);  color: var(--error); }
  .step.skipped .step-ico { background: rgba(245,158,11,0.2); color: var(--warn); }
  .step-txt { flex: 1; min-width: 0; }
  .step-name { font-weight: 600; font-size: 12px; color: #f1f5f9; }
  .step.pending .step-name { color: var(--muted); }
  .step-desc { font-size: 10.5px; color: var(--muted); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  @keyframes spin { to { transform: rotate(360deg); } }
  .spin {
    width: 14px; height: 14px;
    border: 2px solid rgba(124,58,237,0.3);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }

  /* Log panel */
  .log-pane {
    flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 14px 18px;
  }
  .log-hdr {
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 1px; color: var(--muted); margin-bottom: 8px; flex-shrink: 0;
  }
  .log-body {
    flex: 1; overflow-y: auto;
    background: #07070f;
    border: 1px solid var(--border); border-radius: 8px;
    padding: 11px 13px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 11.5px; line-height: 1.75;
  }
  .log-body::-webkit-scrollbar { width: 3px; }
  .log-body::-webkit-scrollbar-thumb { background: var(--surface2); border-radius: 2px; }
  .le       { display: block; }
  .le.info  { color: #475569; }
  .le.msg   { color: #94a3b8; }
  .le.ok    { color: var(--success); }
  .le.err   { color: #f87171; }
  .le.warn  { color: var(--warn); }
  .le.step  { color: #a78bfa; font-weight: 700; }
  .le.skip  { color: var(--warn); }
  .le.dl    { color: #38bdf8; }
  .ts { color: #1e293b; margin-right: 6px; font-size: 10px; user-select: none; }

  /* Footer */
  .footer {
    border-top: 1px solid var(--border);
    padding: 12px 24px;
    display: flex; align-items: center; justify-content: space-between;
    flex-shrink: 0; background: var(--surface);
  }
  .status { font-size: 12px; color: var(--muted); }
  .status b { color: var(--text); font-weight: 600; }
  .btns { display: flex; gap: 8px; }
  .btn {
    padding: 8px 26px; border-radius: 8px; border: none;
    font-size: 13px; font-weight: 600; cursor: pointer;
    transition: all 0.2s ease; letter-spacing: 0.2px;
  }
  .btn-p {
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: #fff; box-shadow: 0 0 20px var(--glow);
  }
  .btn-p:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 28px var(--glow); }
  .btn-p:disabled { opacity: 0.45; cursor: not-allowed; transform: none; box-shadow: none; }
  .btn-s {
    background: var(--surface2); color: var(--text);
    border: 1px solid var(--border);
  }
  .btn-s:hover { background: #222245; }
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-top">
    <div class="logo">M</div>
    <div>
      <div class="hdr-title">MoodPlay Installer</div>
      <div class="hdr-sub">Instance-Guided Semantic Video Colorization System</div>
    </div>
  </div>
  <div class="prog-track"><div class="prog-fill" id="gp"></div></div>
</div>

<div class="main">
  <div class="steps-pane">
    <div class="sec-lbl">Installation Steps</div>
    <div id="stepsList"></div>
  </div>
  <div class="log-pane">
    <div class="log-hdr">Installation Log</div>
    <div class="log-body" id="logBody"></div>
  </div>
</div>

<div class="footer">
  <div class="status" id="statusTxt">Ready. Click <b>Start Install</b> to begin.</div>
  <div class="btns">
    <button class="btn btn-s" onclick="closeWin()">Exit</button>
    <button class="btn btn-p" id="btnStart" onclick="doInstall()">Start Install</button>
  </div>
</div>

<script>
const STEPS = [
  {id:"git",       name:"Git",                      desc:"Version control system"},
  {id:"ffmpeg",    name:"FFmpeg (Gyan)",             desc:"Video processing engine"},
  {id:"miniconda", name:"Miniconda",                 desc:"Conda package manager"},
  {id:"py310",     name:"Python 3.10.9",             desc:"Primary ML runtime"},
  {id:"py311",     name:"Python 3.11.9",             desc:"Secondary runtime"},
  {id:"vsbuild",   name:"VS Build Tools 2022",       desc:"C++ compiler + MSVC"},
  {id:"clone",     name:"Clone Repository",          desc:"HuggingFace → C:\\moodplay"},
  {id:"setup",     name:"Setup Conda Environment",   desc:"setup_windows.ps1 (may take 10–30 min)"},
  {id:"pathenv",   name:"Update System PATH",        desc:"Register all tools"},
];
const ICONS = {pending:"○", done:"✓", error:"✗", skipped:"→"};
let doneCount = 0;

function renderSteps() {
  document.getElementById("stepsList").innerHTML = STEPS.map(s => `
    <div class="step pending" id="step_${s.id}">
      <div class="step-ico" id="ico_${s.id}">○</div>
      <div class="step-txt">
        <div class="step-name">${s.name}</div>
        <div class="step-desc" id="dsc_${s.id}">${s.desc}</div>
      </div>
    </div>`).join("");
}

function ts() {
  return new Date().toTimeString().slice(0,8);
}

function log(msg, type) {
  const lb = document.getElementById("logBody");
  const el = document.createElement("span");
  el.className = "le " + (type || "msg");
  el.innerHTML = `<span class="ts">${ts()}</span>${msg}`;
  lb.appendChild(el);
  lb.appendChild(document.createElement("br"));
  lb.scrollTop = lb.scrollHeight;
}

function updateStep(id, status, msg) {
  const el  = document.getElementById("step_" + id);
  const ico = document.getElementById("ico_"  + id);
  const dsc = document.getElementById("dsc_"  + id);
  if (!el) return;
  el.className = "step " + status;
  if (status === "running") {
    ico.innerHTML = '<div class="spin"></div>';
  } else {
    ico.textContent = ICONS[status] || "?";
  }
  if (msg) dsc.textContent = msg;
  if (["done","error","skipped"].includes(status)) {
    doneCount++;
    document.getElementById("gp").style.width = Math.round(doneCount / STEPS.length * 100) + "%";
    const t = status === "done" ? "ok" : status === "error" ? "err" : "skip";
    const p = status === "done" ? "✓" : status === "error" ? "✗" : "→";
    log(p + " " + (msg || id), t);
  }
}

function logMessage(msg, type) { log(msg, type || "msg"); }
function setStatus(html)       { document.getElementById("statusTxt").innerHTML = html; }

function onComplete(success) {
  const b = document.getElementById("btnStart");
  b.disabled = false;
  b.textContent = "Done";
  b.classList.replace("btn-p", "btn-s");
  if (success) {
    setStatus('<span style="color:#10b981;font-weight:600">✓ Installation complete!</span> MoodPlay is ready.');
    document.getElementById("gp").style.width = "100%";
  } else {
    setStatus('<span style="color:#ef4444;font-weight:600">Completed with errors.</span> Check the log above.');
  }
}

function doInstall() {
  document.getElementById("btnStart").disabled = true;
  document.getElementById("btnStart").textContent = "Installing…";
  setStatus("Installation in progress…");
  log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info");
  log("MoodPlay Installer — starting sequence", "step");
  log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info");
  window.pywebview.api.start_install();
}

function closeWin() { window.pywebview.api.close_window(); }

renderSteps();
</script>
</body>
</html>"""

# ─── Global window reference ───────────────────────────────────────────────────

_window = None

# ─── UI helpers ────────────────────────────────────────────────────────────────

def _esc(s):
    """Escape a string for safe injection into a JS double-quoted string."""
    return (str(s)
            .replace("\\", "\\\\")
            .replace('"',  '\\"')
            .replace("\n", " ")
            .replace("\r", ""))

def log(msg, kind="msg"):
    if _window:
        _window.evaluate_js(f'logMessage("{_esc(msg)}", "{kind}")')

def update_step(step_id, status, message=""):
    if _window:
        _window.evaluate_js(f'updateStep("{step_id}", "{status}", "{_esc(message)}")')

def set_status(html):
    if _window:
        _window.evaluate_js(f'setStatus("{_esc(html)}")')

# ─── Shell helpers ─────────────────────────────────────────────────────────────

def run_cmd(cmd, timeout=3600, cwd=None):
    """Run a shell command, stream last few output lines to UI, return success."""
    log(f"  $ {cmd[:130]}{'…' if len(cmd)>130 else ''}", "info")
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, errors="replace", cwd=cwd
        )
        for line in r.stdout.strip().splitlines()[-5:]:
            line = line.strip()
            if line:
                log(f"    {line}", "info")
        if r.returncode != 0:
            for line in r.stderr.strip().splitlines()[-3:]:
                line = line.strip()
                if line:
                    log(f"    !! {line}", "warn")
        return r.returncode == 0, r.stdout
    except subprocess.TimeoutExpired:
        log(f"  TIMEOUT after {timeout}s", "err")
        return False, ""
    except Exception as e:
        log(f"  Exception: {e}", "err")
        return False, ""

def download_file(url, dest, step_id):
    """Download a file with % progress piped to the UI."""
    last = [-1]

    def hook(count, block_size, total):
        if total > 0:
            pct = min(100, int(count * block_size * 100 / total))
            if pct != last[0] and pct % 10 == 0:
                last[0] = pct
                done_mb  = count * block_size / 1_048_576
                total_mb = total / 1_048_576
                log(f"  Downloading… {pct}%  ({done_mb:.0f}/{total_mb:.0f} MB)", "dl")
                update_step(step_id, "running", f"Downloading… {pct}%")

    try:
        urllib.request.urlretrieve(url, dest, hook)
        return True
    except Exception as e:
        log(f"  Download failed: {e}", "err")
        return False

# ─── Detection helpers ─────────────────────────────────────────────────────────

def winget_has(pkg_id):
    ok, out = run_cmd(
        f'winget list --id "{pkg_id}" -e --accept-source-agreements 2>nul',
        timeout=45,
    )
    return ok and pkg_id.lower() in out.lower()

def py_launcher_has(ver):
    """Check via the py launcher (py -3.10 --version)."""
    ok, _ = run_cmd(f'py -{ver} --version 2>nul', timeout=15)
    return ok

def miniconda_exists():
    candidates = [
        os.path.expandvars(r"%USERPROFILE%\Miniconda3"),
        os.path.expandvars(r"%USERPROFILE%\miniconda3"),
        r"C:\Miniconda3", r"C:\miniconda3",
        r"C:\ProgramData\Miniconda3", r"C:\ProgramData\miniconda3",
    ]
    return any(os.path.isdir(p) for p in candidates)

def vsbuild_exists():
    vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if not os.path.isfile(vswhere):
        return False
    ok, out = run_cmd(
        f'"{vswhere}" -products * -requires '
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json',
        timeout=30
    )
    return ok and out.strip() not in ("", "[]")

# ─── PATH registry helper ──────────────────────────────────────────────────────

def add_to_system_path(new_path):
    if not new_path or not os.path.isdir(new_path):
        return
    if winreg is None:
        log(f"  winreg unavailable — cannot add {new_path}", "warn")
        return
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        )
        current, _ = winreg.QueryValueEx(key, "Path")
        parts = [p.strip() for p in current.split(";") if p.strip()]
        if new_path not in parts:
            parts.append(new_path)
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(parts))
            log(f"  PATH ← {new_path}", "ok")
        else:
            log(f"  PATH already has: {new_path}", "info")
        winreg.CloseKey(key)
    except Exception as e:
        log(f"  PATH registry error: {e}", "err")

def broadcast_env_change():
    """Tell Explorer and running shells that the environment changed."""
    try:
        HWND_BROADCAST   = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0,
            "Environment", SMTO_ABORTIFHUNG, 5000, None
        )
    except Exception:
        pass

# ─── Step implementations ──────────────────────────────────────────────────────

def step_git():
    sid = "git"
    update_step(sid, "running", "Checking…")
    log("\n━━ Git", "step")
    if winget_has("Git.Git"):
        update_step(sid, "skipped", "Already installed")
        return True
    update_step(sid, "running", "Installing via winget…")
    ok, _ = run_cmd(
        "winget install --id Git.Git -e --source winget --silent "
        "--accept-package-agreements --accept-source-agreements",
        timeout=300,
    )
    if ok:
        update_step(sid, "done", "Git installed")
    else:
        update_step(sid, "error", "Git install failed")
    return ok


def step_ffmpeg():
    sid = "ffmpeg"
    update_step(sid, "running", "Checking…")
    log("\n━━ FFmpeg", "step")
    if winget_has("Gyan.FFmpeg"):
        update_step(sid, "skipped", "Already installed")
        _ensure_ffmpeg_path()
        return True
    update_step(sid, "running", "Installing via winget…")
    ok, _ = run_cmd(
        "winget install --id Gyan.FFmpeg -e --source winget --silent "
        "--accept-package-agreements --accept-source-agreements",
        timeout=300,
    )
    _ensure_ffmpeg_path()
    if ok:
        update_step(sid, "done", "FFmpeg installed")
    else:
        update_step(sid, "error", "FFmpeg install failed (non-fatal)")
    return ok


def _ensure_ffmpeg_path():
    """Search common FFmpeg bin locations and add the first found to PATH."""
    candidates = [
        r"C:\Program Files\ffmpeg\bin",
        r"C:\ffmpeg\bin",
        r"C:\ProgramData\chocolatey\bin",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg\bin"),
    ]
    # Also glob for any winget-installed ffmpeg
    base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    if os.path.isdir(base):
        for entry in os.listdir(base):
            if "Gyan.FFmpeg" in entry:
                bin_path = os.path.join(base, entry, "ffmpeg", "bin")
                candidates.insert(0, bin_path)
    for p in candidates:
        if os.path.isdir(p):
            add_to_system_path(p)
            return


def step_miniconda(tmpdir):
    sid = "miniconda"
    update_step(sid, "running", "Checking…")
    log("\n━━ Miniconda", "step")
    if miniconda_exists():
        update_step(sid, "skipped", "Already installed")
        return True
    update_step(sid, "running", "Downloading Miniconda…")
    dest = os.path.join(tmpdir, DOWNLOADS["miniconda"]["filename"])
    if not download_file(DOWNLOADS["miniconda"]["url"], dest, sid):
        update_step(sid, "error", "Download failed")
        return False
    install_path = r"C:\Miniconda3"
    update_step(sid, "running", "Installing Miniconda…")
    ok, _ = run_cmd(
        f'"{dest}" /S /AddToPath=1 /RegisterPython=0 /D={install_path}',
        timeout=600,
    )
    for sub in ["", "Scripts", "condabin"]:
        add_to_system_path(os.path.join(install_path, sub) if sub else install_path)
    if ok:
        update_step(sid, "done", f"Installed → {install_path}")
    else:
        update_step(sid, "error", "Miniconda install failed")
    return ok


def _install_python(ver_tag, sid, label, tmpdir):
    update_step(sid, "running", "Checking…")
    log(f"\n━━ Python {label}", "step")
    py_ver = "3.10" if "310" in ver_tag else "3.11"
    if py_launcher_has(py_ver):
        update_step(sid, "skipped", f"Python {label} already installed")
        return True
    update_step(sid, "running", f"Downloading Python {label}…")
    dest = os.path.join(tmpdir, DOWNLOADS[ver_tag]["filename"])
    if not download_file(DOWNLOADS[ver_tag]["url"], dest, sid):
        update_step(sid, "error", "Download failed")
        return False
    update_step(sid, "running", f"Installing Python {label}…")
    ok, _ = run_cmd(
        f'"{dest}" /quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1',
        timeout=600,
    )
    if ok:
        update_step(sid, "done", f"Python {label} installed")
    else:
        update_step(sid, "error", f"Python {label} install failed")
    return ok


def step_vsbuild(tmpdir):
    sid = "vsbuild"
    update_step(sid, "running", "Checking…")
    log("\n━━ VS Build Tools 2022", "step")
    if vsbuild_exists():
        update_step(sid, "skipped", "Already installed")
        return True
    update_step(sid, "running", "Downloading VS Build Tools…")
    dest = os.path.join(tmpdir, DOWNLOADS["vsbuild"]["filename"])
    if not download_file(DOWNLOADS["vsbuild"]["url"], dest, sid):
        update_step(sid, "error", "Download failed")
        return False
    update_step(sid, "running", "Installing VS Build Tools (10–20 min)…")
    add_flags = " ".join(f"--add {c}" for c in VS_COMPONENTS)
    cmd = (
        f'"{dest}" --quiet --wait --norestart --nocache '
        f'--installPath "C:\\BuildTools" {add_flags}'
    )
    ok, _ = run_cmd(cmd, timeout=2400)
    # VS installer may return non-zero even when it succeeds (e.g. reboot pending)
    if not ok and vsbuild_exists():
        ok = True
    if ok:
        update_step(sid, "done", "VS Build Tools 2022 installed")
    else:
        update_step(sid, "error", "VS Build Tools install failed")
    return ok


def step_clone():
    sid = "clone"
    update_step(sid, "running", "Checking…")
    log("\n━━ Clone Repository (HuggingFace)", "step")

    if os.path.isdir(os.path.join(CLONE_DIR, ".git")):
        update_step(sid, "skipped", f"Already cloned at {CLONE_DIR}")
        return True

    # git-lfs is required for HuggingFace repos that store large model files
    log("  Ensuring git-lfs is initialised…", "info")
    run_cmd("git lfs install", timeout=30)

    update_step(sid, "running", f"Cloning branch '{REPO_BRANCH}'…")
    log(f"  Source: {REPO_URL}", "info")
    log(f"  Branch: {REPO_BRANCH}", "info")
    log(f"  Dest:   {CLONE_DIR}", "info")

    ok, _ = run_cmd(
        f'git clone --branch "{REPO_BRANCH}" "{REPO_URL}" "{CLONE_DIR}"',
        timeout=1800,   # large HF repos with LFS blobs can take a while
    )
    if ok:
        update_step(sid, "done", f"Cloned → {CLONE_DIR}")
    else:
        update_step(sid, "error", "Clone failed — check log")
    return ok


def step_setup():
    sid = "setup"
    update_step(sid, "running", "Checking…")
    log("\n━━ Setup Conda Environment", "step")

    ps_script = os.path.join(CLONE_DIR, "setup_windows.ps1")

    if not os.path.isdir(CLONE_DIR):
        log(f"  {CLONE_DIR} does not exist — clone step must have failed", "err")
        update_step(sid, "error", "Clone directory missing")
        return False

    if not os.path.isfile(ps_script):
        log(f"  setup_windows.ps1 not found in {CLONE_DIR}", "err")
        update_step(sid, "error", "setup_windows.ps1 not found")
        return False

    update_step(sid, "running", "Running setup_windows.ps1 (10–30 min)…")
    log("  This step creates the conda environment and installs all ML packages.", "info")
    log("  The log will stream here as it progresses.", "info")

    # Run the PowerShell script from inside the clone directory
    ok, _ = run_cmd(
        f'powershell -ExecutionPolicy Bypass -File "{ps_script}"',
        timeout=7200,   # conda env + pip installs for ML stack can be very slow
        cwd=CLONE_DIR,
    )
    if ok:
        update_step(sid, "done", "Conda environment ready")
    else:
        update_step(sid, "error", "setup_windows.ps1 exited with errors")
    return ok


def step_path_env():
    sid = "pathenv"
    update_step(sid, "running", "Updating PATH…")
    log("\n━━ Update System PATH", "step")
    extras = [
        r"C:\Program Files\Git\cmd",
        r"C:\Program Files\Git\bin",
        r"C:\Miniconda3",
        r"C:\Miniconda3\Scripts",
        r"C:\Miniconda3\condabin",
        r"C:\BuildTools\MSBuild\Current\Bin",
    ]
    for p in extras:
        if os.path.isdir(p):
            add_to_system_path(p)
    broadcast_env_change()
    update_step(sid, "done", "System PATH updated")
    return True

# ─── Installer thread ──────────────────────────────────────────────────────────

def run_installer():
    errors  = []
    tmpdir  = tempfile.mkdtemp(prefix="moodplay_inst_")
    log(f"Temp dir: {tmpdir}", "info")

    sequence = [
        ("git",      lambda: step_git()),
        ("ffmpeg",   lambda: step_ffmpeg()),
        ("miniconda",lambda: step_miniconda(tmpdir)),
        ("py310",    lambda: _install_python("py310", "py310", "3.10.9", tmpdir)),
        ("py311",    lambda: _install_python("py311", "py311", "3.11.9", tmpdir)),
        ("vsbuild",  lambda: step_vsbuild(tmpdir)),
        ("clone",    lambda: step_clone()),
        ("setup",    lambda: step_setup()),
        ("pathenv",  lambda: step_path_env()),
    ]

    for sid, fn in sequence:
        try:
            ok = fn()
            if not ok:
                errors.append(sid)
        except Exception as exc:
            log(f"  Unhandled error in [{sid}]: {exc}", "err")
            update_step(sid, "error", str(exc)[:70])
            errors.append(sid)

    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass

    log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")
    if errors:
        log(f"Completed with errors in: {', '.join(errors)}", "err")
    else:
        log("All steps completed successfully.", "ok")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")

    if _window:
        _window.evaluate_js(f'onComplete({"true" if not errors else "false"})')

# ─── pywebview API class ───────────────────────────────────────────────────────

class InstallerApi:
    def start_install(self):
        t = threading.Thread(target=run_installer, daemon=True)
        t.start()

    def close_window(self):
        if _window:
            _window.destroy()

# ─── Entry point ───────────────────────────────────────────────────────────────

def main():
    global _window

    if not is_admin():
        elevate()
        return

    api     = InstallerApi()
    _window = webview.create_window(
        title="MoodPlay Installer",
        html=HTML,
        js_api=api,
        width=1020,
        height=680,
        resizable=True,
        min_size=(780, 500),
        background_color="#0d0d1a",
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
