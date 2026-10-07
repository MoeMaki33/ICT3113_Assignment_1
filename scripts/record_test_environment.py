"""Record one test machine's hardware and software (run it ON each machine before benchmarking).

    python -m scripts.record_test_environment --role service      # service + Ollama machine
    python -m scripts.record_test_environment --role loadgen      # JMeter machine

Writes ``results/environment/<role>-<hostname>.json`` (a new timestamped file if one exists).
Values are read from the machine; anything that cannot be read is recorded as null, never
guessed. Fill the network section and anything null in docs/test_environment.md by hand.
"""
import argparse
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.perf_common import ROOT, git_info, utc_now, write_json


def _run(command: list[str], timeout: int = 20) -> str | None:
    if not shutil.which(command[0]):
        return None
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or "") + (result.stderr or "")
    return output.strip() or None


def cpu_model() -> str | None:
    system = platform.system()
    if system == "Darwin":
        return _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    if system == "Windows":
        out = _run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"])
        return out.splitlines()[0].strip() if out else None
    try:
        text = Path("/proc/cpuinfo").read_text()
    except OSError:
        return None
    match = re.search(r"model name\s*:\s*(.+)", text)
    return match.group(1).strip() if match else None


def total_ram_gb() -> float | None:
    system = platform.system()
    try:
        if system == "Darwin":
            return round(int(_run(["sysctl", "-n", "hw.memsize"])) / 1024**3, 1)
        if system == "Windows":
            out = _run(["powershell", "-NoProfile", "-Command",
                        "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"])
            return round(int(out) / 1024**3, 1)
        match = re.search(r"MemTotal:\s+(\d+) kB", Path("/proc/meminfo").read_text())
        return round(int(match.group(1)) / 1024**2, 1)
    except (TypeError, ValueError, OSError, AttributeError):
        return None


def first_line(text: str | None) -> str | None:
    return text.splitlines()[0].strip() if text else None


def collect(role: str, jmeter: str | None = None) -> dict:
    info = {
        "role": role, "recorded_utc": utc_now(), "hostname": socket.gethostname(),
        "os": platform.platform(), "os_release": platform.release(), "machine": platform.machine(),
        "cpu_model": cpu_model(), "logical_cpus": os.cpu_count(), "physical_cores": None,
        "ram_gb": total_ram_gb(), "python": sys.version.split()[0], "git": git_info(ROOT),
    }
    if platform.system() == "Darwin":
        info["physical_cores"] = int(_run(["sysctl", "-n", "hw.physicalcpu"]) or 0) or None
    elif platform.system() == "Windows":
        out = _run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).NumberOfCores"])
        info["physical_cores"] = int(out.splitlines()[0]) if out and out.splitlines()[0].isdigit() else None
    if role == "service":
        info["docker"] = first_line(_run(["docker", "--version"]))
        info["docker_compose"] = first_line(_run(["docker", "compose", "version"]))
        info["ollama"] = first_line(_run(["ollama", "--version"]))
        info["ollama_list"] = _run(["ollama", "list"])
        info["ollama_ps"] = _run(["ollama", "ps"])
        info["ollama_env"] = {k: v for k, v in os.environ.items() if k.startswith("OLLAMA_")}
    if role == "loadgen":
        info["java"] = first_line(_run(["java", "-version"]))
        jmeter_bin = jmeter or os.getenv("JMETER_BIN") or "jmeter"
        out = _run([jmeter_bin, "--version"], timeout=60)
        match = re.search(r"\d+\.\d+(?:\.\d+)?", out or "")
        info["jmeter"] = match.group(0) if match else None
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--role", required=True, choices=("service", "loadgen"))
    parser.add_argument("--jmeter", help="jmeter executable (load generator only)")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "environment")
    args = parser.parse_args()
    data = collect(args.role, args.jmeter)
    target = args.output_dir / f"{args.role}-{data['hostname']}.json"
    if target.exists():
        target = target.with_name(f"{target.stem}-{data['recorded_utc'][:19].replace(':', '')}.json")
    write_json(target, data)
    print(json.dumps(data, indent=2))
    print(f"Saved {target}")
