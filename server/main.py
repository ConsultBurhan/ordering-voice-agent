import os
import sys

# Suppress NLTK CWD security check
os.environ.setdefault("NLTK_DISABLE_IMPORT_SECURITY", "1")

# Make sure src.voice.pipeline is imported so Pipecat runner finds the `bot` function
from src.voice.pipeline import bot

if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
