#!/usr/bin/env python3
"""
This script is an example of how to use the VapGPT model with two WAV files.
"""

import sys
import os
import argparse

# For debugging purposes, you can uncomment the following line to add the src directory to the path.
# This allows you to import modules from the src directory without pip installing the package.
# Uncomment the line below if you need to run this script directly without installing the package.

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/')))

from maai import Maai, MaaiInput, MaaiOutput


def _str2bool(value: str) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def parse_args():
    parser = argparse.ArgumentParser(description="Console bar viewer for MaAI")
    parser.add_argument("--sample-play", default="true", help="true: run local WAV sample, false: monitor TCP server")
    parser.add_argument("--mode", default="vap", choices=["vap", "vap_mc", "bc_2type", "nod", "vap_prompt"])
    parser.add_argument("--lang", default="jp")
    parser.add_argument("--frame-rate", type=int, default=10)
    parser.add_argument("--context-len-sec", type=int, default=5)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--ip", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50008)
    parser.add_argument("--wav1", default="../wav_sample/jpn_inoue_16k.wav")
    parser.add_argument("--wav2", default="../wav_sample/jpn_sumida_16k.wav")
    return parser.parse_args()


def test():
    args = parse_args()
    sample_play = _str2bool(args.sample_play)

    output = MaaiOutput.ConsoleBar(bar_type="balance")

    if sample_play:
        wav1 = MaaiInput.Wav(wav_file_path=args.wav1)
        wav2 = MaaiInput.Wav(wav_file_path=args.wav2)

        maai = Maai(
            mode=args.mode,
            lang=args.lang,
            frame_rate=args.frame_rate,
            context_len_sec=args.context_len_sec,
            audio_ch1=wav1,
            audio_ch2=wav2,
            device=args.device,
        )

        maai.start()
        while True:
            result = maai.get_result()
            output.update(result)
    else:
        receiver = MaaiOutput.TcpReceiver(ip=args.ip, port=args.port, mode=args.mode)
        receiver.start()
        print(f"[Monitor] waiting for TCP output on {args.ip}:{args.port} (mode={args.mode})")
        while True:
            result = receiver.get_result()
            output.update(result)


if __name__ == "__main__":
    test()