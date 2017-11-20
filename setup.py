from setuptools import find_packages, setup


def bump_version(version_string):
    parts = [int(i) for i in version_string.split(".")]
    parts[-1] += 1
    bumped_version_string = ".".join([str(i) for i in parts])
    return bumped_version_string


def perform_setup():

    with open("version", "r+") as fh:
        version_string = fh.read()
        fh.seek(0)
        fh.write(bump_version(version_string))

    setup(
        name='pysweep2',
        version=version_string,
        description='Easily sweep QCoDeS parameters',
        license='MIT',
        author='Sohail Chatoor',
        author_email='a-sochat@microsoft.com',
        url='https://github.com/sohailc/pysweep2.0',
        packages=find_packages(),
        python_requires='>=3',
    )


if __name__ == "__main__":
    perform_setup()
