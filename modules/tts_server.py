import numpy as np
import sounddevice
import torch
from pydub import AudioSegment
from TTS.api import TTS

# Get device
device = "cuda" if torch.cuda.is_available() else "cpu"

print(sounddevice.query_devices())
# List available 🐸TTS models
print(TTS().list_models())

audioSegment: AudioSegment = AudioSegment.from_wav("output.wav")
print(audioSegment.channels)
audio_array = np.ndarray(
    (int(audioSegment.frame_count()), audioSegment.channels),  # type: ignore
    buffer=audioSegment.raw_data,
    dtype=np.int16,
)
sounddevice.play(audio_array, audioSegment.frame_rate, device=6)
# Init TTS
try:
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    # Run TTS
    # ❗ Since this model is multi-lingual voice cloning model, we must set the target speaker_wav and language
    # Text to speech list of amplitude values as output
    # wav = tts.tts(text="Hello world!", speaker_wav="input.wav", language="en")
    # Text to speech to a file
    tts.tts_to_file(
        text="Hello. How is your day?",
        speaker_wav="input_2.wav",
        language="en",
        file_path="output.wav",
    )
except Exception as e:
    print(e)
