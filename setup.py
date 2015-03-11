from setuptools import setup


setup(
    name='pyvcd',
    version='0.0.1a1',
    packages=[
        'pyvcd',
    ],
    install_requires=[
        'coverage',
        'lxml',
        'mock',
        'nose',
        'requests',
    ],
)
