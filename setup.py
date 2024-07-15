from setuptools import setup

setup(
    name='weather',
    version='1.2',
    author="Joshua English",
    author_email="josh@joshuarenglish.com",
    py_modules=['cli'],
    install_requires=['Click', 'Sphinx-Click', 'sphinx-autodoc-annotation',
                      'pytz', 'requests'],
    entry_points={
        'console_scripts': [
            'weather = cli:main'
            ]
        }
    )
