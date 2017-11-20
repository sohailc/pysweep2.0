import os
import re
import subprocess
from collections import defaultdict


def make():
    command = "python setup.py bdist_wheel"
    p = subprocess.Popen(command)
    p.communicate()


def get_latest(version_list):

    major_version_dict = defaultdict(list)
    for version in version_list:
        major, minor = version.split(".")
        major_version_dict[major].append(minor)

    max_major = sorted(major_version_dict.keys())[-1]
    max_minor = sorted(major_version_dict[max_major])[-1]

    return "{}.{}".format(max_major, max_minor)


def upload():
    dist_files = os.listdir("dist")
    versions = {}
    for file_name in dist_files:
        result = re.search("pysweep2-([0-9]*\.[0-9]*).+", file_name)

        if result is not None:
            versions[result.groups()[0]] = file_name

    latest_version = get_latest(versions.keys())
    latest_file = versions[latest_version]

    command = "twine upload dist{}{}".format(os.path.sep, latest_file)
    print("Please run the command:")
    print(command)


if __name__ == "__main__":
    make()
    upload()
