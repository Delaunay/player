#!/usr/bin/env python
from setuptools import setup


if __name__ == '__main__':
    setup(
        name='player',
        version='0.0.0',
        description='Python Video Player',
        author='Pierre Delaunay',
        package_data={
            "player.binaries.win64": [
                'player/binaries/win64'
            ]
        },
        entry_points={
            'console_scripts': [
                'player = player.player:main',
            ],
        },
        packages=[
            'player',
        ],
        setup_requires=['setuptools'],
    )
