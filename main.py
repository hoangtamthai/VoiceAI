import io
import os
import tempfile
import time
from queue import Queue
from threading import Thread

import click
import numpy as np
import soundcard as sc
import sounddevice
import soundfile as sf  # To save the file
import speech_recognition as sr
import torch
from pydub import AudioSegment
from whisper import Whisper, load_model

from modules.coqui_tts import get_tts
from modules.sound import play_to_output
from modules.tkinter_text import start_app
from modules.translate import translate


@click.command()
@click.option(
    "--model",
    default="base",
    help="Model to use",
    type=click.Choice(["tiny", "base", "small", "turbo", "medium", "large"]),
)
@click.option(
    "--english",
    default=False,
    help="Whether to use English model",
    is_flag=True,
    type=bool,
)
@click.option(
    "--subtitles/--no-subtitles",
    default=True,
    help="Whether to show translated subtitles",
    type=bool,
)
@click.option(
    "--dubbing/--no-dubbing",
    default=False,
    help="Whether to play dubbing sound",
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
@click.option("--pause", default=0.8, help="Pause time before entry ends", type=float)
@click.option(
    "--dest",
    default="en",
    help="Translation target language",
    type=click.Choice(["en", "vi", "ja", "ko", "de"]),
)
@click.option(
    "--save_file", default=False, help="Flag to save file", is_flag=True, type=bool
)
def main(
    model,
    english,
    subtitles,
    dubbing,
    verbose,
    energy,
    pause,
    dynamic_energy,
    record_timeout,
    dest,
    save_file,
):
    temp_dir = tempfile.mkdtemp() if save_file else None
    # there are no english models for large
    if model != "large" and english:
        model = model + ".en"
    print("Loading model...")
    print("Has CUDA:", torch.cuda.is_available())
    # devices = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    audio_model = load_model(model)
    audio_queue = Queue()
    result_queue = Queue()
    translation_queue = Queue()
    threads = []
    result = sr.Microphone.list_working_microphones()
    if result == {}:
        print(sounddevice.query_devices())
    for i in result:
        print(i, result[i])
    # device_index = int(input("Please choose an input source for audio: "))
    device_index = 1
    record_process = Thread(
        target=record_audio,
        args=(
            audio_queue,
            device_index,
            energy,
            pause,
            dynamic_energy,
            save_file,
            temp_dir,
            record_timeout,
            verbose,
        ),
    )
    threads.append(record_process)
    transcribing_process = Thread(
        target=transcribe_forever,
        args=(
            audio_queue,
            result_queue,
            audio_model,
            english,
            verbose,
            save_file,
        ),
    )
    threads.append(transcribing_process)
    translating_process = Thread(
        target=translate,
        args=(result_queue, translation_queue, dest),
    )
    threads.append(translating_process)
    if dubbing:
        output_audio_process = Thread(
            target=play_translated_audio, args=([translation_queue], verbose)
        )
        threads.append(output_audio_process)
    for t in threads:
        t.start()
    if subtitles:
        start_app(translation_queue)


def record_audio(
    audio_queue,
    device,
    energy,
    pause,
    dynamic_energy,
    save_file,
    temp_dir,
    record_timeout,
    verbose,
):
    print("Start recording thread...")
    # load the speech recognizer and set the initial energy threshold and pause threshold
    r = sr.Recognizer()
    r.energy_threshold = energy
    r.pause_threshold = pause
    r.dynamic_energy_threshold = dynamic_energy
    r.operation_timeout = record_timeout
    # r.non_speaking_duration = 0.05
    samplerate = 48000
    record_sec = 5

    # Get the default speaker and its loopback interface
    with sc.get_microphone(
        id=sc.default_speaker().name, include_loopback=True
    ).recorder(samplerate=samplerate) as source:
        # with sr.Microphone(device_index=device) as source:
        # print("Adjusting for ambient noise...")
        # r.adjust_for_ambient_noise(source, duration=5)
        # print("Finish adjusting")
        i = 0
        while True:
            # get and save audio to wav file
            if verbose:
                print("Listening...")
            # audio = r.listen(source, phrase_time_limit=record_timeout)
            if save_file:
                data = source.record(
                    numframes=samplerate * record_sec,
                )
                # data = io.BytesIO(audio.get_wav_data())
                # audio_clip = AudioSegment.from_file(data)
                filename = os.path.join(temp_dir, f"temp{i}.wav")
                sf.write(filename, data, samplerate)
                if verbose:
                    print(filename)
                # audio_clip.export(filename, format="wav")
                audio_data = filename
            else:
                torch_audio = torch.from_numpy(
                    np.frombuffer(audio.get_raw_data(), np.int16)
                    .flatten()
                    .astype(np.float32)
                    / 32768.0
                )
                audio_data = torch_audio
            if verbose:
                print("Audio recored")
            audio_queue.put_nowait(audio_data)
            i += 1


def transcribe_forever(
    audio_queue, result_queue, audio_model: Whisper, english, verbose, save_file
):
    print("Start transcribing thread...")
    while True:
        audio_data = audio_queue.get()
        if verbose:
            print("Transcribing...")
        start = time.time()
        if english:
            result = audio_model.transcribe(
                audio_data, no_speech_threshold=0.5, language="english"
            )
        else:
            result = audio_model.transcribe(audio_data, no_speech_threshold=0.5)
        predicted_text = result["text"].strip()
        result_queue.put_nowait(predicted_text)
        if verbose:
            print(result)
            print("Took", time.time() - start)
        # if save_file:
        # os.remove(audio_data)


def play_translated_audio(translation_queue, verbose):
    print("Start audio thread...")
    while True:
        output = translation_queue.get()
        translation_queue.put(output)
        output_sentence = output["text"]
        if verbose:
            print("You say:", output_sentence)
        if output_sentence != "":
            audio, frame_rate = get_tts(output_sentence)
            play_to_output(audio, frame_rate)


if __name__ == "__main__":
    main()
