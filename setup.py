from setuptools import setup

setup(
    name='weather',
    version='1.1',
    py_modules=['cli'],
    install_requires=['Click', 'Sphinx-Click', 'sphink-autodoc-annotation',
                      'pytz', 'requests'],
    entry_points={
        'console_scripts': [
            'weather = cli:main'
            ]
        }
    )
