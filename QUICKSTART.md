# Quickstart (standalone binary)

> **Current support status:** the prebuilt standalone binary flow in this guide is **macOS-only for now**.

This guide explains how to run the prebuilt standalone binary and connect it from an external app (for example, Node.js) over TCP.

## 1) Unpack the distribution zip

```bash
cd /path/to/MaAI
unzip dist/maai_tcp_server-macos-arm64.zip -d dist
```

Binary path after extraction:

```text
dist/maai_tcp_server.dist/maai_tcp_server.bin
```

## 2) First-run check on macOS

Check startup with:

```bash
./dist/maai_tcp_server.dist/maai_tcp_server.bin --help
```

If macOS blocks execution due to quarantine attributes:

```bash
xattr -dr com.apple.quarantine ./dist/maai_tcp_server.dist
```

## 3) Start the server

```bash
./dist/maai_tcp_server.dist/maai_tcp_server.bin \
  --mode vap \
  --lang jp \
  --frame-rate 10 \
  --device cpu \
  --input-ip 127.0.0.1 \
  --input-port 5000 \
  --output-ip 127.0.0.1 \
  --output-port 50008
```

Key options:

- `--input-port`: TCP port for incoming audio frames
- `--output-port`: TCP port for outgoing inference results
- `--input-float32`: receive audio as `float32` (default is `float64`)
- `--input-client-mode`: connect to an external input server instead of listening
- `--model-path /path/to/model.pt`: use a local model file

## 4) Input frame format

- Sampling rate: 16 kHz
- Frame size: 160 samples (10 ms)
- Default: `float64` little-endian
- With `--input-float32`: `float32` little-endian

Per frame:

- default: `160 * 8 = 1280` bytes
- `--input-float32`: `160 * 4 = 640` bytes

## 5) Minimal connectivity test

This script sends silent frames to the input port and receives one inference packet from the output port.

```bash
python3 - <<'PY'
import socket
import struct
import time

HOST = "127.0.0.1"
IN_PORT = 5000
OUT_PORT = 50008

out_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
out_sock.connect((HOST, OUT_PORT))
print("connected: output")

in_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
in_sock.connect((HOST, IN_PORT))
print("connected: input")

frame = b"".join(struct.pack("<d", 0.0) for _ in range(160))  # float64
for _ in range(120):  # about 12 seconds
    in_sock.sendall(frame)
    time.sleep(0.1)

size_b = out_sock.recv(4)
size = int.from_bytes(size_b, "little")
payload = b""
while len(payload) < size:
    chunk = out_sock.recv(size - len(payload))
    if not chunk:
        break
    payload += chunk

print("received bytes:", len(payload), "expected:", size)
in_sock.close()
out_sock.close()
PY
```

If `received bytes` equals `expected`, the basic TCP pipeline is working.

## 6) Node.js integration notes

- Send frames every 10 ms from Node.js
- Use `float64 LE` by default, or `float32 LE` with `--input-float32`
- Parse output as: `4-byte payload length` + `payload bytes`
- Align your parser with MaAI's TCP result serialization (`TcpReceiver` behavior)

## 7) Troubleshooting

- Execution blocked: run `xattr -dr com.apple.quarantine ./dist/maai_tcp_server.dist`
- Port conflict: `lsof -nP -iTCP:5000 -iTCP:50008`
- Startup check: `./dist/maai_tcp_server.dist/maai_tcp_server.bin --help`
