from setuptools import setup, find_packages

version_parts = (0, 1, 0, 'a', 26)
version = '.'.join(map(str, version_parts))

setup(
    name='chiasma',
    description='tmux layout renderer',
    version=version,
    author='Torsten Schmits',
    author_email='torstenschmits@gmail.com',
    license='MIT',
    url='https://github.com/tek/chiasma',
    packages=find_packages(exclude=['unit', 'unit.*', 'integration', 'integration.*']),
    install_requires=[
        'amino==13.0.0a28',
        'psutil==5.3.1',
    ],
    tests_require=[
        'kallikrein~=0.22.0a15',
    ],
)
