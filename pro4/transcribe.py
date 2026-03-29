import time
from faster_whisper import WhisperModel
from pathlib import Path
from converter import convert_to_simplified


MODEL_PATH = "model/small"
MODEL = None


def get_model():
    """Load model globally, only once."""
    global MODEL
    if MODEL is None:
        MODEL = WhisperModel(MODEL_PATH, device="cuda", compute_type="int8", local_files_only=True)
    return MODEL


def transcribe_with_timestamps(audio_path: str, output_file=None) -> list[tuple[float, float, str]]:
    file_size = Path(audio_path).stat().st_size
    model = get_model()
    segments, info = model.transcribe(audio_path, beam_size=5)

    total_duration = info.duration
    print(f"  Duration: {total_duration:.2f}s | Language: {info.language} ({info.language_probability:.2f})")

    result = []
    seg_count = 0
    processed_duration = 0.0
    seg_start_time = time.perf_counter()
    prev_total = 0.0

    for segment in segments:
        seg_seg_start = time.perf_counter()
        simplified_text = convert_to_simplified(segment.text)
        seg_count += 1
        processed_duration = segment.end

        total_elapsed = seg_seg_start - seg_start_time
        speed = seg_count / total_elapsed if total_elapsed > 0 else 0
        audio_progress = (processed_duration / total_duration * 100) if total_duration > 0 else 0

        if seg_count > 1:
            delta = total_elapsed - prev_total
            if delta > 0.1:
                print(f"  --- +{delta:.1f}s batch wait ---")
        prev_total = total_elapsed

        print(f"  [{segment.start:08.2f}s - {segment.end:08.2f}s] {simplified_text} | {total_elapsed:.1f}s total | {speed:.1f} seg/s | audio: {processed_duration:.1f}s/{total_duration:.1f}s ({audio_progress:.0f}%)")
        result.append((segment.start, segment.end, simplified_text))
        if output_file:
            output_file.write(f"[{segment.start:08.2f}s - {segment.end:08.2f}s] {simplified_text}\n")
            output_file.flush()

    total_time = time.perf_counter() - seg_start_time
    file_size_mb = file_size / 1024 / 1024
    print(f"  Done. {seg_count} segments | {total_time:.1f}s transcribe time | audio: {total_duration:.1f}s ({file_size_mb:.1f}MB) | {seg_count/total_time:.1f} seg/s")

    return result
