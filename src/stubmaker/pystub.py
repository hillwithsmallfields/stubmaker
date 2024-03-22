#!/usr/bin/env python3

import argparse
import os

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--args", "-a", nargs='*')
    parser.add_argument("--csv", "-c", action='store_true')
    parser.add_argument("--fileinput", "-f", action='store_true')
    parser.add_argument("--json", "-j", action='store_true')
    parser.add_argument("--yaml", "-y", action='store_true')
    parser.add_argument("output")
    return vars(parser.parse_args())

def pystub(args, csv, fileinput, json, yaml, output):
    with open(output, 'w') as outstream:
        progname = os.path.splitext(os.path.basename(output))[0]
        outstream.write("#!/usr/bin/env python3\n\n")
        if args:
            outstream.write("import argparse\n")
        if csv:
            outstream.write("import csv\n")
        if fileinput:
            outstream.write("import fileinput")
            args.append("inputspec+")
        else:
            args.append("inputspec+")
        if json:
            outstream.write("import json\n")
        if yaml:
            outstream.write("import yaml\n")
        if args:
            outstream.write("""\ndef get_args():\n    parser = argparse.ArgumentParser()\n""")
            short_args = set()
            for iarg, arg in enumerate(args):
                short = arg[0]
                extra = ', "-%s"' % short if short not in short_args else ""
                short_args.add(short)
                action = ""
                if arg.endswith("+"):
                    action = ", action='append'"
                    arg = arg.removesuffix("+")
                if arg.endswith("*"):
                    action = ", nargs='*'"
                    arg = arg.removesuffix("*")
                if arg.endswith(":"):
                    action = ", action='store_true'"
                    arg = arg.removesuffix(":")
                args[iarg] = arg
                outstream.write("""    parser.add_argument("%s%s"%s%s)\n""" %
                                ("" if iarg == len(args) - 1 else "--",
                                 arg, extra, action))
            outstream.write("""    return vars(parser.parse_args())\n\n""")
        outstream.write("""def %s(%s):\n""" % (progname,
                                            ", ".join(args)))
        if args and (csv or json or yaml):
            has_config = 'config' in args and yaml
            if has_config:
                outstream.write("""    with open(config) as confstream:\n""")
                outstream.write("""        config = yaml.safeload(confstream)\n""")
            if fileinput:
                outstream.write("""    with fileinput.input(files=inputspec) as instream:\n""")
            else:
                outstream.write("""    with open(inputspec) as instream:\n""")
            if csv:
                outstream.write("""        data = [f(x) for x in csv.DictReader(instream)]\n""")
            elif json:
                outstream.write("""        data = json.load(instream)\n""")
            elif yaml and not has_config:
                outstream.write("""        data = yaml.safeload(instream)\n""")
            if 'output' in args:
                outstream.write("""    with open(output) as outstream:\n""")
                outstream.write("""        outstream.write(data)\n""")
        else:
            outstream.write("""    pass\n\n""")
        outstream.write("""\nif __name__ == "__main__":\n""")
        outstream.write("""    %s(**args)\n""" % progname)

if __name__ == "__main__":
    pystub(**get_args())
