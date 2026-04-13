import io
import os
import queue
import tempfile
import threading
import time

import click
import keyboard
import numpy as np
import speech_recognition as sr
import torch
import whisper
from pydub import AudioSegment

from modules.tkinter_text import start_app
from modules.translate import translate


def record_audio(
    audio_queue, energy, pause, dynamic_energy, save_file, temp_dir, record_timeout
):
    # load the speech recognizer and set the initial energy threshold and pause threshold
    r = sr.Recognizer()
    r.energy_threshold = energy
    r.pause_threshold = pause
    r.dynamic_energy_threshold = dynamic_energy
    r.operation_timeout = record_timeout
    # r.non_speaking_duration = 0.05

    with sr.Microphone(device_index=1) as source:
        # print("Adjusting for ambient noise...")
        # r.adjust_for_ambient_noise(source, duration=5)
        print("Finish adjusting")
        i = 0
        while True:
            # get and save audio to wav file
            print("Listening...")
            audio = r.listen(source, phrase_time_limit=record_timeout)
            if save_file:
                data = io.BytesIO(audio.get_wav_data())
                audio_clip = AudioSegment.from_file(data)
                filename = os.path.join(temp_dir, f"temp{i}.wav")
                print(filename)
                audio_clip.export(filename, format="wav")
                audio_data = filename
            else:
                torch_audio = torch.from_numpy(
                    np.frombuffer(audio.get_raw_data(), np.int16)
                    .flatten()
                    .astype(np.float32)
                    / 32768.0
                )
                audio_data = torch_audio
            print("Audio recored")
            audio_queue.put_nowait(audio_data)
            i += 1


def transcribe_forever(
    audio_queue, result_queue, audio_model: whisper.Whisper, english, verbose, save_file
):
    while True:
        audio_data = audio_queue.get()
        print("Transcribing...")
        if english:
            result = audio_model.transcribe(
                audio_data, no_speech_threshold=0.5, language="english"
            )
        else:
            result = audio_model.transcribe(audio_data, no_speech_threshold=0.5)

        predicted_text = result["text"]
        result_queue.put_nowait(predicted_text)
        if verbose:
            print(result)
        if save_file:
            os.remove(audio_data)


@click.command()
@click.option(
    "--model",
    default="base",
    help="Model to use",
    type=click.Choice(["tiny", "base", "small", "medium", "large"]),
)
@click.option(
    "--is_english",
    default=False,
    help="Whether to use English model",
    is_flag=True,
    type=bool,
)
@click.option(
    "--verbose",
    default=False,
    help="Whether to print verbose output",
    is_flag=True,
    type=bool,
)
@click.option("--energy", default=1000, help="Energy level for mic to detect", type=int)
@click.option(
    "--dynamic_energy",
    default=False,
    is_flag=True,
    help="Flag to enable dynamic engergy",
    type=bool,
)
@click.option(
    "--record_timeout",
    default=3,
    help="The timeout for new translation",
    type=int,
)
@click.option("--pause", default=0.6, help="Pause time before entry ends", type=float)
@click.option(
    "--dest",
    default="en",
    help="Translation target language",
    type=click.Choice(["en", "vi", "ja", "ko"]),
)
@click.option(
    "--save_file", default=False, help="Flag to save file", is_flag=True, type=bool
)
def main(
    model,
    is_english,
    verbose,
    energy,
    pause,
    dynamic_energy,
    record_timeout,
    dest,
    save_file,
):
    # temp_dir = tempfile.mkdtemp() if save_file else None
    temp_dir = "./temp" if save_file else None
    # there are no english models for large
    if model != "large" and is_english:
        model = model + ".en"
    print("Load model...")
    print("Has CUDA:" + torch.cuda.is_available())
    # devices = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    audio_model = whisper.load_model(model)
    audio_queue = queue.Queue()
    result_queue = queue.Queue()
    translation_queue = queue.Queue()
    output_queue = queue.Queue()
    dest = dest
    print("Start recording thread...")
    threading.Thread(
        target=record_audio,
        args=(
            audio_queue,
            energy,
            pause,
            dynamic_energy,
            save_file,
            temp_dir,
            record_timeout,
        ),
    ).start()
    print("Start transcribing thread...")
    threading.Thread(
        target=transcribe_forever,
        args=(audio_queue, result_queue, audio_model, is_english, verbose, save_file),
    ).start()
    print("Start translating thread...")
    threading.Thread(
        target=translate,
        args=(result_queue, translation_queue, dest),
    ).start()
    start_app(translation_queue)


if __name__ == "__main__":
    main()
