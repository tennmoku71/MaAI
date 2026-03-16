# MaAI TCP-only Nuitka build

`build/nuitka/maai_tcp_server.py` is a TCP-only runtime entrypoint:

- Audio input: TCP (`float64` by default, or `--input-float32`)
- Audio channel 2: `Zero`
- Output: TCP via MaAI binary protocol

## Build

### macOS (verified)

Run from the repository root:

```bash
PYTHONPATH="$(pwd)/src" python3 -m nuitka build/nuitka/maai_tcp_server.py \
  --standalone \
  --follow-imports \
  --enable-plugin=torch \
  --enable-plugin=numpy \
  --enable-plugin=anti-bloat \
  --module-parameter=torch-disable-jit=yes \
  --no-deployment-flag=excluded-module-usage \
  --nofollow-import-to=pytest,IPython,setuptools,pyaudio \
  --include-package=numpy \
  --noinclude-setuptools-mode=nofollow \
  --jobs=8 \
  --show-progress \
  --output-dir=dist
```

Binary output: `dist/maai_tcp_server.dist/maai_tcp_server.bin`

### Windows (PowerShell)

Run from the repository root. On first run, Nuitka may prompt to download a C compiler (MinGW64)—accept to continue.

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m nuitka build/nuitka/maai_tcp_server.py `
  --standalone `
  --follow-imports `
  --enable-plugin=torch `
  --enable-plugin=numpy `
  --enable-plugin=anti-bloat `
  --module-parameter=torch-disable-jit=yes `
  --no-deployment-flag=excluded-module-usage `
  --nofollow-import-to=pytest,IPython,setuptools,pyaudio `
  --include-package=numpy `
  --noinclude-setuptools-mode=nofollow `
  --jobs=8 `
  --show-progress `
  --output-dir=dist
```

Binary output: `dist\maai_tcp_server.dist\maai_tcp_server.exe`

### Windows (CMD)

```cmd
set PYTHONPATH=%cd%\src
python -m nuitka build/nuitka/maai_tcp_server.py --standalone --follow-imports --enable-plugin=torch --enable-plugin=numpy --enable-plugin=anti-bloat --module-parameter=torch-disable-jit=yes --no-deployment-flag=excluded-module-usage --nofollow-import-to=pytest,IPython,setuptools,pyaudio --include-package=numpy --noinclude-setuptools-mode=nofollow --jobs=8 --show-progress --output-dir=dist
```

## Run

### macOS / Linux

```bash
./dist/maai_tcp_server.dist/maai_tcp_server.bin \
  --mode vap \
  --lang jp \
  --frame-rate 10 \
  --input-ip 127.0.0.1 \
  --input-port 5000 \
  --output-ip 127.0.0.1 \
  --output-port 50008
```

### Windows (PowerShell)

```powershell
.\dist\maai_tcp_server.dist\maai_tcp_server.exe `
  --mode vap `
  --lang jp `
  --frame-rate 10 `
  --input-ip 127.0.0.1 `
  --input-port 5000 `
  --output-ip 127.0.0.1 `
  --output-port 50008
```

Useful flags:

- `--input-float32`: receive `float32` audio frames instead of `float64`
- `--input-client-mode`: connect to an external TCP input server instead of listening
- `--model-path /path/to/model.pt`: use local model file (on Windows e.g. `C:\path\to\model.pt`)

## Quick verification

**macOS / Linux:**

```bash
./dist/maai_tcp_server.dist/maai_tcp_server.bin --help
```

**Windows:**

```powershell
.\dist\maai_tcp_server.dist\maai_tcp_server.exe --help
```

## Troubleshooting

If the exe fails with **NumPy** (`No module named 'numpy.core._multiarray_umath'`) or **unittest.mock** (`Unexpected failure of hard import of 'unittest.mock'`), rebuild with the options in this README: do **not** put `unittest` in `--nofollow-import-to`, and add `--include-package=numpy`. Then run the exe again.

The above build/run combination was validated with:

- process startup (`--help`)
- TCP listen on input/output ports
- audio frame send to input TCP port
- inference packet receive from output TCP port
- Windows: standalone exe run from a copied folder (no Python/pip on run path)
