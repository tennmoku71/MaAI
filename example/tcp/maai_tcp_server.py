#!/usr/bin/env python3
"""
TCP runtime entrypoint for MaAI.

Input protocol (single stream for synchronized x1/x2):
  header (24 bytes, little-endian):
    magic(4s='MAA1'), version(B=1), dtype(B:1=float32,2=float64),
    frame_samples(H), seq(I), timestamp_us(Q), payload_len(I)
  payload:
    x1[frame_samples] + x2[frame_samples] with dtype above.

Output protocol:
  MaAI TcpTransmitter binary protocol (length-prefixed payload).
"""

import argparse
import os
import queue
import signal
import socket
import struct
import sys
import threading
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from maai.model import Maai
from maai.input import Base
from maai.output import TcpTransmitter

MAGIC = b"MAA1"
VERSION = 1
DTYPE_FLOAT32 = 1
DTYPE_FLOAT64 = 2
HEADER_FMT = "<4sBBHIQI"
HEADER_SIZE = struct.calcsize(HEADER_FMT)


class _ChannelInput(Base):
    def __init__(self, start_callback):
        super().__init__()
        self._start_callback = start_callback

    def start(self):
        self._start_callback()


class StereoPacketInputServer:
    def __init__(self, ip: str, port: int, ch1: _ChannelInput, ch2: _ChannelInput):
        self.ip = ip
        self.port = port
        self.ch1 = ch1
        self.ch2 = ch2
        self._started = False
        self._start_lock = threading.Lock()

    @staticmethod
    def _recv_exact(conn: socket.socket, size: int):
        data = b""
        while len(data) < size:
            part = conn.recv(size - len(data))
            if not part:
                return None
            data += part
        return data

    def _serve_forever(self):
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.ip, self.port))
                s.listen(1)
                print(f"[IN] Waiting for synchronized x1/x2 packets on {self.ip}:{self.port} ...")

                conn, addr = s.accept()
                print("[IN] Connected by", addr)
                with conn:
                    while True:
                        header = self._recv_exact(conn, HEADER_SIZE)
                        if header is None:
                            raise ConnectionError("Connection closed while receiving header")

                        magic, version, dtype_code, frame_samples, _seq, _ts_us, payload_len = struct.unpack(
                            HEADER_FMT, header
                        )
                        if magic != MAGIC:
                            raise ValueError(f"Invalid magic: {magic!r}")
                        if version != VERSION:
                            raise ValueError(f"Unsupported version: {version}")
                        if frame_samples != self.ch1.FRAME_SIZE:
                            raise ValueError(
                                f"Invalid frame_samples: {frame_samples} (expected {self.ch1.FRAME_SIZE})"
                            )
                        if dtype_code == DTYPE_FLOAT32:
                            dtype = "<f4"
                            bytes_per_sample = 4
                        elif dtype_code == DTYPE_FLOAT64:
                            dtype = "<f8"
                            bytes_per_sample = 8
                        else:
                            raise ValueError(f"Unsupported dtype code: {dtype_code}")

                        expected_payload_len = frame_samples * bytes_per_sample * 2
                        if payload_len != expected_payload_len:
                            raise ValueError(
                                f"Invalid payload_len: {payload_len} (expected {expected_payload_len})"
                            )

                        payload = self._recv_exact(conn, payload_len)
                        if payload is None:
                            raise ConnectionError("Connection closed while receiving payload")

                        arr = np.frombuffer(payload, dtype=dtype, count=frame_samples * 2)
                        if arr.size != frame_samples * 2:
                            raise ValueError("Unexpected payload sample count")

                        x1 = arr[:frame_samples].astype(np.float32).tolist()
                        x2 = arr[frame_samples:].astype(np.float32).tolist()

                        self.ch1._put_to_all_queues(x1)
                        self.ch2._put_to_all_queues(x2)
            except Exception as e:
                print("[IN] Server error:", e)
                time.sleep(0.5)

    def start(self):
        with self._start_lock:
            if self._started:
                return
            threading.Thread(target=self._serve_forever, daemon=True).start()
            self._started = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MaAI TCP runtime")
    parser.add_argument("--mode", default="vap", choices=["vap", "vap_mc", "bc", "bc_2type", "nod", "vap_prompt"])
    parser.add_argument("--lang", default="jp")
    parser.add_argument("--frame-rate", type=int, default=10)
    parser.add_argument("--context-len-sec", type=int, default=20)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])

    parser.add_argument("--input-ip", default="127.0.0.1")
    parser.add_argument("--input-port", type=int, default=5000)

    parser.add_argument("--output-ip", default="127.0.0.1")
    parser.add_argument("--output-port", type=int, default=50008)
    parser.add_argument("--model-path", default=None, help="Optional local .pt model file")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    receiver_ref = {}

    def _start_receiver_once():
        receiver_ref["receiver"].start()

    audio_ch1 = _ChannelInput(_start_receiver_once)
    audio_ch2 = _ChannelInput(_start_receiver_once)
    receiver = StereoPacketInputServer(args.input_ip, args.input_port, audio_ch1, audio_ch2)
    receiver_ref["receiver"] = receiver
    transmitter = TcpTransmitter(ip=args.output_ip, port=args.output_port, mode=args.mode)

    transmitter.start_server()

    maai = Maai(
        mode=args.mode,
        lang=args.lang,
        frame_rate=args.frame_rate,
        context_len_sec=args.context_len_sec,
        audio_ch1=audio_ch1,
        audio_ch2=audio_ch2,
        device=args.device,
        local_model=args.model_path,
    )

    running = True

    def _handle_signal(_sig, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    maai.start()
    print(
        f"[MaAI TCP] running mode={args.mode} lang={args.lang} "
        f"in-sync={args.input_ip}:{args.input_port} "
        f"out={args.output_ip}:{args.output_port}"
    )

    try:
        while running:
            try:
                result = maai.result_dict_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            transmitter.update(result)
    except KeyboardInterrupt:
        running = False
    finally:
        print("[MaAI TCP] shutting down...")
        maai.stop(wait=True, timeout=2.0)

    return 0


if __name__ == "__main__":
    sys.exit(main())
