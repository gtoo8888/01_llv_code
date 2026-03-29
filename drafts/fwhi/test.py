from faster_whisper import WhisperModel
from opencc import OpenCC

# model_size = "large-v3"
model_size = "small"
# model_size = "medium"


cc = OpenCC('t2s')

# Run on GPU with FP16
model = WhisperModel(model_size, device="cuda", compute_type="int8",local_files_only=True)

# or run on GPU with INT8
# model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
# or run on CPU with INT8
# model = WhisperModel(model_size, device="cpu", compute_type="int8",local_files_only=True)

segments, info = model.transcribe("16.m4a", beam_size=5)

print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

for segment in segments:
    simplified_text = cc.convert(segment.text)
    print(f"[{segment.start:08.2f}-{segment.end:08.2f}] {simplified_text}")