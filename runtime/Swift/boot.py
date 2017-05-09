#! /usr/bin/python

"""
Find all .g4 files and generate parsers in the same directory.
the antlr used should be the one located at user's mvn directory
the filename is antlr4-ANTLR_VERSION-SNAPSHOT.jar. You can get it
by running: "mvn install"

NOTE: In case of customized location of .m2 folder, you can change the
USER_M2 constant below.

the java version is used according to environment variable $JAVA_HOME.
"""

import shutil
import argparse
import fnmatch
import os.path
import time
from subprocess import call

ANTLR_MAJOR_VERSION = "4"
ANTLR_MINOR_VERSION = "7"
ANTLR_RELEASE = "0" # Placeholder which required by SPM to work.
ANTLR_VERSION = ANTLR_MAJOR_VERSION + "." + ANTLR_MINOR_VERSION
USER_M2 = os.path.expanduser("~") + "/.m2/"
ANTLR4_FOLDER = USER_M2 + "repository/org/antlr/antlr4/" + ANTLR_VERSION + "-SNAPSHOT/"
ANTLR4_JAR = ANTLR4_FOLDER + "antlr4-" + ANTLR_VERSION + "-SNAPSHOT-complete.jar"
TMP_FOLDER = "/tmp/"
DIR = os.path.dirname(os.path.realpath(__file__))

# Colors
RED = "\033[91;1m"
GREEN = "\033[32;1m"
YELLOW = "\033[93;1m"
CYAN = "\033[36;1m"
GREY = "\033[38;2;127;127;127m"
RESET = "\033[0m"


def jar_exists():
    """
    Finds the antlr4 jar.
    """
    return os.path.exists(ANTLR4_JAR)


def find_g4():
    """
    Find all g4 files and return a list of them.
    The recursive search starts from the directory containing
    this python file.
    """
    file_path = os.path.realpath(__file__)
    parent_folder = file_path[0:file_path.rindex("/") + 1]
    res = []
    for cur, _, filenames in os.walk(parent_folder):
        cur_files = fnmatch.filter(filenames, "*.g4")
        res += [cur + "/" + cur_file for cur_file in cur_files]
    return res


def gen_parser(grammar):
    """
    Generate parser for the input g4 file.
    """
    grammar_folder = grammar[0:grammar.rindex("/") + 1]
    java_home = os.environ["JAVA_HOME"]
    java = java_home + "/bin/java"
    if not os.path.exists(java):
        antlr_complains("Cannot find java. Check your JAVA_HOME setting.")
        return

    call([java, "-jar", ANTLR4_JAR,
          "-Dlanguage=Swift", grammar, "-visitor",
          "-o", grammar_folder + "/gen"])


def swift_test():
    """
    Run unit tests.
    """
    generate_parser()
    call(["swift", "test"])


def get_argument_parser():
    """
    Initialize argument parser.
    :return: the argument parser
    """
    p = argparse.ArgumentParser(description="Helper script for ANTLR4 Swift target. "
                                            "<DEVELOPER> flag means the command is mostly used by a developer. "
                                            "<USER> flag means the command should be used by user. ")
    p.add_argument("--gen-spm-module",
                   action="store_true",
                   help="<USER> Generates a Swift Package Manager flavored module. "
                        "Use this command if you want to include ANTLR4 as SPM dependency.", )
    p.add_argument("--gen-xcodeproj",
                   action="store_true",
                   help="<DEVELOPER> Generates an Xcode project for ANTLR4 Swift runtime. "
                        "This directive will generate all the required parsers for the project. "
                        "Feel free to re-run whenever you updated the test grammar files.")
    p.add_argument("--test",
                   action="store_true",
                   help="<DEVELOPER> Run unit tests.")
    return p


def generate_spm_module(in_folder=TMP_FOLDER):
    """
    Generate spm module in the specified folder, default
    to the system's tmp folder.

    After generation, user can simply use the prompt SPM
    code to include the ANTLR4 Swift runtime package.
    :param in_folder: the folder where we generate the SPM module.
    :return: None
    """

    tmp_antlr_folder = in_folder + "Antlr4-tmp-" + str(int(time.time()))
    os.mkdir(tmp_antlr_folder)

    # Copy folders and SPM manifest file.
    dirs_to_copy = ["Sources", "Tests"]
    for dir_to_copy in dirs_to_copy:
        shutil.copytree(DIR + "/" + dir_to_copy, tmp_antlr_folder + "/" + dir_to_copy)

    shutil.copy("Package.swift", tmp_antlr_folder)

    os.chdir(tmp_antlr_folder)
    call(["git", "init"])
    call(["git", "add", "*"])
    call(["git", "commit", "-m", "Initial commit."])
    call(["git", "tag", ANTLR_VERSION + "." + ANTLR_RELEASE])

    antlr_says("Created local repository.")
    antlr_says("Put .Package(url: \"{}\", majorVersion: {}) in your project dependencies.".format(os.getcwd(),
                                                                                                  ANTLR_MAJOR_VERSION))


def generate_xcodeproj():
    """
    Generates the ANTLR4 Swift runtime Xcode project.

    This method will also generate parsers required by
    the runtime tests.
    :return:
    """
    generate_parser()
    call(["swift", "package", "generate-xcodeproj"])


def generate_parser():
    if not jar_exists():
        antlr_complains("Run \"mvn install\" in antlr4 project root first or check mvn settings")
        exit()

    _ = [gen_parser(f) for f in find_g4()]


def antlr_says(msg):
    print GREEN + "[ANTLR] " + msg + RESET


def antlr_complains(msg):
    print RED + "[ANTLR] " + msg + RESET


if __name__ == "__main__":
    parser = get_argument_parser()
    args = parser.parse_args()
    if args.gen_spm_module:
        generate_spm_module()
    elif args.gen_xcodeproj:
        generate_xcodeproj()
    elif args.test:
        swift_test()
    else:
        parser.print_help()
