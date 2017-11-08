from distutils.core import setup

setup(
    name='pysweep2',
    version='0.1',
    description='Easily sweep QCoDeS parameters',
    author='Sohail Chatoor',
    author_email='a-sochat@microsoft.com',
    url='https://github.com/sohailc/pysweep2.0',
    packages=['pysweep', 'pysweep.data_storage', 'pysweep.docs', 'pysweep.tests']
)