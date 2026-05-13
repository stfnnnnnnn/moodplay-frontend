#!/usr/bin/env python3
"""
MoodPlay Installer
Instance-Guided Semantic Video Colorization System
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
import time
import socket
import json

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
MIN_FREE_GB = 25

# Prevent git from hanging silently on credential prompts
os.environ["GIT_TERMINAL_PROMPT"] = "0"

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

# CUDA Toolkit — only 12.9 (driver CUDA ≥ 12.8) or 12.4 (driver CUDA ≥ 12.4)
# Network installers: ~35 MB stub, downloads components from NVIDIA on-demand
CUDA_VERSIONS = {
    "12.9": {
        "url":       "https://developer.download.nvidia.com/compute/cuda/12.9.0/network_installers/cuda_12.9.0_windows_network.exe",
        "filename":  "cuda_12.9.0_windows_network.exe",
        "min_driver": 12.8,   # driver must report CUDA Version >= 12.8
        "nvcc":      r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.9\bin\nvcc.exe",
        "bin":       r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.9\bin",
    },
    "12.4": {
        "url":       "https://developer.download.nvidia.com/compute/cuda/12.4.0/network_installers/cuda_12.4.0_windows_network.exe",
        "filename":  "cuda_12.4.0_windows_network.exe",
        "min_driver": 12.4,   # driver must report CUDA Version >= 12.4
        "nvcc":      r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin\nvcc.exe",
        "bin":       r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin",
    },
}
# Components installed silently (no display driver re-install, no samples)
CUDA_COMPONENTS = [
    "nvcc", "compilers", "cudart", "cublas_dev",
    "curand_dev", "visual_studio_integration",
]

# ─── UAC Elevation ─────────────────────────────────────────────────────────────

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def elevate():
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
    --pink:       #D4608A;
    --pink-soft:  #F5C6DA;
    --pink-glow:  rgba(212,96,138,0.35);
    --blue:       #3A65B8;
    --blue-soft:  #BAD0F5;
    --blue-glow:  rgba(58,101,184,0.30);
    --purple:     #6B4E9A;
    --surface:    rgba(255,255,255,0.92);
    --surface2:   rgba(255,255,255,0.98);
    --glass:      rgba(255,255,255,0.78);
    --text-1:     #12132A;
    --text-2:     #3E4C62;
    --text-3:     #68788F;
    --border:     rgba(0,0,0,0.11);
    --shadow-sm:  0 1px 5px rgba(0,0,0,0.09);
    --shadow-md:  0 4px 20px rgba(0,0,0,0.13);
    --error:      #C81D1D;
    --warn-clr:   #B85C00;
    --ok-clr:     #0A7A52;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; overflow: hidden; }

  @keyframes moodGradient {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }
  body {
    background: linear-gradient(-45deg, #F5C8DD, #E5D0FF, #C4DCFF, #FBDFF0, #C8DFFF);
    background-size: 400% 400%;
    animation: moodGradient 14s ease infinite;
    color: var(--text-1);
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 13px;
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  /* ── Header ── */
  .hdr {
    background: var(--surface);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
    padding: 13px 22px 11px;
    flex-shrink: 0;
    box-shadow: var(--shadow-sm);
  }
  .hdr-top { display: flex; align-items: center; gap: 12px; margin-bottom: 11px; }
  .logo {
    width: 38px; height: 38px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
  }
  .logo svg { width: 36px; height: 36px; }
  .hdr-info { flex: 1; }
  .hdr-title {
    font-size: 16px; font-weight: 800; letter-spacing: -0.4px; line-height: 1;
  }
  .hdr-title .mood { color: var(--pink); }
  .hdr-title .play { color: var(--blue); }
  .hdr-title .rest { color: var(--text-1); }
  .hdr-sub { font-size: 11px; color: var(--text-2); margin-top: 3px; }
  .hdr-chips { display: flex; align-items: center; gap: 7px; margin-left: auto; flex-shrink: 0; }
  .chip {
    font-size: 11px; color: var(--text-2);
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 100px; padding: 3px 11px; white-space: nowrap;
    box-shadow: var(--shadow-sm);
  }
  .chip b { font-weight: 700; }
  .prog-wrap { display: flex; align-items: center; gap: 10px; }
  .prog-track {
    flex: 1; height: 5px; background: rgba(0,0,0,0.11); border-radius: 100px; overflow: hidden;
  }
  .prog-fill {
    height: 100%; width: 0%;
    background: linear-gradient(90deg, #a8d3fb, #c9b8da, #eab2bc);
    border-radius: 100px; transition: width 0.4s ease;
    box-shadow: 0 0 8px var(--pink-glow);
  }
  .prog-lbl { font-size: 11px; color: var(--text-2); white-space: nowrap; min-width: 44px; text-align: right; }

  /* ── Main layout ── */
  .main { display: flex; flex: 1; overflow: hidden; }

  /* Steps panel */
  .steps-pane {
    width: 300px; flex-shrink: 0;
    background: var(--surface);
    backdrop-filter: blur(12px);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 6px 7px 12px;
  }
  .steps-pane::-webkit-scrollbar { width: 3px; }
  .steps-pane::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.10); border-radius: 2px; }
  .sec-lbl {
    font-size: 9.5px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.2px; color: #5B6E8E;
    padding: 10px 10px 4px;
  }
  .sec-divider { height: 1px; background: rgba(0,0,0,0.13); margin: 4px 10px 2px; }
  .step {
    display: flex; align-items: center; gap: 10px;
    padding: 7px 10px; border-radius: 9px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
  }
  .step.running { background: rgba(58,101,184,0.10);  border-color: rgba(58,101,184,0.28); }
  .step.done    { background: rgba(212,96,138,0.10);  border-color: rgba(212,96,138,0.30); }
  .step.error   { background: rgba(200,29,29,0.09);   border-color: rgba(200,29,29,0.28); }
  .step.skipped { background: rgba(184,92,0,0.08);    border-color: rgba(184,92,0,0.28); }
  .step.warn    { background: rgba(184,92,0,0.08);    border-color: rgba(184,92,0,0.28); }
  .step-ico {
    width: 24px; height: 24px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; font-size: 11px; font-weight: 700;
    border: 2px solid transparent;
  }
  .step.pending .step-ico { background: rgba(0,0,0,0.04); color: var(--text-3); border-color: #E5E7EB; }
  .step.running .step-ico { background: #fff; color: var(--blue); border-color: var(--blue); box-shadow: 0 0 0 4px var(--blue-glow); }
  .step.done    .step-ico { background: var(--pink); color: #fff; border-color: var(--pink); box-shadow: 0 2px 8px var(--pink-glow); }
  .step.error   .step-ico { background: var(--error); color: #fff; border-color: var(--error); }
  .step.skipped .step-ico { background: rgba(217,119,6,0.12); color: var(--warn-clr); border-color: rgba(217,119,6,0.35); }
  .step.warn    .step-ico { background: rgba(217,119,6,0.12); color: var(--warn-clr); border-color: rgba(217,119,6,0.35); }
  .step-txt { flex: 1; min-width: 0; }
  .step-name {
    font-weight: 600; font-size: 12px; color: var(--text-1);
    display: flex; align-items: center; gap: 5px;
  }
  .step.pending .step-name { color: var(--text-2); }
  .step-badge {
    font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 4px;
    flex-shrink: 0; letter-spacing: 0.3px; display: none;
  }
  .step-badge.ok   { background: rgba(212,96,138,0.18);  color: var(--pink); }
  .step-badge.err  { background: rgba(200,29,29,0.13);   color: var(--error); }
  .step-badge.skip { background: rgba(184,92,0,0.14);    color: var(--warn-clr); }
  .step-desc {
    font-size: 10.5px; color: #5A6B80; margin-top: 1px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  @keyframes spin { to { transform: rotate(360deg); } }
  .spin {
    width: 11px; height: 11px;
    border: 2px solid var(--blue-soft);
    border-top-color: var(--blue);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }

  /* Log panel */
  .log-pane {
    flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 12px 15px;
  }
  .log-hdr {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 8px; flex-shrink: 0;
  }
  .log-hdr-lbl {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #5B6E8E;
  }
  .log-actions { display: flex; gap: 5px; }
  .log-btn {
    font-size: 10px; padding: 3px 9px; border-radius: 6px;
    background: var(--surface2); color: var(--text-2);
    cursor: pointer; border: 1px solid var(--border);
    transition: all 0.15s; box-shadow: var(--shadow-sm);
  }
  .log-btn:hover { background: #fff; color: var(--text-1); border-color: rgba(0,0,0,0.12); }
  .log-body {
    flex: 1; overflow-y: auto;
    background: rgba(245,248,255,0.95);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 11px 14px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 11.5px; line-height: 1.75;
    box-shadow: var(--shadow-sm);
  }
  .log-body::-webkit-scrollbar { width: 3px; }
  .log-body::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.10); border-radius: 2px; }
  .le       { display: block; }
  .le.info  { color: #8A97AB; }
  .le.msg   { color: #304055; }
  .le.ok    { color: var(--ok-clr); }
  .le.err   { color: var(--error); }
  .le.warn  { color: var(--warn-clr); }
  .le.step  { color: var(--pink); font-weight: 700; }
  .le.skip  { color: var(--warn-clr); }
  .le.dl    { color: var(--blue); }
  .le.check { color: var(--blue); }
  .ts { color: #A8B8CC; margin-right: 6px; font-size: 10px; user-select: none; }

  /* Install location bar */
  .loc-bar {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 20px; border-top: 1px solid var(--border);
    background: var(--surface2); flex-shrink: 0;
  }
  .loc-lbl {
    font-size: 11px; font-weight: 600; color: #5B6E8E;
    white-space: nowrap; flex-shrink: 0;
  }
  .loc-input {
    flex: 1; font-size: 11px; font-family: 'Consolas', monospace;
    padding: 4px 9px; border-radius: 6px;
    border: 1px solid var(--border);
    background: rgba(245,248,255,0.9); color: var(--text-1);
    outline: none; min-width: 0;
  }
  .loc-input:focus { border-color: var(--blue); box-shadow: 0 0 0 2px var(--blue-glow); }
  .loc-input:disabled { color: var(--text-3); background: rgba(240,242,246,0.9); cursor: not-allowed; }
  .loc-browse {
    font-size: 10.5px; padding: 4px 11px; border-radius: 6px;
    background: var(--surface2); color: var(--text-2);
    border: 1px solid var(--border); cursor: pointer;
    transition: all 0.15s; box-shadow: var(--shadow-sm); flex-shrink: 0;
  }
  .loc-browse:hover:not(:disabled) { background: #fff; color: var(--text-1); border-color: rgba(0,0,0,0.12); }
  .loc-browse:disabled { opacity: 0.5; cursor: not-allowed; }

  /* Footer */
  .footer {
    border-top: 1px solid var(--border);
    padding: 10px 20px;
    display: flex; align-items: center; justify-content: space-between;
    flex-shrink: 0;
    background: var(--surface);
    backdrop-filter: blur(12px);
    box-shadow: 0 -1px 0 var(--border);
  }
  .status { font-size: 12px; color: var(--text-2); }
  .status b { color: var(--text-1); font-weight: 700; }
  .btns { display: flex; gap: 8px; }
  .btn {
    padding: 7px 22px; border-radius: 8px; border: none;
    font-size: 12.5px; font-weight: 700; cursor: pointer;
    transition: all 0.2s ease; letter-spacing: 0.2px;
  }
  .btn-p {
    background: linear-gradient(135deg, var(--pink) 0%, #C96A8A 100%);
    color: #fff; box-shadow: 0 4px 16px var(--pink-glow);
  }
  .btn-p:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 22px var(--pink-glow); }
  .btn-p:disabled { opacity: 0.42; cursor: not-allowed; transform: none; box-shadow: none; }
  .btn-s {
    background: var(--surface2); color: var(--text-2);
    border: 1px solid var(--border); box-shadow: var(--shadow-sm);
  }
  .btn-s:hover:not(:disabled) { background: #fff; color: var(--text-1); }
  .btn-s:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-w {
    background: rgba(79,123,202,0.09); color: var(--blue);
    border: 1.5px solid rgba(79,123,202,0.28);
  }
  .btn-w:hover { background: rgba(79,123,202,0.16); border-color: var(--blue); }
  .btn-abort {
    background: rgba(200,29,29,0.08); color: var(--error);
    border: 1.5px solid rgba(200,29,29,0.25);
  }
  .btn-abort:hover:not(:disabled) { background: rgba(200,29,29,0.16); border-color: var(--error); }
  .btn-abort:disabled { opacity: 0.4; cursor: not-allowed; }

  /* Toast */
  .toast {
    position: fixed; bottom: 58px; right: 18px;
    background: rgba(255,255,255,0.96); border: 1px solid rgba(232,141,172,0.4); color: var(--pink);
    font-size: 11.5px; font-weight: 600; padding: 7px 16px; border-radius: 100px;
    opacity: 0; pointer-events: none; transition: opacity 0.25s;
    box-shadow: 0 4px 14px rgba(232,141,172,0.20);
  }
  .toast.show { opacity: 1; }
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-top">
    <div class="logo">
      <!-- MoodPlay logo mark (simplified, brand gradient) -->
      <svg viewBox="0 0 1500 1500" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="lg1" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#4F7BCA"/>
            <stop offset="1" stop-color="#E88DAC"/>
          </linearGradient>
          <clipPath id="cp1">
            <path d="M1265.4 6.4C1388.5 6.4 1488.3 106.2 1488.3 229.3V493.9C1488.3 579.7 1438.9 658 1361.5 695L1121.1 809.9 844.7 997.1 843.2 998.2 587.7 1145.7V1270.7C587.7 1393.8 488 1493.6 364.9 1493.6H222.9C99.8 1493.6 0 1393.8 0 1270.7V229.3C0 106.2 99.8 6.4 222.9 6.4ZM222.9 109.3C156.6 109.3 102.9 163 102.9 229.3V1270.7C102.9 1337 156.6 1390.7 222.9 1390.7H364.9C431.1 1390.7 484.9 1337 484.9 1270.7V541.9C484.9 431.3 609.1 366.1 700 429.1L1100.2 705.9 1317.1 602.2C1358.8 582.2 1385.4 540.1 1385.4 493.9V229.3C1385.4 163 1331.7 109.3 1265.4 109.3ZM641.5 513.7C618.8 497.9 587.7 514.2 587.7 541.9V1026.9L788.6 910.9 1004.4 764.7Z" clip-rule="evenodd"/>
          </clipPath>
          <clipPath id="cp2">
            <path d="M1499.1 1253.8C1499.1 1379.9 1400.9 1487.8 1272.9 1487.8H581.8L649 1421.8C673 1398.2 705.4 1385 739.1 1385H1272.9C1337.1 1385 1394.7 1329.3 1394.7 1253.8V835.5C1394.7 802.2 1407.6 770.2 1430.8 746.2L1498.8 675.8H1499.1Z" clip-rule="nonzero"/>
          </clipPath>
        </defs>
        <g clip-path="url(#cp1)"><rect width="1500" height="1500" fill="url(#lg1)"/></g>
        <g clip-path="url(#cp2)"><rect width="1500" height="1500" fill="url(#lg1)" opacity="0.72"/></g>
      </svg>
    </div>
    <div class="hdr-info">
      <div class="hdr-title">
        <span class="mood">Mood</span><span class="play">Play</span><span class="rest"> Installer</span>
      </div>
      <div class="hdr-sub">Instance-Guided Semantic Video Colorization System</div>
    </div>
    <div class="hdr-chips">
      <div class="chip">Disk C: <b id="diskVal">—</b></div>
      <div class="chip">Network <b id="netVal">—</b></div>
    </div>
  </div>
  <div class="prog-wrap">
    <div class="prog-track"><div class="prog-fill" id="gp"></div></div>
    <div class="prog-lbl" id="progLbl">0 / 0</div>
  </div>
</div>

<div class="main">
  <div class="steps-pane" id="stepsList"></div>
  <div class="log-pane">
    <div class="log-hdr">
      <div class="log-hdr-lbl">Installation Log</div>
      <div class="log-actions">
        <button class="log-btn" onclick="clearLog()">Clear</button>
        <button class="log-btn" onclick="copyLog()">Copy log</button>
      </div>
    </div>
    <div class="log-body" id="logBody"></div>
  </div>
</div>

<div class="loc-bar">
  <span class="loc-lbl">Install to:</span>
  <input class="loc-input" id="installPath" type="text" value="C:\\moodplay" spellcheck="false"/>
  <button class="loc-browse" id="btnBrowse" onclick="browseFolder()">Browse…</button>
</div>

<div class="footer">
  <div class="status" id="statusTxt">Ready to install. Click <b>Start Install</b> to begin.</div>
  <div class="btns">
    <button class="btn btn-s" onclick="closeWin()">Exit</button>
    <button class="btn btn-w" id="btnRetry" onclick="doRetry()" style="display:none">Retry Failed</button>
    <button class="btn btn-abort" id="btnAbort" onclick="doAbort()" style="display:none">Abort</button>
    <button class="btn btn-p" id="btnStart" onclick="doInstall()">Start Install</button>
  </div>
</div>

<div class="toast" id="toast">✓ Copied to clipboard</div>

<script>
const STEP_GROUPS = [
  { label: "Pre-flight",    ids: ["preflight"] },
  { label: "Prerequisites", ids: ["git","ffmpeg","miniconda","py310","py311","vsbuild","cuda"] },
  { label: "Repository",   ids: ["clone"] },
  { label: "Environment",  ids: ["setup"] },
  { label: "Finalize",     ids: ["pathenv","verify"] },
];
const STEP_META = {
  preflight: { name: "Pre-flight Checks",        desc: "Internet · disk · OS" },
  git:       { name: "Git",                       desc: "Version control system" },
  ffmpeg:    { name: "FFmpeg (Gyan)",             desc: "Video processing engine" },
  miniconda: { name: "Miniconda",                 desc: "Conda package manager" },
  py310:     { name: "Python 3.10.9",             desc: "Primary ML runtime" },
  py311:     { name: "Python 3.11.9",             desc: "Secondary runtime" },
  vsbuild:   { name: "VS Build Tools 2022",       desc: "C++ compiler + MSVC" },
  cuda:      { name: "NVIDIA CUDA Toolkit",       desc: "12.9 (driver ≥ 12.8) or 12.4 (driver ≥ 12.4)" },
  clone:     { name: "Clone Repository",          desc: "HuggingFace → C:\\moodplay" },
  setup:     { name: "Setup Conda Environments",  desc: "ML stack install (10–30 min)" },
  pathenv:   { name: "Update System PATH",        desc: "Register tools in PATH" },
  verify:    { name: "Verify Installation",       desc: "Confirm all tools work" },
};
const ALL_IDS    = STEP_GROUPS.flatMap(g => g.ids);
const TOTAL      = ALL_IDS.length;
const ICONS      = { pending:"○", done:"✓", error:"✗", skipped:"→", warn:"!" };

let doneCount  = 0;
let stepStates = {};   // tracks current terminal state per step id

function renderSteps() {
  let html = "";
  for (const g of STEP_GROUPS) {
    html += `<div class="sec-lbl">${g.label}</div>`;
    for (const id of g.ids) {
      const m = STEP_META[id];
      html += `
        <div class="step pending" id="step_${id}">
          <div class="step-ico" id="ico_${id}">○</div>
          <div class="step-txt">
            <div class="step-name">
              ${m.name}
              <span class="step-badge" id="badge_${id}"></span>
            </div>
            <div class="step-desc" id="dsc_${id}">${m.desc}</div>
          </div>
        </div>`;
    }
    html += `<div class="sec-divider"></div>`;
  }
  document.getElementById("stepsList").innerHTML = html;
  document.getElementById("progLbl").textContent = `0 / ${TOTAL}`;
}

function ts() { return new Date().toTimeString().slice(0,8); }

function log(msg, type) {
  const lb = document.getElementById("logBody");
  const el = document.createElement("span");
  el.className = "le " + (type || "msg");
  el.innerHTML = `<span class="ts">${ts()}</span>${msg}`;
  lb.appendChild(el);
  lb.appendChild(document.createElement("br"));
  lb.scrollTop = lb.scrollHeight;
}

const TERMINAL = new Set(["done","error","skipped","warn"]);

function updateStep(id, status, msg) {
  const el    = document.getElementById("step_" + id);
  const ico   = document.getElementById("ico_"  + id);
  const dsc   = document.getElementById("dsc_"  + id);
  const badge = document.getElementById("badge_" + id);
  if (!el) return;

  // Handle retry: if going from terminal → running, undo the count
  const prev = stepStates[id];
  if (TERMINAL.has(prev) && status === "running") {
    doneCount = Math.max(0, doneCount - 1);
    delete stepStates[id];
  }

  el.className = "step " + status;
  if (status === "running") {
    ico.innerHTML = '<div class="spin"></div>';
    if (badge) badge.style.display = "none";
  } else {
    ico.textContent = ICONS[status] || "?";
  }
  if (msg) dsc.textContent = msg;

  if (TERMINAL.has(status) && !stepStates[id]) {
    stepStates[id] = status;
    doneCount++;
    document.getElementById("gp").style.width   = Math.round(doneCount / TOTAL * 100) + "%";
    document.getElementById("progLbl").textContent = `${doneCount} / ${TOTAL}`;

    if (badge) {
      const lbl = status === "done" ? "OK" : status === "error" ? "ERR" : status === "warn" ? "WARN" : "SKIP";
      const cls = status === "done" ? "ok"  : status === "error" ? "err" : "skip";
      badge.textContent    = lbl;
      badge.className      = "step-badge " + cls;
      badge.style.display  = "inline";
    }
    const t = status === "done" ? "ok" : status === "error" ? "err" : "skip";
    const p = status === "done" ? "✓"  : status === "error" ? "✗"  : "→";
    log(p + " " + (msg || id), t);
  }
}

function setChip(valId, text, color) {
  const el = document.getElementById(valId);
  if (el) { el.textContent = text; el.style.color = color || ""; }
}

function logMessage(msg, type) { log(msg, type || "msg"); }
function setStatus(html)       { document.getElementById("statusTxt").innerHTML = html; }

function _finishInstall() {
  document.getElementById("btnAbort").style.display  = "none";
  document.getElementById("installPath").disabled    = false;
  document.getElementById("btnBrowse").disabled      = false;
}

function onComplete(success) {
  const b = document.getElementById("btnStart");
  b.disabled    = false;
  b.textContent = "Done";
  b.classList.replace("btn-p", "btn-s");
  if (success) {
    document.getElementById("gp").style.width      = "100%";
    document.getElementById("progLbl").textContent = `${TOTAL} / ${TOTAL}`;
    setStatus('<span style="color:#E88DAC;font-weight:700">✓ Installation complete!</span> <span style="color:#4F7BCA;font-weight:600">MoodPlay</span> is ready to use.');
  } else {
    setStatus('<span style="color:#DC2626;font-weight:700">Completed with errors.</span> Check the log, then click <b>Retry Failed</b>.');
    document.getElementById("btnRetry").style.display = "";
  }
  _finishInstall();
}

function onAborted() {
  const b = document.getElementById("btnStart");
  b.disabled    = false;
  b.textContent = "Start Install";
  b.classList.replace("btn-s", "btn-p");
  setStatus('<span style="color:#B85C00;font-weight:700">Installation aborted.</span> You can restart or exit.');
  _finishInstall();
}

function doAbort() {
  const btn = document.getElementById("btnAbort");
  btn.disabled    = true;
  btn.textContent = "Aborting…";
  setStatus("Aborting — waiting for current operation to stop…");
  window.pywebview.api.abort_install();
}

function browseFolder() {
  window.pywebview.api.browse_folder().then(p => {
    if (p) {
      document.getElementById("installPath").value = p;
      const dsc = document.getElementById("dsc_clone");
      if (dsc) dsc.textContent = "HuggingFace → " + p;
    }
  });
}

function doInstall() {
  const installPath = document.getElementById("installPath").value.trim() || "C:\\moodplay";

  // Reset all steps
  doneCount = 0; stepStates = {};
  for (const id of ALL_IDS) {
    const el = document.getElementById("step_" + id);
    const ico = document.getElementById("ico_" + id);
    const dsc = document.getElementById("dsc_" + id);
    const badge = document.getElementById("badge_" + id);
    if (!el) continue;
    el.className = "step pending";
    ico.textContent = "○";
    if (dsc) dsc.textContent = STEP_META[id].desc;
    if (badge) { badge.style.display = "none"; badge.textContent = ""; }
  }
  // Update clone desc to show the chosen path
  const cloneDsc = document.getElementById("dsc_clone");
  if (cloneDsc) cloneDsc.textContent = "HuggingFace → " + installPath;

  document.getElementById("gp").style.width = "0%";
  document.getElementById("progLbl").textContent = `0 / ${TOTAL}`;
  document.getElementById("btnRetry").style.display = "none";

  document.getElementById("btnStart").disabled    = true;
  document.getElementById("btnStart").textContent = "Installing…";
  document.getElementById("btnAbort").style.display  = "";
  document.getElementById("btnAbort").disabled       = false;
  document.getElementById("btnAbort").textContent    = "Abort";
  document.getElementById("installPath").disabled = true;
  document.getElementById("btnBrowse").disabled   = true;
  setStatus("Installation in progress…");
  log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info");
  log("MoodPlay Installer — starting installation sequence", "step");
  log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info");
  window.pywebview.api.start_install(installPath);
}

function doRetry() {
  document.getElementById("btnStart").disabled    = true;
  document.getElementById("btnRetry").style.display = "none";
  setStatus("Retrying failed steps…");
  log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info");
  log("Retrying failed steps…", "step");
  log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info");
  window.pywebview.api.retry_failed();
}

function clearLog() { document.getElementById("logBody").innerHTML = ""; }

function showToast() {
  const t = document.getElementById("toast");
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2000);
}

function fallbackCopy(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.cssText = "position:fixed;top:0;left:0;opacity:0;pointer-events:none";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try { document.execCommand("copy"); showToast(); } catch (_) {}
  document.body.removeChild(ta);
}

function copyLog() {
  const text = document.getElementById("logBody").innerText;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(showToast).catch(() => fallbackCopy(text));
  } else {
    fallbackCopy(text);
  }
}

function closeWin() { window.pywebview.api.close_window(); }

renderSteps();
</script>
</body>
</html>"""

# ─── Global state ──────────────────────────────────────────────────────────────

_window        = None
_failed_steps  = []
_abort_flag    = threading.Event()
_proc_lock     = threading.Lock()
_current_proc: "subprocess.Popen | None" = None


def _kill_current_proc():
    with _proc_lock:
        p = _current_proc
    if p:
        try:
            p.kill()
        except Exception:
            pass

# ─── UI helpers ────────────────────────────────────────────────────────────────

def _esc(s):
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

def set_chip(val_id, text, color=""):
    if _window:
        _window.evaluate_js(f'setChip("{val_id}", "{_esc(text)}", "{color}")')

# ─── Shell helpers ─────────────────────────────────────────────────────────────

def run_cmd(cmd, timeout=3600, cwd=None):
    """Run a command, stream last output lines to UI, return (ok, stdout)."""
    global _current_proc
    if _abort_flag.is_set():
        return False, ""
    log(f"  $ {cmd[:130]}{'…' if len(cmd) > 130 else ''}", "info")
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace", cwd=cwd,
        )
        with _proc_lock:
            _current_proc = proc
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            log(f"  TIMEOUT after {timeout}s", "err")
            return False, ""
        finally:
            with _proc_lock:
                if _current_proc is proc:
                    _current_proc = None
        if _abort_flag.is_set():
            return False, ""
        for line in stdout.strip().splitlines()[-5:]:
            line = line.strip()
            if line:
                log(f"    {line}", "info")
        if proc.returncode != 0:
            for line in stderr.strip().splitlines()[-3:]:
                line = line.strip()
                if line:
                    log(f"    !! {line}", "warn")
        return proc.returncode == 0, stdout
    except Exception as e:
        log(f"  Exception: {e}", "err")
        return False, ""

def _probe(cmd, timeout=12):
    """Silent quick check — does not log. Returns (ok, stdout+stderr)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, errors="replace",
        )
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception:
        return False, ""

def download_file(url, dest, step_id):
    """Download with % progress to UI."""
    last = [-1]

    def hook(count, block_size, total):
        if _abort_flag.is_set():
            raise Exception("Aborted")
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
        if _abort_flag.is_set():
            log("  Download aborted.", "warn")
        else:
            log(f"  Download failed: {e}", "err")
        return False

# ─── Detection helpers ─────────────────────────────────────────────────────────

def winget_has(pkg_id):
    ok, out = _probe(
        f'winget list --id "{pkg_id}" -e --accept-source-agreements 2>nul',
        timeout=45,
    )
    return ok and pkg_id.lower() in out.lower()

def git_exists():
    """Check git binary is actually usable. Returns (bool, version_str)."""
    ok, out = _probe("git --version")
    if ok and "git version" in out.lower():
        return True, out.splitlines()[0].strip()
    for p in [r"C:\Program Files\Git\cmd\git.exe", r"C:\Program Files\Git\bin\git.exe"]:
        if os.path.isfile(p):
            return True, "git (found at standard path)"
    if winget_has("Git.Git"):
        return True, "git (registered in winget)"
    return False, ""

def ffmpeg_exists():
    """Returns (bool, version_str)."""
    ok, out = _probe("ffmpeg -version")
    if ok and "ffmpeg version" in out.lower():
        first = out.splitlines()[0].strip()
        return True, first[:70]
    for p in [r"C:\Program Files\ffmpeg\bin\ffmpeg.exe", r"C:\ffmpeg\bin\ffmpeg.exe"]:
        if os.path.isfile(p):
            return True, "ffmpeg (found at standard path)"
    if winget_has("Gyan.FFmpeg"):
        return True, "ffmpeg (registered in winget)"
    return False, ""

def miniconda_exists():
    """Returns (bool, version_str)."""
    ok, out = _probe("conda --version")
    if ok and "conda" in out.lower():
        return True, out.strip().splitlines()[0]
    candidates = [
        os.path.expandvars(r"%USERPROFILE%\Miniconda3"),
        os.path.expandvars(r"%USERPROFILE%\miniconda3"),
        r"C:\Miniconda3", r"C:\miniconda3",
        r"C:\ProgramData\Miniconda3", r"C:\ProgramData\miniconda3",
        os.path.expandvars(r"%USERPROFILE%\Anaconda3"),
        r"C:\Anaconda3",
    ]
    for base in candidates:
        if os.path.isfile(os.path.join(base, "Scripts", "conda.exe")):
            return True, f"conda (at {base})"
    return False, ""

def python_exists(ver):
    """Check Python version (e.g. '3.10'). Returns (bool, version_str)."""
    ok, out = _probe(f"py -{ver} --version")
    if ok and "python" in out.lower():
        return True, out.strip().splitlines()[0]
    ok, out = _probe(f"python{ver.replace('.', '')} --version")
    if ok and "python" in out.lower():
        return True, out.strip()
    ver_nodot = ver.replace(".", "")
    for p in [
        rf"C:\Python{ver_nodot}\python.exe",
        os.path.expandvars(rf"%LOCALAPPDATA%\Programs\Python\Python{ver_nodot}\python.exe"),
    ]:
        if os.path.isfile(p):
            return True, f"Python {ver} (at {os.path.dirname(p)})"
    return False, ""

def vsbuild_exists():
    """Returns (bool, desc_str)."""
    vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if os.path.isfile(vswhere):
        ok, out = _probe(
            f'"{vswhere}" -products * '
            '-requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json',
            timeout=30,
        )
        if ok and out.strip() not in ("", "[]"):
            return True, "VS Build Tools 2022 (verified via vswhere)"
    for base in [
        r"C:\BuildTools\VC\Tools\MSVC",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC",
        r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC",
    ]:
        if os.path.isdir(base):
            return True, f"VS Build Tools (MSVC at {base})"
    return False, ""

def nvidia_gpu_present():
    """True if an NVIDIA GPU is detected via nvidia-smi."""
    ok, out = _probe("nvidia-smi -L", timeout=20)
    return ok and "GPU" in out

def get_driver_cuda_ver():
    """Parse max CUDA version supported by the installed driver. Returns float or None."""
    import re
    ok, out = _probe("nvidia-smi", timeout=20)
    if ok:
        m = re.search(r"CUDA Version:\s*([0-9]+\.[0-9]+)", out)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                pass
    return None

def cuda_toolkit_exists():
    """True if nvcc is usable. Returns (bool, version_str)."""
    ok, out = _probe("nvcc --version", timeout=15)
    if ok and "release" in out.lower():
        for line in out.splitlines():
            if "release" in line.lower():
                return True, line.strip()
        return True, "CUDA Toolkit (nvcc found)"
    # Check standard install paths for both allowed versions
    for ver_key, cfg in CUDA_VERSIONS.items():
        if os.path.isfile(cfg["nvcc"]):
            return True, f"CUDA Toolkit {ver_key} (at standard path)"
    return False, ""

def pick_cuda_version(driver_cuda_ver):
    """Return '12.9' or '12.4' based on driver CUDA version, or None if unsupported."""
    if driver_cuda_ver is None:
        return None
    for ver_key in ["12.9", "12.4"]:       # prefer newest first
        if driver_cuda_ver >= CUDA_VERSIONS[ver_key]["min_driver"]:
            return ver_key
    return None

def conda_env_exists(env_name):
    """True if the named conda environment directory exists."""
    # Try 'conda env list --json' via any reachable conda
    for conda_exe in ["conda", r"C:\Miniconda3\Scripts\conda.exe",
                      r"C:\ProgramData\Miniconda3\Scripts\conda.exe",
                      os.path.expandvars(r"%USERPROFILE%\Miniconda3\Scripts\conda.exe")]:
        ok, out = _probe(f'"{conda_exe}" env list --json', timeout=30)
        if ok:
            try:
                envs = json.loads(out).get("envs", [])
                if any(os.path.basename(e) == env_name for e in envs):
                    return True
                break
            except Exception:
                break
    # Fallback: check env directories directly
    env_bases = [
        r"C:\Miniconda3\envs",
        r"C:\ProgramData\Miniconda3\envs",
        os.path.expandvars(r"%USERPROFILE%\Miniconda3\envs"),
        os.path.expandvars(r"%USERPROFILE%\miniconda3\envs"),
    ]
    return any(os.path.isdir(os.path.join(b, env_name)) for b in env_bases)

def check_internet():
    """Probe pypi.org:443. Returns (ok, msg)."""
    for host, port in [("pypi.org", 443), ("repo.anaconda.com", 443), ("8.8.8.8", 53)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(7)
            s.connect((host, port))
            s.close()
            return True, "Online"
        except Exception:
            pass
    return False, "No internet detected"

def check_disk_space(path=r"C:\\", min_gb=25):
    """Returns (ok, free_gb, msg)."""
    try:
        usage   = shutil.disk_usage(path)
        free_gb = usage.free / (1024 ** 3)
        return free_gb >= min_gb, free_gb, f"{free_gb:.1f} GB free"
    except Exception as e:
        return False, 0.0, f"Error: {e}"

# ─── PATH registry helper ──────────────────────────────────────────────────────

def add_to_system_path(new_path):
    if not new_path or not os.path.isdir(new_path):
        return
    # Update current process PATH immediately
    cur = os.environ.get("PATH", "")
    if new_path not in cur:
        os.environ["PATH"] = cur + ";" + new_path
    if winreg is None:
        log(f"  winreg unavailable — cannot persist {new_path}", "warn")
        return
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            0, winreg.KEY_READ | winreg.KEY_WRITE,
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
    try:
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None
        )
    except Exception:
        pass

# ─── Step implementations ──────────────────────────────────────────────────────

def step_preflight():
    sid = "preflight"
    update_step(sid, "running", "Checking system requirements…")
    log("\n━━ Pre-flight Checks", "step")
    issues = []

    # Windows version
    ok, out = _probe("ver")
    win_ver = out.splitlines()[0].strip() if ok and out.strip() else "Windows (version unknown)"
    log(f"  OS: {win_ver}", "check")

    # Internet
    log("  Checking internet connectivity…", "info")
    net_ok, net_msg = check_internet()
    if net_ok:
        log(f"  ✓ Internet: {net_msg}", "ok")
        set_chip("netVal", "Online",  "#10b981")
    else:
        log(f"  ✗ Internet: {net_msg} — downloads will fail", "err")
        set_chip("netVal", "Offline", "#ef4444")
        issues.append("No internet")

    # Disk space
    log(f"  Checking disk space (need ≥ {MIN_FREE_GB} GB free on C:)…", "info")
    disk_ok, free_gb, disk_msg = check_disk_space(r"C:\\", MIN_FREE_GB)
    if disk_ok:
        log(f"  ✓ Disk: {disk_msg}", "ok")
        set_chip("diskVal", disk_msg, "#10b981")
    else:
        log(f"  ⚠ Disk: {disk_msg} — installation may run out of space", "warn")
        set_chip("diskVal", disk_msg, "#f59e0b")
        # Disk low is a warning, not a hard block

    # Scan already-installed tools and log their status
    log("  Scanning pre-installed tools…", "info")
    for label, fn in [
        ("Git",         git_exists),
        ("FFmpeg",      ffmpeg_exists),
        ("Conda",       miniconda_exists),
        ("VS Build",    vsbuild_exists),
    ]:
        found, ver = fn()
        if found:
            log(f"  ✓ {label}: {ver}", "check")
    for pyver in ["3.10", "3.11"]:
        found, ver = python_exists(pyver)
        if found:
            log(f"  ✓ Python {pyver}: {ver}", "check")

    if issues:
        update_step(sid, "error", " · ".join(issues))
        return False

    desc = f"Disk: {disk_msg} · " + ("Online" if net_ok else "Offline")
    if not disk_ok:
        update_step(sid, "warn", f"Low disk ({disk_msg}) — proceed with caution")
    else:
        update_step(sid, "done", desc)
    return True


def step_git():
    sid = "git"
    update_step(sid, "running", "Checking…")
    log("\n━━ Git", "step")
    found, ver = git_exists()
    if found:
        update_step(sid, "skipped", f"Already installed — {ver}")
        return True
    update_step(sid, "running", "Installing via winget…")
    ok, _ = run_cmd(
        "winget install --id Git.Git -e --source winget --silent "
        "--accept-package-agreements --accept-source-agreements",
        timeout=300,
    )
    if ok:
        time.sleep(2)
        found, ver = git_exists()
        update_step(sid, "done", f"Installed — {ver}" if found else "Git installed")
    else:
        update_step(sid, "error", "Git install failed — check log")
    return ok


def step_ffmpeg():
    sid = "ffmpeg"
    update_step(sid, "running", "Checking…")
    log("\n━━ FFmpeg", "step")
    found, ver = ffmpeg_exists()
    if found:
        update_step(sid, "skipped", f"Already installed — {ver}")
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
        time.sleep(2)
        found, ver = ffmpeg_exists()
        update_step(sid, "done", f"Installed — {ver}" if found else "FFmpeg installed")
    else:
        update_step(sid, "error", "FFmpeg install failed (non-fatal — add manually if needed)")
    return ok


def _ensure_ffmpeg_path():
    candidates = [
        r"C:\Program Files\ffmpeg\bin",
        r"C:\ffmpeg\bin",
        r"C:\ProgramData\chocolatey\bin",
        os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"
            r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg\bin"
        ),
    ]
    base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    if os.path.isdir(base):
        for entry in os.listdir(base):
            if "Gyan.FFmpeg" in entry:
                candidates.insert(0, os.path.join(base, entry, "ffmpeg", "bin"))
    for p in candidates:
        if os.path.isdir(p):
            add_to_system_path(p)
            return


def step_miniconda(tmpdir):
    sid = "miniconda"
    update_step(sid, "running", "Checking…")
    log("\n━━ Miniconda", "step")
    found, ver = miniconda_exists()
    if found:
        update_step(sid, "skipped", f"Already installed — {ver}")
        return True
    update_step(sid, "running", "Downloading Miniconda…")
    dest = os.path.join(tmpdir, DOWNLOADS["miniconda"]["filename"])
    if not download_file(DOWNLOADS["miniconda"]["url"], dest, sid):
        update_step(sid, "error", "Download failed — check internet connection")
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
        time.sleep(2)
        found, ver = miniconda_exists()
        update_step(sid, "done", f"Installed — {ver}" if found else f"Installed → {install_path}")
    else:
        update_step(sid, "error", "Miniconda install failed — check log")
    return ok


def _install_python(ver_tag, sid, label, tmpdir):
    update_step(sid, "running", "Checking…")
    log(f"\n━━ Python {label}", "step")
    py_ver = "3.10" if "310" in ver_tag else "3.11"
    found, ver = python_exists(py_ver)
    if found:
        update_step(sid, "skipped", f"Already installed — {ver}")
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
        time.sleep(2)
        found, ver = python_exists(py_ver)
        update_step(sid, "done", f"Installed — {ver}" if found else f"Python {label} installed")
    else:
        update_step(sid, "error", f"Python {label} install failed")
    return ok


def step_vsbuild(tmpdir):
    sid = "vsbuild"
    update_step(sid, "running", "Checking…")
    log("\n━━ VS Build Tools 2022", "step")
    found, ver = vsbuild_exists()
    if found:
        update_step(sid, "skipped", f"Already installed — {ver}")
        return True
    update_step(sid, "running", "Downloading VS Build Tools…")
    dest = os.path.join(tmpdir, DOWNLOADS["vsbuild"]["filename"])
    if not download_file(DOWNLOADS["vsbuild"]["url"], dest, sid):
        update_step(sid, "error", "Download failed")
        return False
    update_step(sid, "running", "Installing VS Build Tools (10–20 min)…")
    add_flags = " ".join(f"--add {c}" for c in VS_COMPONENTS)
    ok, _ = run_cmd(
        f'"{dest}" --quiet --wait --norestart --nocache '
        f'--installPath "C:\\BuildTools" {add_flags}',
        timeout=2400,
    )
    # VS installer may return non-zero on success (reboot pending)
    if not ok:
        found, ver = vsbuild_exists()
        if found:
            ok = True
    if ok:
        update_step(sid, "done", "VS Build Tools 2022 installed")
    else:
        update_step(sid, "error", "VS Build Tools install failed — check log")
    return ok


def step_cuda(tmpdir):
    sid = "cuda"
    update_step(sid, "running", "Checking NVIDIA GPU…")
    log("\n━━ NVIDIA CUDA Toolkit", "step")

    # No GPU → not needed
    if not nvidia_gpu_present():
        log("  No NVIDIA GPU detected — CUDA Toolkit not required (CPU mode)", "warn")
        update_step(sid, "skipped", "No NVIDIA GPU — CPU-only mode")
        return True

    log("  NVIDIA GPU detected", "check")

    # Already installed?
    found, ver = cuda_toolkit_exists()
    if found:
        update_step(sid, "skipped", f"Already installed — {ver}")
        return True

    # Detect driver CUDA capability
    update_step(sid, "running", "Querying driver CUDA version…")
    driver_ver = get_driver_cuda_ver()

    if driver_ver is None:
        log("  Could not read CUDA Version from nvidia-smi output", "warn")
        log("  Install CUDA Toolkit 12.4 or 12.9 manually from developer.nvidia.com", "warn")
        update_step(sid, "warn", "Driver version undetectable — install CUDA Toolkit manually")
        return True  # non-fatal; setup_windows.ps1 has a PyTorch-bundled CUDA fallback

    log(f"  Driver max CUDA: {driver_ver}", "check")

    chosen = pick_cuda_version(driver_ver)
    if chosen is None:
        log(f"  ✗ Driver CUDA {driver_ver} is below 12.4 — neither 12.9 nor 12.4 can be installed", "err")
        log("  Update your NVIDIA driver to 551.61+ (for CUDA 12.4) or 576.02+ (for CUDA 12.9)", "warn")
        update_step(sid, "error", f"Driver CUDA {driver_ver} < 12.4 — update NVIDIA driver first")
        return False

    cfg = CUDA_VERSIONS[chosen]
    log(f"  Selected: CUDA Toolkit {chosen}  (driver {driver_ver} ≥ {cfg['min_driver']})", "ok")

    # Download network installer (~35 MB stub)
    update_step(sid, "running", f"Downloading CUDA Toolkit {chosen} network installer…")
    dest = os.path.join(tmpdir, cfg["filename"])
    if not download_file(cfg["url"], dest, sid):
        log("  Download failed. Get it from: developer.nvidia.com/cuda-toolkit-archive", "err")
        update_step(sid, "error", f"Download failed — install CUDA Toolkit {chosen} manually")
        return False

    # Silent install — only development components, no display driver
    update_step(sid, "running", f"Installing CUDA Toolkit {chosen} (5–20 min, downloads components)…")
    log("  Components: nvcc, compilers, cudart, cublas_dev, curand_dev, vs_integration", "info")
    log("  Note: the network installer downloads each component (~1–2 GB total)", "info")

    component_args = " ".join(f"{c}_{chosen}" for c in CUDA_COMPONENTS)
    ok, _ = run_cmd(f'"{dest}" -s {component_args}', timeout=2400)

    # CUDA installer often returns non-zero even on success (reboot pending)
    if not ok:
        found, ver = cuda_toolkit_exists()
        if found:
            ok = True
            log("  Installer returned non-zero but nvcc found — treating as success", "warn")

    if ok:
        add_to_system_path(cfg["bin"])
        # Add libnvvp and lib paths used by nvcc
        for sub in ["lib\\x64", "extras\\CUPTI\\lib64"]:
            candidate = cfg["bin"].replace("\\bin", f"\\{sub}")
            if os.path.isdir(candidate):
                add_to_system_path(candidate)
        found, ver = cuda_toolkit_exists()
        update_step(sid, "done", f"CUDA Toolkit {chosen} — {ver if found else 'installed'}")
    else:
        update_step(sid, "error", f"CUDA Toolkit {chosen} install failed — check log")

    return ok


def _run_git(git_exe: str, args: str, env: "dict[str, str]", timeout: int = 1800, cwd: "str | None" = None) -> bool:
    """Run a git command, stream every non-blank output line to the UI log."""
    global _current_proc
    if _abort_flag.is_set():
        return False
    cmd = f"{git_exe} {args}"
    log(f"  $ {cmd[:160]}{'…' if len(cmd) > 160 else ''}", "info")
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace", env=env, cwd=cwd,
        )
        with _proc_lock:
            _current_proc = proc
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            log(f"  TIMEOUT after {timeout}s", "err")
            return False
        finally:
            with _proc_lock:
                if _current_proc is proc:
                    _current_proc = None
        if _abort_flag.is_set():
            return False
        combined = (stdout + stderr).strip().splitlines()
        for line in combined:
            line = line.strip()
            if not line or "\r" in line:
                continue
            log(f"    {line}", "info" if proc.returncode == 0 else "warn")
        return proc.returncode == 0
    except Exception as e:
        log(f"  Exception: {e}", "err")
        return False


def _clear_dir(path: str) -> bool:
    """Remove a directory tree, return True on success."""
    try:
        shutil.rmtree(path)
        return True
    except Exception as e:
        log(f"  Could not remove {path}: {e}", "err")
        return False


def step_clone():
    sid = "clone"
    update_step(sid, "running", "Checking…")
    log("\n━━ Clone Repository (HuggingFace)", "step")

    KEY_FILES = ["setup_windows.ps1", "requirements.txt", "environment.yml"]

    # ── Resolve git executable ────────────────────────────────────────────────
    git_exe = "git"
    for candidate in [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
    ]:
        if os.path.isfile(candidate):
            git_exe = f'"{candidate}"'
            log(f"  Using git at: {candidate}", "info")
            break

    # ── Ensure git-lfs is present ─────────────────────────────────────────────
    lfs_ok, lfs_out = _probe(f"{git_exe} lfs version")
    if lfs_ok:
        log(f"  git-lfs: {lfs_out.strip().splitlines()[0] if lfs_out.strip() else 'present'}", "info")
    else:
        log("  git-lfs not found — installing via winget…", "warn")
        run_cmd(
            "winget install --id GitHub.GitLFS -e --source winget --silent "
            "--accept-package-agreements --accept-source-agreements",
            timeout=120,
        )
        time.sleep(2)

    env_git = os.environ.copy()
    env_git["GIT_TERMINAL_PROMPT"] = "0"
    env_git["GIT_LFS_SKIP_SMUDGE"] = "1"   # pull LFS files separately after clone

    _run_git(git_exe, "lfs install --force", env_git, timeout=30)

    # ── Evaluate existing directory state ─────────────────────────────────────
    dir_exists = os.path.exists(CLONE_DIR)
    git_exists = dir_exists and os.path.isdir(os.path.join(CLONE_DIR, ".git"))

    if git_exists:
        missing = [f for f in KEY_FILES if not os.path.isfile(os.path.join(CLONE_DIR, f))]
        if not missing:
            # Fully healthy — just make sure we're on the right branch
            _, branch_out = _probe(f'{git_exe} -C "{CLONE_DIR}" rev-parse --abbrev-ref HEAD')
            current_branch = branch_out.strip()
            if current_branch and current_branch != REPO_BRANCH:
                log(f"  Repo present on branch '{current_branch}' — switching to '{REPO_BRANCH}'…", "warn")
                _run_git(git_exe, f'-C "{CLONE_DIR}" checkout {REPO_BRANCH}', env_git, timeout=60)
            update_step(sid, "skipped", f"Already cloned → {CLONE_DIR}")
            return True

        # .git exists but incomplete — wipe and re-clone for a clean state
        log(f"  Incomplete clone at {CLONE_DIR} (missing: {', '.join(missing)}) — removing and re-cloning…", "warn")
        if not _clear_dir(CLONE_DIR):
            update_step(sid, "error", f"Cannot remove incomplete clone at {CLONE_DIR}")
            return False

    elif dir_exists:
        # Directory exists but no .git — stale or user-created folder
        log(f"  Directory exists at {CLONE_DIR} but is not a git repo — removing…", "warn")
        if not _clear_dir(CLONE_DIR):
            update_step(sid, "error", f"Cannot remove existing directory: {CLONE_DIR}")
            return False

    # ── Create parent directory if needed ─────────────────────────────────────
    parent = os.path.dirname(os.path.abspath(CLONE_DIR))
    if parent and not os.path.isdir(parent):
        try:
            os.makedirs(parent, exist_ok=True)
            log(f"  Created parent directory: {parent}", "info")
        except Exception as e:
            log(f"  Cannot create {parent}: {e}", "err")
            update_step(sid, "error", f"Cannot create directory: {parent}")
            return False

    log(f"  Source: {REPO_URL}", "info")
    log(f"  Branch: {REPO_BRANCH}", "info")
    log(f"  Dest:   {CLONE_DIR}", "info")
    log("  (LFS pointer files only during clone — data fetched next)", "info")

    # ── Attempt 1: clone with explicit branch ─────────────────────────────────
    update_step(sid, "running", f"Cloning branch {REPO_BRANCH}…")
    ok = _run_git(
        git_exe,
        f'clone --branch {REPO_BRANCH} --progress "{REPO_URL}" "{CLONE_DIR}"',
        env_git, timeout=1800,
    )

    # ── Attempt 2: clone default branch, then checkout desired branch ─────────
    if not ok:
        log(f"  Branch '{REPO_BRANCH}' clone failed — cloning default branch and switching…", "warn")
        if os.path.exists(CLONE_DIR):
            shutil.rmtree(CLONE_DIR, ignore_errors=True)

        update_step(sid, "running", "Cloning default branch…")
        if not _run_git(git_exe, f'clone --progress "{REPO_URL}" "{CLONE_DIR}"', env_git, timeout=1800):
            update_step(sid, "error", "Clone failed — check internet connection and HuggingFace access")
            return False

        switched = _run_git(git_exe, f'-C "{CLONE_DIR}" checkout {REPO_BRANCH}', env_git, timeout=60)
        if switched:
            log(f"  Switched to branch {REPO_BRANCH}", "ok")
        else:
            log(f"  Branch '{REPO_BRANCH}' not found on remote — staying on default branch", "warn")

    # ── Pull LFS files ────────────────────────────────────────────────────────
    update_step(sid, "running", "Fetching LFS files…")
    log("  Pulling LFS tracked files…", "info")
    env_lfs = os.environ.copy()
    env_lfs["GIT_TERMINAL_PROMPT"] = "0"
    _run_git(git_exe, f'-C "{CLONE_DIR}" lfs pull', env_lfs, timeout=900)

    # ── Verify key files ──────────────────────────────────────────────────────
    missing = [f for f in KEY_FILES if not os.path.isfile(os.path.join(CLONE_DIR, f))]
    if missing:
        log(f"  ⚠ Clone succeeded but key files missing: {', '.join(missing)}", "warn")
        update_step(sid, "warn", f"Cloned — missing: {', '.join(missing)}")
    else:
        update_step(sid, "done", f"Cloned → {CLONE_DIR} (all key files present)")

    return True
def step_setup():
    sid = "setup"
    update_step(sid, "running", "Checking…")
    log("\n━━ Setup Conda Environments", "step")

    if not os.path.isdir(CLONE_DIR):
        update_step(sid, "error", f"{CLONE_DIR} not found — clone step must have failed")
        return False

    ps_script = os.path.join(CLONE_DIR, "setup_windows.ps1")
    if not os.path.isfile(ps_script):
        update_step(sid, "error", "setup_windows.ps1 not found in repo")
        return False

    vidcolor_ok = conda_env_exists("vidcolor")
    gdino_ok    = conda_env_exists("gdino310")
    if vidcolor_ok and gdino_ok:
        update_step(sid, "skipped", "Conda envs 'vidcolor' and 'gdino310' already exist")
        return True
    if vidcolor_ok:
        log("  'vidcolor' exists but 'gdino310' is missing — running setup to complete…", "warn")
    elif gdino_ok:
        log("  'gdino310' exists but 'vidcolor' is missing — running setup to complete…", "warn")

    update_step(sid, "running", "Running setup_windows.ps1 (10–30 min)…")
    log("  Creates conda environments and installs the full ML stack.", "info")
    ok, _ = run_cmd(
        f'powershell -ExecutionPolicy Bypass -File "{ps_script}"',
        timeout=7200,
        cwd=CLONE_DIR,
    )

    vidcolor_ok = conda_env_exists("vidcolor")
    gdino_ok    = conda_env_exists("gdino310")

    if vidcolor_ok and gdino_ok:
        update_step(sid, "done", "Conda envs 'vidcolor' and 'gdino310' ready")
        return True
    if ok and not (vidcolor_ok or gdino_ok):
        update_step(sid, "error", "Script ran OK but no conda envs found — check log")
        return False
    if not ok and (vidcolor_ok or gdino_ok):
        envs = " + ".join(filter(None, [
            "vidcolor" if vidcolor_ok else "",
            "gdino310" if gdino_ok else "",
        ]))
        log(f"  Script exited with errors but env(s) created: {envs}", "warn")
        update_step(sid, "warn", f"Partial success: {envs} created (see log)")
        return True  # partial success — verify step will catch gaps
    update_step(sid, "error", "setup_windows.ps1 failed — check log for details")
    return False


def step_path_env():
    sid = "pathenv"
    update_step(sid, "running", "Updating PATH…")
    log("\n━━ Update System PATH", "step")
    candidates = [
        r"C:\Program Files\Git\cmd",
        r"C:\Program Files\Git\bin",
        r"C:\Miniconda3",
        r"C:\Miniconda3\Scripts",
        r"C:\Miniconda3\condabin",
        r"C:\BuildTools\MSBuild\Current\Bin",
    ]
    for cfg in CUDA_VERSIONS.values():
        candidates.append(cfg["bin"])
    added = sum(1 for p in candidates if os.path.isdir(p) and (add_to_system_path(p) or True))
    broadcast_env_change()
    update_step(sid, "done", f"System PATH updated ({added} paths verified)")
    return True


def step_verify():
    sid = "verify"
    update_step(sid, "running", "Verifying installation…")
    log("\n━━ Verify Installation", "step")
    hard_failures = []

    def chk(label, ok, ver, critical=True):
        if ok:
            log(f"  ✓ {label}: {ver}", "ok")
        else:
            lvl = "err" if critical else "warn"
            log(f"  {'✗' if critical else '!'} {label}: not found", lvl)
            if critical:
                hard_failures.append(label)

    ok, ver = git_exists()
    chk("Git", ok, ver)
    ok, ver = ffmpeg_exists()
    chk("FFmpeg", ok, ver, critical=False)
    ok, ver = miniconda_exists()
    chk("Conda", ok, ver)
    ok, ver = python_exists("3.10")
    chk("Python 3.10", ok, ver)
    ok, ver = python_exists("3.11")
    chk("Python 3.11", ok, ver, critical=False)
    ok, ver = vsbuild_exists()
    chk("VS Build Tools", ok, ver)

    # CUDA Toolkit — only critical if GPU is present
    gpu = nvidia_gpu_present()
    if gpu:
        ok, ver = cuda_toolkit_exists()
        if ok:
            log(f"  ✓ CUDA Toolkit (nvcc): {ver}", "ok")
        else:
            log("  ✗ CUDA Toolkit (nvcc): not found — GroundingDINO custom ops may not compile", "warn")
            # Not appended to hard_failures: setup_windows.ps1 has a torch-bundled fallback
    else:
        log("  — CUDA Toolkit: no GPU, skipped", "info")

    clone_ok = os.path.isdir(os.path.join(CLONE_DIR, ".git"))
    chk("Repository", clone_ok, CLONE_DIR)

    vidcolor_ok = conda_env_exists("vidcolor")
    gdino_ok    = conda_env_exists("gdino310")
    chk("Conda env: vidcolor",  vidcolor_ok, "present")
    chk("Conda env: gdino310",  gdino_ok,    "present")

    if not hard_failures:
        update_step(sid, "done", "All critical components verified ✓")
        return True
    else:
        update_step(sid, "error", f"Missing: {', '.join(hard_failures)}")
        return False

# ─── Installer orchestration ───────────────────────────────────────────────────

def run_installer(retry_steps=None):
    global _failed_steps
    errors: list[str] = []
    tmpdir = tempfile.mkdtemp(prefix="moodplay_inst_")
    log(f"Temp dir: {tmpdir}", "info")

    all_steps = [
        ("preflight", lambda: step_preflight()),
        ("git",       lambda: step_git()),
        ("ffmpeg",    lambda: step_ffmpeg()),
        ("miniconda", lambda: step_miniconda(tmpdir)),
        ("py310",     lambda: _install_python("py310", "py310", "3.10.9", tmpdir)),
        ("py311",     lambda: _install_python("py311", "py311", "3.11.9", tmpdir)),
        ("vsbuild",   lambda: step_vsbuild(tmpdir)),
        ("cuda",      lambda: step_cuda(tmpdir)),
        ("clone",     lambda: step_clone()),
        ("setup",     lambda: step_setup()),
        ("pathenv",   lambda: step_path_env()),
        ("verify",    lambda: step_verify()),
    ]

    sequence = [(s, f) for s, f in all_steps if retry_steps is None or s in retry_steps]
    if retry_steps:
        log(f"Retrying: {', '.join(s for s, _ in sequence)}", "step")

    for sid, fn in sequence:
        if _abort_flag.is_set():
            update_step(sid, "skipped", "Aborted")
            continue
        try:
            ok = fn()
            if not ok:
                errors.append(sid)
        except Exception as exc:
            log(f"  Unhandled error in [{sid}]: {exc}", "err")
            update_step(sid, "error", str(exc)[:70])
            errors.append(sid)

    _failed_steps = list(errors) if not _abort_flag.is_set() else []
    shutil.rmtree(tmpdir, ignore_errors=True)

    if _abort_flag.is_set():
        log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")
        log("Installation aborted by user.", "warn")
        log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")
        if _window:
            _window.evaluate_js("onAborted()")
        return

    log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")
    if errors:
        log(f"Completed with errors in: {', '.join(errors)}", "err")
        log("Click  Retry Failed  to re-run only the failed steps.", "warn")
    else:
        log("All steps completed successfully.", "ok")
        log("", "info")
        log("━━ Next Steps ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "step")
        log("1. Open a new terminal (Win + R → cmd)", "msg")
        log(f"2. cd {CLONE_DIR}", "msg")
        log("3. conda activate vidcolor", "msg")
        log("4. streamlit run app.py", "msg")
        log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")

    if _window:
        _window.evaluate_js(f'onComplete({"true" if not errors else "false"})')

# ─── pywebview API ─────────────────────────────────────────────────────────────

class InstallerApi:
    def browse_folder(self):
        if _window:
            result = _window.create_file_dialog(webview.FOLDER_DIALOG, allow_multiple=False)
            if result:
                return result[0]
        return None

    def abort_install(self):
        _abort_flag.set()
        _kill_current_proc()
        log("\n⚠ Abort requested — stopping after current operation…", "warn")

    def start_install(self, path=""):
        global CLONE_DIR
        _abort_flag.clear()
        p = (path or "").strip()
        if p:
            # Validate: the chosen path must either not exist yet, be empty,
            # or already be a valid moodplay clone (.git present).
            # This prevents git failing when user picks Downloads, Desktop, etc.
            is_existing_clone = os.path.isdir(os.path.join(p, ".git"))
            is_empty_or_new   = (not os.path.exists(p)) or (
                os.path.isdir(p) and len(os.listdir(p)) == 0
            )
            if is_existing_clone or is_empty_or_new:
                CLONE_DIR = p
            else:
                # Path exists and already has files — append \moodplay subfolder
                candidate = os.path.join(p, "moodplay")
                log(
                    f"  ⚠ Chosen path '{p}' already has files — "
                    f"cloning into '{candidate}' instead",
                    "warn"
                )
                CLONE_DIR = candidate
        threading.Thread(target=run_installer, daemon=True).start()

    def retry_failed(self):
        if _failed_steps:
            steps = list(_failed_steps)
            threading.Thread(
                target=lambda: run_installer(retry_steps=steps), daemon=True
            ).start()

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
        width=1060,
        height=720,
        resizable=True,
        min_size=(800, 540),
        background_color="#0d0d1a",
    )
    webview.start(debug=False)

if __name__ == "__main__":
    main()
