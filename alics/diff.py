#!/usr/bin/env python3

from colorama import Fore, Back, Style, init
import difflib
import json
import argparse


def color(diff):
    for line in diff:
        if line.startswith('+'):
            yield Fore.GREEN + line + Fore.RESET
        elif line.startswith('-'):
            yield Fore.RED + line + Fore.RESET
        elif line.startswith('^'):
            yield Fore.BLUE + line + Fore.RESET
        else:
            yield line


def color_diff(obj1, obj2):
    init()
    diff = difflib.ndiff(json.dumps(obj1, indent=True, sort_keys=True).splitlines(), json.dumps(obj2, indent=True, sort_keys=True).splitlines())
    print('\n'.join(color(diff)))


def color_diff_text(text1, text2):
    init()
    diff = difflib.ndiff(text1.splitlines(), text2.splitlines())
    print('\n'.join(color(diff)))


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
      python3 diff.py 1.txt 2.txt
      python3 diff.py 1.txt 2.txt -m json
    """)
    parser.add_argument("file1", help="file1")
    parser.add_argument("file2", help="file2")
    parser.add_argument("-m", "--mode", default="text", help="text")
    args = parser.parse_args()
    if args.mode == "text":
        color_diff_text(open(args.file1).read(), open(args.file2).read())
    elif args.mode == "json":
        color_diff(json.loads(open(args.file1).read()), json.loads(open(args.file2).read()))


if __name__ == "__main__":
    main()
