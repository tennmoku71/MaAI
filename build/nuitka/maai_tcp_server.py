#!/usr/bin/env python3
"""
TCP-only runtime entrypoint for MaAI.

This process:
  - receives audio frames over TCP (channel 1)
  - uses Zero input for channel 2
  - runs MaAI inference
  - transmits inference results over TCP
"""

import argparse
import signal
import sys
import time

from maai.model import Maai
from maai.input import Tcp, Zero
from maai.output import TcpTransmitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MaAI TCP-only runtime")
    parser.add_argument("--mode", default="vap", choices=["vap", "vap_mc", "bc", "bc_2type", "nod", "vap_prompt"])
    parser.add_argument("--lang", default="jp")
    parser.add_argument("--frame-rate", type=int, default=10)
    parser.add_argument("--context-len-sec", type=int, default=20)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])

    parser.add_argument("--input-ip", default="127.0.0.1")
    parser.add_argument("--input-port", type=int, default=5000)
    parser.add_argument("--input-float32", action="store_true", help="Receive input audio as float32 frames")
    parser.add_argument("--input-client-mode", action="store_true", help="Connect to input server instead of listening")

    parser.add_argument("--output-ip", default="127.0.0.1")
    parser.add_argument("--output-port", type=int, default=50008)
    parser.add_argument("--model-path", default=None, help="Optional local .pt model file")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    audio_ch1 = Tcp(
        ip=args.input_ip,
        port=args.input_port,
        recv_float32=args.input_float32,
        client_mode=args.input_client_mode,
    )
    audio_ch2 = Zero()
    transmitter = TcpTransmitter(ip=args.output_ip, port=args.output_port, mode=args.mode)

    audio_ch1.start_server()
    time.sleep(0.5)
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
        f"in={args.input_ip}:{args.input_port} out={args.output_ip}:{args.output_port}"
    )

    try:
        while running:
            result = maai.get_result()
            transmitter.update(result)
    finally:
        maai.stop(wait=True, timeout=2.0)

    return 0


if __name__ == "__main__":
    sys.exit(main())
