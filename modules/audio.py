import soundcard as sc
import soundfile as sf  # To save the file

output_file = "output.wav"
samplerate = 48000
record_sec = 5

# Get the default speaker and its loopback interface
with sc.get_microphone(id=sc.default_speaker().name, include_loopback=True).recorder(
    samplerate=samplerate
) as mic:
    data = mic.record(
        numframes=samplerate * record_sec,
    )
    sf.write(output_file, data, samplerate)
