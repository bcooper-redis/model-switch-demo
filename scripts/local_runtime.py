"""Run the project-local Ollama server with cloud inference disabled."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
binary = ROOT / '.artifacts/ollama-0.17.7/ollama'
if not binary.exists():
    raise SystemExit('Install the official Ollama CLI in .artifacts/ollama-0.17.7 first; see docs/milestone-3.md.')
env = dict(os.environ, OLLAMA_HOST='127.0.0.1:11434', OLLAMA_NO_CLOUD='1',
           OLLAMA_MODELS=str(ROOT / '.artifacts/ollama-models'), OLLAMA_MAX_LOADED_MODELS='1',
           OLLAMA_NUM_PARALLEL='1', OLLAMA_CONTEXT_LENGTH='8192')
args = sys.argv[1:] or ['serve']
# This helper is for explicit local runtime operations; no cloud sign-in or credential handling.
if args[0] not in ('serve', 'pull', 'list', 'ps', 'stop', '--version'):
    raise SystemExit('Supported commands: serve, pull MODEL, list, ps, stop MODEL, --version')
if args[0] == 'pull' and (len(args) != 2 or 'cloud' in args[1].lower()):
    raise SystemExit('Specify one downloaded local model tag.')
os.execve(binary, [str(binary), *args], env)
