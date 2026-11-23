"""Inspect in the engine's own environment without loading the synthesis model."""
import argparse
import json
from .catalog import inspect_engine

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('kokoro', 'melo'), required=True)
    print(json.dumps(inspect_engine(parser.parse_args().engine), ensure_ascii=False))
