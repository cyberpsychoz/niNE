"""
Build script for niNE client using Panda3D deploy-ng.

Usage:
    python setup.py build_apps

Output will be in build/ directory.
For Windows build from Linux, you need: python setup.py build_apps -p win_amd64
"""

from setuptools import setup

setup(
    name="niNE",
    version="0.1.0",

    options={
        'build_apps': {
            # Main client entry point
            'gui_apps': {
                'niNE': 'client.py',
            },

            # Platforms (build for current platform by default)
            # Use -p flag to override: python setup.py build_apps -p win_amd64
            'platforms': [],

            # Requirements file for dependencies
            'requirements_path': 'requirements-client.txt',

            # Log filename (for debugging)
            'log_filename': 'niNE.log',

            # Plugins to include (Panda3D plugins, not game plugins)
            'plugins': [
                'pandagl',
                'p3openal_audio',
            ],

            # Include patterns for data files
            'include_patterns': [
                'nine/**/*.py',
                'nine/**/*.bam',
                'nine/**/*.png',
                'nine/**/*.jpg',
                'nine/**/*.gif',
                'nine/**/*.ttf',
                'certs/cert.pem',  # Only public cert, NOT key.pem!
                'config.json',
            ],

            # Exclude server-only modules
            'exclude_modules': [
                'nine.server',
                'nine.server.*',
                'nine.core.database',
                'nine.core.world',
                'nine.core.character_controller',
                'bcrypt',
                'bcrypt.*',
                'sqlalchemy',
                'sqlalchemy.*',
                'tinydb',
                'ursina',
                'ursina.*',
            ],

            # Include these packages
            'include_modules': [
                'nine.*',
                'PIL',
                'PIL.*',
            ],
        },
    },
)
