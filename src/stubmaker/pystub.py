#!/usr/bin/env python3

import argparse
import os

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--args", "-a",
        nargs='*',
        help="""Provide a list of command line arguments to the program.
        If an argument has '%' at the end, it is treated as supplying an
        input filename, and a reader is provided.
        An argument name may have '.csv', '.json', or '.yaml' at the end of it,
        in which case the appropriate way of reading the file is used.
        An argument with ':' at the end is treated as a boolean flag.
        The arguments 'config' and 'output' are treated specially.
        """)
    parser.add_argument(
        "--fileinput", "-f",
        action='store_true',
        help="""Use the fileinput package to read multiple files seamlessly.""")
    parser.add_argument(
        "--csv", "-c",
        action='store_true',
        help="""Import the 'csv' package, even if none of the input arguments have a .csv type.""")
    parser.add_argument(
        "--json", "-j",
        action='store_true',
        help="""Import the 'json' package, even if none of the input arguments have a .json type.""")
    parser.add_argument(
        "--yaml", "-y",
        action='store_true',
        help="""Import the 'yaml' package, even if none of the input arguments have a .yaml type.""")
    parser.add_argument(
        "--output", "-o",
        help="""The name of the file to write the resulting program to.""")
    return vars(parser.parse_args())

def without_flags(arg):
    return arg.removesuffix('+').removesuffix('*').removesuffix(':').removesuffix('%') if arg else arg

def arg_name(arg):
    """Return the name part of an arg."""
    return arg.split('.')[0]

def arg_type(arg):
    """Return the type part of an arg."""
    return arg.split('.')[1] if '.' in arg else None

TYPE_READERS = {
    'csv': "[f(x) for x in csv.DictReader(%s_stream)]",
    'json': "json.load(%s_stream)",
    'yaml': "yaml.safeload(%s_stream)",
    'bool': "%s",
    }

def pystub(args, csv, fileinput, json, yaml, output):
    input_args = []
    arg_types = {without_flags(arg_name(arg)): without_flags(arg_type(arg)) for arg in args}
    csv |= 'csv' in arg_types.values()
    json |= 'json' in arg_types.values()
    yaml |= 'yaml' in arg_types.values()
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
        if json:
            outstream.write("import json\n")
        if yaml:
            outstream.write("import yaml\n")

        # Write the argparser details:
        if args:
            outstream.write("""\ndef get_args():\n    parser = argparse.ArgumentParser()\n""")
            short_args = set()
            for iarg, arg in enumerate(args):
                argtype = arg_type(arg)
                arg = arg_name(arg)
                short = arg[0]
                extra = ', "-%s"' % short if short not in short_args else ""
                short_args.add(short)
                action = ""
                if arg.endswith("+") or (argtype and argtype.endswith("+")):
                    action = ", action='append'"
                    arg = arg.removesuffix("+")
                elif arg.endswith("*") or (argtype and argtype.endswith("*")):
                    action = ", nargs='*'"
                    arg = arg.removesuffix("*")
                elif arg.endswith(":"):
                    action = ", action='store_true'"
                    arg = arg.removesuffix(":")
                    arg_types[arg] = 'bool'
                    input_args.append(arg)
                elif arg.endswith("%") or (argtype and argtype.endswith("%")):
                    arg = arg.removesuffix("%")
                    input_args.append(arg)
                args[iarg] = arg
                outstream.write("""    parser.add_argument("%s%s"%s%s)\n""" %
                                ("" if iarg == len(args) - 1 else "--",
                                 arg, extra, action))
            outstream.write("""    return vars(parser.parse_args())\n\n\n""")

        # write the stub for the central logic:
        has_config = 'config' in args and yaml
        outstream.write("""def %s(%s%s):\n    return foo\n\n\n"""
                        % (progname,
                           ", ".join([k for k in arg_types.keys() if k != 'output']
                                     + [arg for arg in args if arg not in arg_types and arg != 'output']),
                           ", config_data" if has_config else ""
                           ))

        # write a config_handling wrapper:
        outstream.write("""def %s_%s(%s%s):\n""" % (progname,
                                                    "on_files" if has_config else "main",
                                                    ", ".join(args),
                                                    ", config_data" if has_config else ""))
        if args:
            if fileinput:
                outstream.write("""    with fileinput.input(files=inputspec) as instream:\n""")
            elif input_args:
                outstream.write("""    with """
                                + ", ".join("""open(%s) as %s_stream""" % (arg_name(arg), arg_name(arg))
                                            for arg in input_args
                                            if arg_types.get(arg) not in ('bool', 'int', 'float') and arg != 'config')
                                + ":\n")
            else:
                outstream.write("""        data = instream.read()\n""")
            outstream.write("""        result = %s(\n""" % progname)
            for argname, argtype in arg_types.items():
                if argname not in ('config', 'output'):
                    outstream.write("""            %s=%s,\n""" % (argname,
                                                                  TYPE_READERS.get(argtype, "%s_stream.read()") % argname))
            if has_config:
                outstream.write("""            config_data=config_data,\n""")
            outstream.write("""        )\n""")
            if 'output' in args:
                outstream.write("""    with open(output, 'w') as outstream:\n""")
                outstream.write("""        result.save(outstream)\n""")
            outstream.write("""    return result\n""")
        else:
            outstream.write("""    pass\n\n""")

        # write a main function:
        if has_config:
            outstream.write("""\n\ndef %s_main(**args):\n""" % progname)
            outstream.write("""    with open(config) as confstream:\n""")
            outstream.write("""        config = yaml.safeload(confstream)\n""")
            outstream.write("""        config['args'].update(args)\n""")
            outstream.write("""        %s_on_files(**config['args'], config_data=config):\n""" % progname)

        # write the executable boilerplate:
        outstream.write("""\nif __name__ == "__main__":\n""")
        outstream.write("""    %s_main(**get_args())\n""" % progname)

if __name__ == "__main__":
    pystub(**get_args())
