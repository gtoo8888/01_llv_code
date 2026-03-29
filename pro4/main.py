#!/usr/bin/env python3
"""语音转文字 CLI 工具"""
import sys
from pathlib import Path
from transcribe import transcribe_with_timestamps

# 支持的音频格式
AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.wav', '.flac', '.ogg', '.webm'}


def scan_audio_files(folder_path: str):
    """扫描目录下所有音频文件"""
    folder = Path(folder_path)
    audio_files = []
    for ext in AUDIO_EXTENSIONS:
        audio_files.extend(folder.glob(f'*{ext}'))
        audio_files.extend(folder.glob(f'*{ext.upper()}'))
    return sorted(audio_files)


def process_folder(folder_path: str):
    """扫描并处理文件夹中的所有音频文件"""
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"Error: Path does not exist or is not a directory: {folder_path}")
        return

    audio_files = scan_audio_files(folder_path)
    if not audio_files:
        print(f"No audio files found. Supported formats: {', '.join(sorted(AUDIO_EXTENSIONS))}")
        return

    output_folder = folder.parent / f"{folder.name}_output"
    output_folder.mkdir(exist_ok=True)

    print(f"Scanning folder: {folder_path}")
    print(f"Found {len(audio_files)} audio file(s)")
    print(f"Output folder: {output_folder}\n")

    success_count = 0
    for i, audio_file in enumerate(audio_files, 1):
        print(f"[{i}/{len(audio_files)}] Processing: {audio_file.name}")
        try:
            txt_path = output_folder / audio_file.with_suffix('.txt').name
            with open(txt_path, 'w', encoding='utf-8') as f:
                transcribe_with_timestamps(str(audio_file), output_file=f)
            print(f"  -> {txt_path} OK")
            success_count += 1
        except Exception as e:
            print(f"  FAILED: {e}")

    print(f"\nDone. {success_count}/{len(audio_files)} file(s) succeeded | output: {output_folder}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <audio_folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    process_folder(folder_path)


if __name__ == '__main__':
    main()
