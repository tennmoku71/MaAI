# MaAI TCP-only Nuitka build

`build/nuitka/maai_tcp_server.py` is a TCP-only runtime entrypoint:

- Audio input: TCP (`float64` by default, or `--input-float32`)
- Audio channel 2: `Zero`
- Output: TCP via MaAI binary protocol

## Build

Verified working command (macOS, standalone + torch):

```bash
PYTHONPATH="$(pwd)/src" python3 -m nuitka build/nuitka/maai_tcp_server.py \
  --standalone \
  --follow-imports \
  --enable-plugin=torch \
  --enable-plugin=numpy \
  --enable-plugin=anti-bloat \
  --module-parameter=torch-disable-jit=yes \
  --no-deployment-flag=excluded-module-usage \
  --nofollow-import-to=pytest,IPython,setuptools,unittest,pyaudio \
  --noinclude-setuptools-mode=nofollow \
  --jobs=8 \
  --show-progress \
  --output-dir=dist
```

Binary output:

```text
dist/maai_tcp_server.dist/maai_tcp_server.bin
```

## Run

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

Useful flags:

- `--input-float32`: receive `float32` audio frames instead of `float64`
- `--input-client-mode`: connect to an external TCP input server instead of listening
- `--model-path /path/to/model.pt`: use local model file

## Quick verification

```bash
./dist/maai_tcp_server.dist/maai_tcp_server.bin --help
```

The above build/run combination was validated with:

- process startup (`--help`)
- TCP listen on input/output ports
- audio frame send to input TCP port
- inference packet receive from output TCP port
