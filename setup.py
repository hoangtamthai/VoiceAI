from setuptools import setup

setup(
    name="live_subtitle",
    version="0.1.0",
    py_modules=["main"],
    install_requires=[
        "click",
        "numpy",
        "sounddevice",
        "speechrecognition",
        "torch",
        "pydub",
        "whisper",
    ],
    entry_points={
        "console_scripts": [
            "live_subtitle=main:main",
        ],
    },
)
