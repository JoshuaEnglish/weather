from setuptools import setup

setup(
    name='weather',
    version='1.1',
    py_modules=['cli'],
    install_requires=['Click', ],
    entry_points={
        'console_scripts': [
            'weather = cli:main'
            ]
        }
    )
