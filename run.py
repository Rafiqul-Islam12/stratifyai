#!/usr/bin/env python3
"""StratifyAI one-command launcher (standard library only, cross-platform).

Commands:
    setup    create .venv, install requirements, seed .env, generate data if present
    start    launch the Streamlit app on 127.0.0.1:8501
    demo     setup if needed, then start and open the browser
    test     pytest -q
    eval     python scripts/run_eval.py
    check    health check (imports, data, fonts, copilot mode, audit chain, .env)
    status   scripts/status.py
    report   python scripts/build_report.py

No argument behaves like `start`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_ENTRY = ROOT / "app" / "main.py"
HOST = "127.0.0.1"
PORT = "8501"
URL = f"http://{HOST}:{PORT}"
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
REQUIREMENTS_DEV = ROOT / "requirements-dev.txt"
ENV_EXAMPLE = ROOT / ".env.example"
ENV_FILE = ROOT / ".env"
DATA_GENERATOR = ROOT / "data" / "generate_synthetic.py"
EVAL_SCRIPT = ROOT / "scripts" / "run_eval.py"
REPORT_SCRIPT = ROOT / "scripts" / "build_report.py"
STATUS_SCRIPT = ROOT / "scripts" / "status.py"
SECRETS_SCRIPT = ROOT / "scripts" / "check_secrets.py"


def is_windows() -> bool:
    return os.name == "nt"


def venv_python() -> Path | None:
    """The project venv interpreter, if `setup` has been run."""
    scripts = "Scripts" if is_windows() else "bin"
    exe = "python.exe" if is_windows() else "python"
    candidate = VENV_DIR / scripts / exe
    return candidate if candidate.is_file() else None


def python() -> str:
    """Prefer the venv interpreter; fall back to the one running this script."""
    venv = venv_python()
    return str(venv) if venv else sys.executable


def run(command: list[str], *, cwd: Path | None = None) -> int:
    """Echo a command and run it."""
    print("$ " + " ".join(f'"{part}"' if " " in part else part for part in command))
    return subprocess.run(command, check=False, cwd=cwd or ROOT).returncode


def step(title: str) -> None:
    print()
    print(f"== {title}")


def missing_script(path: Path, purpose: str) -> int:
    print(f"{path.relative_to(ROOT)} does not exist yet (built by a later task). {purpose}")
    return 0


# --------------------------------------------------------------------------
# setup
# --------------------------------------------------------------------------


def setup_venv() -> None:
    if venv_python():
        print(f"venv already present: {VENV_DIR}")
        return
    step("Creating virtual environment")
    if run([sys.executable, "-m", "venv", str(VENV_DIR)]) != 0:
        raise SystemExit("failed to create the virtual environment")


def install_requirements() -> None:
    py = python()
    step("Installing requirements")
    run([py, "-m", "pip", "install", "--upgrade", "pip"])
    if not REQUIREMENTS.is_file():
        raise SystemExit(f"{REQUIREMENTS.name} is missing")
    if run([py, "-m", "pip", "install", "-r", str(REQUIREMENTS)]) != 0:
        raise SystemExit("failed to install requirements")
    if REQUIREMENTS_DEV.is_file():
        run([py, "-m", "pip", "install", "-r", str(REQUIREMENTS_DEV)])


def seed_env() -> None:
    step("Seeding .env")
    if ENV_FILE.exists():
        print(f"{ENV_FILE.name} already exists, leaving it untouched")
        return
    if not ENV_EXAMPLE.is_file():
        raise SystemExit(f"{ENV_EXAMPLE.name} is missing")
    shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
    print(f"copied {ENV_EXAMPLE.name} -> {ENV_FILE.name} (values are placeholders; edit .env)")


def generate_data() -> None:
    step("Generating synthetic data")
    if not DATA_GENERATOR.is_file():
        print("data/generate_synthetic.py not present yet (built by T03), nothing to generate")
        return
    run([python(), str(DATA_GENERATOR)])


def cmd_setup() -> int:
    setup_venv()
    install_requirements()
    seed_env()
    generate_data()
    print()
    print("setup complete. Run: python run.py demo")
    return 0


def ensure_setup() -> bool:
    """Run setup if the venv or the app entry point is missing."""
    if venv_python() and APP_ENTRY.is_file():
        return True
    print("first run detected, running setup")
    return cmd_setup() == 0


# --------------------------------------------------------------------------
# running the app
# --------------------------------------------------------------------------


def streamlit_command() -> list[str]:
    if not APP_ENTRY.is_file():
        raise SystemExit(f"{APP_ENTRY.relative_to(ROOT)} is missing")
    return [python(), "-m", "streamlit", "run", str(APP_ENTRY), "--server.port", PORT, "--server.address", HOST]


def open_browser(delay: float = 3.0) -> None:
    threading.Thread(target=lambda: (time.sleep(delay), webbrowser.open(URL)), daemon=True).start()


def cmd_start() -> int:
    print(f"launching StratifyAI on {URL}")
    return run(streamlit_command())


def cmd_demo() -> int:
    if not ensure_setup():
        return 1
    open_browser()
    return cmd_start()


def cmd_test() -> int:
    return run([python(), "-m", "pytest", "-q"])


def cmd_eval() -> int:
    if not EVAL_SCRIPT.is_file():
        return missing_script(EVAL_SCRIPT, "Nothing to evaluate yet.")
    return run([python(), str(EVAL_SCRIPT)])


def cmd_report() -> int:
    if not REPORT_SCRIPT.is_file():
        return missing_script(REPORT_SCRIPT, "No report is built until T15.")
    return run([python(), str(REPORT_SCRIPT)])


def cmd_status() -> int:
    if not STATUS_SCRIPT.is_file():
        return missing_script(STATUS_SCRIPT, "No status script yet.")
    args = [python(), str(STATUS_SCRIPT)]
    if "--no-tests" in sys.argv:
        args.append("--no-tests")
    return run(args)


# --------------------------------------------------------------------------
# health check
# --------------------------------------------------------------------------

CHECK_PY = """
import importlib.util
import json
import os
from pathlib import Path

root = Path(%r)

def installed(name):
    return importlib.util.find_spec(name) is not None

modules = ["streamlit", "pandas", "numpy", "plotly", "pydantic", "openpyxl"]
fonts_dir = root / "static" / "fonts"
data_dir = root / "data"
report = {
    "python": os.sys.version.split()[0],
    "interpreter": os.sys.executable,
    "modules": {name: installed(name) for name in modules},
    "dataset_dirs": sorted(p.name for p in data_dir.glob("*") if p.is_dir()) if data_dir.is_dir() else [],
    "dataset_files": sorted(p.name for p in data_dir.glob("*") if p.is_file()) if data_dir.is_dir() else [],
    "font_files": sorted(p.name for p in fonts_dir.iterdir() if p.is_file()) if fonts_dir.is_dir() else [],
    "copilot_mode": (os.environ.get("COPILOT_MODE") or "offline").lower(),
    "copilot_configured": bool(os.environ.get("COPILOT_API_KEY") or os.environ.get("COPILOT_BASE_URL")),
    "services": sorted(p.name for p in (root / "services").glob("*.py")) if (root / "services").is_dir() else [],
    "db_files": sorted(p.name for p in root.glob("*.db")),
}
print(json.dumps(report, indent=2, sort_keys=True))
"""


def load_env_values() -> dict[str, str]:
    """Read KEY=VALUE pairs from .env (COPILOT_MODE feeds the check)."""
    values: dict[str, str] = {}
    if not ENV_FILE.is_file():
        return values
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _ok(value: bool) -> str:
    return "ok" if value else "MISSING"


def cmd_check() -> int:
    env = load_env_values()
    os.environ.setdefault("COPILOT_MODE", env.get("COPILOT_MODE", "offline"))
    os.environ.setdefault("COPILOT_API_KEY", env.get("COPILOT_API_KEY", ""))
    os.environ.setdefault("COPILOT_BASE_URL", env.get("COPILOT_BASE_URL", ""))

    step("Health check")
    failures: list[str] = []

    result = subprocess.run([python(), "-c", CHECK_PY % str(ROOT)],
                            check=False, capture_output=True, text=True, cwd=ROOT)
    import json

    facts = json.loads(result.stdout)
    for name, present in facts["modules"].items():
        print(f"  {name:12} {_ok(present)}")
        if not present:
            failures.append(f"module {name} not importable")
    print(f"  python       {facts['python']}")
    print(f"  interpreter  {facts['interpreter']}")

    print(f"  datasets     {len(facts['dataset_dirs']) + len(facts['dataset_files'])} entries "
          f"({', '.join(facts['dataset_dirs'][:4]) or 'none yet, built by T03'})")
    if not facts["dataset_dirs"] and not facts["dataset_files"]:
        failures.append("no data present")

    if facts["font_files"]:
        print(f"  fonts        {', '.join(facts['font_files'])}")
    else:
        print("  fonts        none yet (T02 adds static/fonts, system-ui fallback in use)")

    print(f"  copilot mode {facts['copilot_mode']}" + ("" if facts["copilot_configured"] else " (no key configured)"))

    audit_module = root_audit_present()
    print(f"  audit chain  {_ok(audit_module)}" if audit_module else "  audit chain  not built yet (T11)")

    gitignore = ROOT / ".gitignore"
    covered = gitignore.is_file() and any(
        line.strip() in {".env", "/.env"} for line in gitignore.read_text(encoding="utf-8").splitlines()
    )
    print(f"  .env ignored {_ok(covered)}")
    if not covered:
        failures.append(".env is not covered by .gitignore")

    if SECRETS_SCRIPT.is_file():
        scan = subprocess.run([python(), str(SECRETS_SCRIPT)],
                              check=False, capture_output=True, text=True, cwd=ROOT)
        print(f"  secret scan    {_ok(scan.returncode == 0)}")
        if scan.returncode != 0:
            failures.append("secret scan found matches")
        if scan.stdout.strip():
            for line in scan.stdout.strip().splitlines():
                print(f"    {line}")

    print()
    if failures:
        print("health check FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("health check passed")
    return 0


def root_audit_present() -> bool:
    return (ROOT / "services" / "audit.py").is_file()


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

COMMANDS = {
    "setup": cmd_setup,
    "start": cmd_start,
    "demo": cmd_demo,
    "test": cmd_test,
    "eval": cmd_eval,
    "check": cmd_check,
    "status": cmd_status,
    "report": cmd_report,
}

USAGE = f"""\
StratifyAI launcher. Usage: python run.py [command]

    setup     create .venv, install requirements, seed .env, generate data
    start     launch the app on {URL}
    demo      setup if needed, then start and open the browser
    test      pytest -q
    eval      run scripts/run_eval.py
    check     health check (imports, data, fonts, copilot mode, audit chain, .env)
    status    print task progress and recent commits
    report    run scripts/build_report.py

No argument runs `start`. `status` accepts --no-tests."""


def main(argv: list[str]) -> int:
    if argv and argv[0] in {"-h", "--help"}:
        print(USAGE)
        return 0
    command = argv[0] if argv else "start"
    handler = COMMANDS.get(command)
    if handler is None:
        print(USAGE)
        return 2
    return handler()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
