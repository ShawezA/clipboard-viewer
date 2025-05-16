from setuptools import setup

setup(
    name='catppuccin-clipboard-preview',
    version='0.1.0', # You can change this
    scripts=['clipboard_preview.py'],
    # No need to list pygobject or other system dependencies here,
    # Nix will handle them.
)