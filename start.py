#!/usr/bin/env python3
r"""
IoT Lab Vision Intelligence Pipeline - All-In-One Unified Launcher
==================================================================
Runs the complete stack with a single command:
  - Backend: FastAPI Computer Vision Inference Server (Port 8000)
  - Frontend: Next.js Real-Time Telemetry Dashboard (Port 3000)
  - Web Browser: Automatically opens http://localhost:3000 where the webcam
                 runs directly inside the Next.js website (no separate OpenCV window)!

Usage:
  python start.py                 # Start stack, opens Next.js with in-browser webcam
  .\start.bat                     # Double-click or run from Windows terminal
  python start.py --split         # Start Backend & Frontend in separate terminal windows
  python start.py --simulator     # Start Backend, Frontend, and Synthetic Camera Simulator
"""

import os
import sys
import time
import signal
import argparse
import subprocess
import threading
import urllib.request
import webbrowser

# Enable ANSI colors on Windows CMD
if os.name == 'nt':
    os.system('')

# ANSI Color Codes
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_BLUE = "\033[94m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_RED = "\033[91m"

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

# Locate python interpreter (prefer backend virtual environment)
VENV_PYTHON = os.path.join(BACKEND_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = os.path.join(BACKEND_DIR, "venv", "bin", "python")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

processes = []
shutting_down = False


def log(tag, message, color=COLOR_CYAN):
    print(f"{color}{COLOR_BOLD}[{tag:<8}]{COLOR_RESET} {message}", flush=True)


def stream_logs(pipe, tag, color):
    """Streams stdout/stderr lines from a process with a color-coded tag."""
    try:
        for line in iter(pipe.readline, ''):
            if shutting_down:
                break
            text = line.rstrip()
            if text:
                print(f"{color}[{tag:<8}]{COLOR_RESET} {text}", flush=True)
    except Exception:
        pass


def kill_process_tree(proc):
    """Recursively terminates a process and all its children."""
    pid = proc.pid
    try:
        import psutil
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.terminate()
            except Exception:
                pass
        parent.terminate()
        _, alive = psutil.wait_procs(parent.children(recursive=True) + [parent], timeout=2)
        for p in alive:
            try:
                p.kill()
            except Exception:
                pass
    except Exception:
        # Fallback if psutil fails
        if os.name == 'nt':
            subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                proc.kill()
            except Exception:
                pass


def wait_for_http(url, timeout=30.0, step=0.5):
    """Polls an HTTP endpoint until it returns 200 OK or times out."""
    start = time.time()
    while time.time() - start < timeout:
        if shutting_down:
            return False
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'AllInOneLauncher'})
            with urllib.request.urlopen(req, timeout=1.0) as res:
                if res.status == 200:
                    return True
        except Exception:
            time.sleep(step)
    return False


def launch_in_separate_windows(args):
    """Launches the stack in separate titled Windows command prompt windows."""
    log("SYSTEM", "Launching services in separate CMD windows...", COLOR_MAGENTA)

    # 1. Backend
    backend_cmd = f'cd /d "{BACKEND_DIR}" && "{VENV_PYTHON}" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload'
    subprocess.Popen(f'start "IoT Lab - 1. FastAPI Backend" cmd /k "{backend_cmd}"', shell=True)
    log("SYSTEM", "Started Backend window (FastAPI on Port 8000).", COLOR_BLUE)

    # 2. Frontend
    frontend_cmd = f'cd /d "{FRONTEND_DIR}" && npm run dev'
    subprocess.Popen(f'start "IoT Lab - 2. Next.js Dashboard" cmd /k "{frontend_cmd}"', shell=True)
    log("SYSTEM", "Started Frontend window (Next.js on Port 3000).", COLOR_GREEN)

    # Optional simulator
    if args.simulator:
        sim_cmd = f'cd /d "{PROJECT_ROOT}" && "{VENV_PYTHON}" backend/scripts/simulate_camera.py'
        subprocess.Popen(f'start "IoT Lab - 3. Camera Simulator" cmd /k "{sim_cmd}"', shell=True)
        log("SYSTEM", "Started Camera Simulator window.", COLOR_YELLOW)
    elif args.python_streamer:
        cam_cmd = f'cd /d "{PROJECT_ROOT}" && "{VENV_PYTHON}" run_webcam.py --no-preview'
        subprocess.Popen(f'start "IoT Lab - 3. Headless Streamer" cmd /k "{cam_cmd}"', shell=True)
        log("SYSTEM", "Started Headless Python Streamer window.", COLOR_YELLOW)

    # Wait for frontend to be accessible before opening browser
    log("SYSTEM", "Waiting for Frontend to respond on http://localhost:3000...", COLOR_MAGENTA)
    wait_for_http("http://localhost:3000", timeout=25.0)

    if not args.no_browser:
        log("SYSTEM", "Opening dashboard in browser (webcam runs inside the website)...", COLOR_MAGENTA)
        webbrowser.open("http://localhost:3000")

    print("\n" + "=" * 65)
    print(f"{COLOR_GREEN}{COLOR_BOLD}  Services launched! Your webcam will open inside the Next.js site.{COLOR_RESET}")
    print(f"  • Dashboard: {COLOR_CYAN}http://localhost:3000{COLOR_RESET}")
    print(f"  • Backend:   {COLOR_CYAN}http://localhost:8000{COLOR_RESET}")
    print(f"  • Swagger:   {COLOR_CYAN}http://localhost:8000/docs{COLOR_RESET}")
    print(f"  • To stop all services: run {COLOR_YELLOW}stop.bat{COLOR_RESET} or close each window.")
    print("=" * 65 + "\n")


def main():
    global shutting_down
    parser = argparse.ArgumentParser(description="IoT Lab Vision All-In-One Launcher")
    parser.add_argument("--split", "-w", action="store_true", help="Launch each service in a separate Windows terminal window")
    parser.add_argument("--simulator", action="store_true", help="Run synthetic hardware camera simulator")
    parser.add_argument("--python-streamer", action="store_true", help="Run standalone Python streamer (headless)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    print("=" * 65)
    print(f"{COLOR_BOLD}{COLOR_CYAN}       IoT Lab Vision Pipeline - Unified Launcher{COLOR_RESET}")
    print("=" * 65)
    print(f"  Python Environment: {VENV_PYTHON}")
    print(f"  Project Root:       {PROJECT_ROOT}")
    print(f"  Webcam View:        Inside Next.js Dashboard (http://localhost:3000)")
    print("=" * 65)

    if args.split and os.name == 'nt':
        launch_in_separate_windows(args)
        return

    # Unified single-terminal launcher
    def signal_handler(sig, frame):
        global shutting_down
        if shutting_down:
            return
        shutting_down = True
        print("\n")
        log("SYSTEM", "Graceful shutdown initiated. Terminating child processes...", COLOR_RED)
        for name, proc in reversed(processes):
            log("SYSTEM", f"Stopping {name} (PID {proc.pid})...", COLOR_YELLOW)
            kill_process_tree(proc)
        log("SYSTEM", "All processes stopped cleanly. Goodbye!", COLOR_GREEN)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 1. Start FastAPI Backend
    log("SYSTEM", "Starting Backend (FastAPI on http://localhost:8000)...", COLOR_BLUE)
    backend_cmd = [VENV_PYTHON, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    processes.append(("Backend", backend_proc))
    t_back = threading.Thread(target=stream_logs, args=(backend_proc.stdout, "BACKEND", COLOR_BLUE), daemon=True)
    t_back.start()

    # 2. Start Next.js Frontend
    log("SYSTEM", "Starting Frontend (Next.js on http://localhost:3000)...", COLOR_GREEN)
    frontend_cmd = "npm run dev"
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND_DIR,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    processes.append(("Frontend", frontend_proc))
    t_front = threading.Thread(target=stream_logs, args=(frontend_proc.stdout, "FRONTEND", COLOR_GREEN), daemon=True)
    t_front.start()

    # Optional simulator or python streamer
    if args.simulator:
        log("SYSTEM", "Starting Synthetic Camera Simulator...", COLOR_YELLOW)
        sim_cmd = [VENV_PYTHON, "backend/scripts/simulate_camera.py"]
        sim_proc = subprocess.Popen(
            sim_cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        processes.append(("Simulator", sim_proc))
        t_sim = threading.Thread(target=stream_logs, args=(sim_proc.stdout, "SIMULATOR", COLOR_YELLOW), daemon=True)
        t_sim.start()
    elif args.python_streamer:
        log("SYSTEM", "Starting Headless Python Streamer...", COLOR_YELLOW)
        cam_cmd = [VENV_PYTHON, "run_webcam.py", "--no-preview"]
        cam_proc = subprocess.Popen(
            cam_cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        processes.append(("Streamer", cam_proc))
        t_cam = threading.Thread(target=stream_logs, args=(cam_proc.stdout, "STREAMER", COLOR_YELLOW), daemon=True)
        t_cam.start()

    # Wait for Backend to become healthy
    log("SYSTEM", "Waiting for Backend to initialize (http://localhost:8000/health)...", COLOR_MAGENTA)
    if wait_for_http("http://localhost:8000/health", timeout=30.0):
        log("SYSTEM", "Backend is healthy and ready!", COLOR_GREEN)
    else:
        log("SYSTEM", "Backend is taking time to initialize; proceeding...", COLOR_YELLOW)

    # Automatically open browser to Next.js
    if not args.no_browser:
        log("SYSTEM", "Waiting for Frontend to respond on http://localhost:3000...", COLOR_MAGENTA)
        if wait_for_http("http://localhost:3000", timeout=25.0):
            log("SYSTEM", "Frontend is ready! Opening dashboard in browser...", COLOR_GREEN)
        else:
            log("SYSTEM", "Opening dashboard in browser...", COLOR_CYAN)
        webbrowser.open("http://localhost:3000")

    print("\n" + "=" * 65)
    print(f"{COLOR_GREEN}{COLOR_BOLD}  IoT Lab Vision Pipeline is RUNNING!{COLOR_RESET}")
    print(f"  • Dashboard:  {COLOR_CYAN}http://localhost:3000{COLOR_RESET}")
    print(f"  • Webcam:     {COLOR_GREEN}Opens inside the website (no separate window){COLOR_RESET}")
    print(f"  • API / Docs: {COLOR_CYAN}http://localhost:8000/docs{COLOR_RESET}")
    print(f"  • Press {COLOR_RED}Ctrl+C{COLOR_RESET} at any time to cleanly stop all services.")
    print("=" * 65 + "\n")

    # Keep main thread alive monitoring child processes
    try:
        while True:
            time.sleep(1)
            for name, proc in processes:
                if proc.poll() is not None and not shutting_down:
                    log("SYSTEM", f"{name} process exited with code {proc.returncode}.", COLOR_RED)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
