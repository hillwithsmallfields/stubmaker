#!/usr/bin/env python3

import argparse
import os
import stat

def get_args():
    parser = argparse.ArgumentParser(
        description="""Python program stub generator.
        Produces a file with a place to write your core logic, and provides a command-line caller for it.
        Optionally also provides a web API.
        An accompanying pytest stub is written.
        If you indicate the program should take a config file, a stub for that is also written.
        """)
    parser.add_argument(
        "--args", "-a",
        nargs='*',
        help="""Provide a list of command line arguments to the program.
        If an argument has '%%' at the end, it is treated as supplying an
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
        "--logging", "-l",
        action='store_true',
        help="""Use the 'logging' package.""")
    parser.add_argument(
        "--yaml", "-y",
        action='store_true',
        help="""Import the 'yaml' package, even if none of the input arguments have a .yaml type.""")
    parser.add_argument(
        "--postgresql", "--pg", "-p",
        action='store_true',
        help="""Include setup for postgres.""")
    parser.add_argument(
       "--server", "-s",
        action='store_true',
        help="""Include a simple API server with JSON input and output."""
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
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

def pystub(args, csv, fileinput, json, postgresql, yaml, logging, server, output):
    """Create a stub python program.
    Arguments:
    args: list of arguments to the program and its main function
    output: the file to write the program to
    csv, json, yaml: import these libraries even if not used in file arguments
    fileinput, logging, postgresql, server: use these libraries
    """

    input_args = []
    arg_types = {without_flags(arg_name(arg)): without_flags(arg_type(arg))
                 for arg in (args or {})}
    csv |= 'csv' in arg_types.values()
    json |= 'json' in arg_types.values()
    yaml |= 'yaml' in arg_types.values()
    if server:
        args.extend(['server:', 'host', 'port'])
    prog_name = os.path.splitext(os.path.basename(output))[0]
    prog_dir = os.path.dirname(output)
    if prog_dir:
        os.makedirs(prog_dir, exist_ok=True)

    with open(output, 'w') as outstream:
        outstream.write("#!/usr/bin/env python3\n\n")
        if args:
            outstream.write("import argparse\n")
        if csv:
            outstream.write("import csv\n")
        if fileinput:
            outstream.write("import fileinput")
            args.append("inputspec+")
        if server:
            outstream.write("import flask\n")
        if json:
            outstream.write("import json\n")
        if logging:
            outstream.write("import logging\n")
        if postgresql:
            outstream.write("import psycopg\n")
        outstream.write("import sys\n")
        if yaml:
            outstream.write("import yaml\n")

        if logging:
            outstream.write("\nlogger = logging.getLogger(__name__)\n")

        # Write the argparser details:
        if args:
            outstream.write(
                """\ndef get_args():\n    parser = argparse.ArgumentParser()\n""")
            short_args = set()
            for iarg, arg in enumerate(args):
                argtype = arg_type(arg)
                arg = arg_name(arg)
                short = arg[0]
                extra = ', "-%s"' % (short
                                     if short not in short_args
                                     else (short.upper()
                                           if short.upper() not in short_args
                                           else ""))
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
        outstream.write(
            '''def %s(%s%s%s):\n    """The core logic of the program, usable from the command line or as a python function."""\n'''
            % (prog_name,
               ", ".join([k for k in arg_types.keys() if k not in ['config', 'output']]
                         + [arg for arg in args if arg not in arg_types and arg != 'output']),
               ", config_data" if has_config else "",
               ", conn" if postgresql else ""
               ))
        if postgresql:
            outstream.write("    with conn.cursor() as cur:\n    ")
        outstream.write("""    return foo # TODO: write your main logic here\n\n\n""")

        if server:
            outstream.write("%s_app = flask.Flask('%s')\n" % (prog_name, prog_name))
            outstream.write("@%s_app.route('/%s/', methods=['GET', 'POST'])\n" % (prog_name, prog_name))
            outstream.write("def respond_%s():\n    return flask.jsonify(%s(**flask.request.json()))\n\n\n" % (prog_name, prog_name))

        # write a config_handling wrapper, or 'main' if there is no config:
        outstream.write(
            """def %s_%s(%s%s):\n"""
            % (prog_name,
               "on_files" if has_config else "main",
               ", ".join(args),
               ", config_data" if has_config else ""))

        if args:
            if fileinput:
                outstream.write(
                    """    with fileinput.input(files=inputspec) as instream:\n""")
            elif input_args:
                outstream.write(
                    """    with """
                    + ", ".join("""open(%s) as %s_stream""" % (arg_name(arg), arg_name(arg))
                                for arg in input_args
                                if arg_types.get(arg) not in ('bool', 'int', 'float') and arg != 'config')
                    + (', psycopg.connect("dbname=%s user=%s" % (config["database"], config["datauser"])) as conn' if postgresql else "")
                    + ":\n")
            else:
                outstream.write("""        data = instream.read()\n""")
            outstream.write("""        result = %s(\n""" % prog_name)
            for argname, argtype in arg_types.items():
                if argname not in ('config', 'output'):
                    outstream.write(
                        """            %s=%s,\n"""
                        % (argname,
                           TYPE_READERS.get(argtype, "%s_stream.read()") % argname))
            if postgresql:
                outstream.write("""            conn,\n""")
            if has_config:
                outstream.write("""            config_data=config_data,\n""")
            outstream.write("""        )\n""")

            # write the output after closing the inputs, in case we're
            # writing back to one of the same files:
            if 'output' in args:
                outstream.write("""    with open(output, 'w') as outstream:\n""")
                outstream.write("""        result.save(outstream)\n""")
            outstream.write("""    return result\n""")
        else:
            outstream.write("""    pass\n\n""")

        # if we're using a config-handling wrapper, write a main
        # function to call it; otherwise we will have written 'main'
        # above:
        if has_config:
            outstream.write("""\n\ndef %s_main(**args):\n""" % prog_name)
            outstream.write("""    with open(args['config']) as confstream:\n""")
            outstream.write("""        config = yaml.safeload(confstream)\n""")
            outstream.write("""        config['args'].update({v: os.environ[v.upper()] for v in config['args'].keys() if v.upper() in os.environ}).update(args)\n""")
            if server:
                outstream.write("""        if config['args']['server']:\n""")
                outstream.write("""            %s_app.run(host=args['host'], port=int(args['port']))\n""" % prog_name)
                outstream.write("""        else:\n    """)
            outstream.write("""        %s_on_files(**config['args'], config_data=config)\n"""
                            % prog_name)

        # write the executable boilerplate:
        outstream.write("""\nif __name__ == "__main__":\n""")
        outstream.write("""    try:\n""")
        outstream.write("""        %s_main(**get_args())\n        sys.exit(0)\n""" % prog_name)
        outstream.write("""    except Exception:\n        sys.exit(1)\n""")

    os.chmod(output, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)

    test_dir = os.path.join(prog_dir, "test")
    os.makedirs(test_dir, exist_ok=True)
    with open(os.path.join(test_dir, "test_%s.py" % prog_name), 'w') as test_stream:
        test_stream.write("import %s\n\n" % prog_name)
        test_stream.write("def test_%s():\n    assert %s(\n" % (prog_name, prog_name))
        for arg in args:
            test_stream.write("        %s=None,\n" % arg)
        test_stream.write("    ) == 'expected_result'\n")

    if has_config:
        with open(os.path.join(prog_dir, prog_name+"_conf.yaml"), 'w') as conf_stream:
            conf_stream.write("args:\n")
            for arg in args:
                if arg != 'config':
                    conf_stream.write("    %s: default value for %s\n" % (arg, arg))

if __name__ == "__main__":
    pystub(**get_args())
