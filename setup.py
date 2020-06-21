
from distutils.core import setup

setup(
    name='hirnoty',
    description='A simple telegram bot for executing scripts and getting' \
                ' notifications',
    version='0.2',
    packages=['hirnoty',],
    install_requires=['aiogram',
                      'pyzmq'],
    scripts=['hirnoty-ctl', 'hirnoty-send']
)

