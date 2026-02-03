#!/usr/bin/env python3
"""
VoxDocs Test Script
Tests the complete Whisper transcription pipeline with dental vocabulary.

Usage:
    python scripts/test_whisper.py [audio_file.wav]

If no audio file is provided, creates a test audio file.
"""

import sys
import os
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

def check_dependencies():
    """Check if all required dependencies are installed."""
    missing = []

    try:
        import whisper
    except ImportError:
        missing.append("openai-whisper")

    try:
        import torch
    except ImportError:
        missing.append("torch")

    try:
        import numpy
    except ImportError:
        missing.append("numpy")

    if missing:
        print("Missing dependencies:")
        print(f"  pip install {' '.join(missing)}")
        return False
    return True


def check_ffmpeg():
    """Check if ffmpeg is available."""
    import shutil
    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg is not installed!")
        print("Install with:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Windows: choco install ffmpeg")
        return False
    return True


def create_test_audio():
    """Create a simple test audio file with a dental phrase."""
    try:
        import numpy as np
        import wave

        # Create a simple beep sound (placeholder for real audio)
        sample_rate = 16000
        duration = 3  # seconds
        frequency = 440  # Hz

        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)

        test_file = Path("test_audio.wav")
        with wave.open(str(test_file), 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio.tobytes())

        print(f"Created test audio: {test_file}")
        return test_file
    except Exception as e:
        print(f"Could not create test audio: {e}")
        return None


def test_whisper_transcription(audio_path: Path):
    """Test Whisper transcription with dental vocabulary boost."""
    print("\n" + "="*60)
    print("Testing Whisper Transcription")
    print("="*60)

    try:
        from app.services.whisper_service import whisper_service

        print(f"\nAudio file: {audio_path}")
        print("Loading Whisper model (this may take a moment)...")

        # Get model info
        info = whisper_service.get_model_info()
        print(f"Model: {info['model_name']}")
        print(f"Device: {info['device']}")
        print(f"Multilingual: {info['multilingual']}")

        # Transcribe
        print("\nTranscribing...")
        start_time = time.time()

        result = whisper_service.transcribe_with_dental_boost(audio_path)

        elapsed = time.time() - start_time

        print(f"\n--- Results ---")
        print(f"Text: {result.text}")
        print(f"Language: {result.language}")
        print(f"Confidence: {result.confidence:.2%}")
        print(f"Processing time: {elapsed:.2f}s")
        print(f"Segments: {len(result.segments)}")

        return result

    except Exception as e:
        print(f"Transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_classification(text: str):
    """Test dental terminology classification."""
    print("\n" + "="*60)
    print("Testing Classification")
    print("="*60)

    try:
        from app.services.classification_service import classifier

        print(f"\nInput text: {text}")

        results = classifier.classify(text)

        print(f"\nFound {len(results)} entities:")
        for r in results:
            print(f"  - [{r.category.value}] {r.extracted_text}")
            if r.tooth_number:
                print(f"    Tooth: {r.tooth_number}")
            if r.normalized_value:
                print(f"    Normalized: {r.normalized_value}")

        summary = classifier.get_summary(results)
        print(f"\nSummary:")
        print(f"  Teeth mentioned: {summary['teeth_mentioned']}")
        print(f"  Diagnoses: {len(summary['diagnoses'])}")
        print(f"  Treatments: {len(summary['treatments'])}")
        print(f"  Findings: {len(summary['findings'])}")

        return results

    except Exception as e:
        print(f"Classification failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_encryption():
    """Test file encryption service."""
    print("\n" + "="*60)
    print("Testing Encryption")
    print("="*60)

    try:
        from app.services.encryption_service import encryption_service

        # Test data encryption
        test_data = b"Zahn 16 mesial Karies Grad 2"
        print(f"\nOriginal: {test_data}")

        encrypted, nonce, salt = encryption_service.encrypt_data(test_data)
        print(f"Encrypted length: {len(encrypted)} bytes")

        decrypted = encryption_service.decrypt_data(encrypted, nonce, salt)
        print(f"Decrypted: {decrypted}")

        assert test_data == decrypted, "Decryption failed!"
        print("Encryption test: PASSED")

        return True

    except Exception as e:
        print(f"Encryption test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("="*60)
    print("VoxDocs - Dental Speech-to-Text Test Suite")
    print("="*60)

    # Check dependencies
    print("\nChecking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("Dependencies: OK")

    # Check ffmpeg
    if not check_ffmpeg():
        print("\nWARNING: Whisper transcription will fail without ffmpeg")

    # Determine audio file
    if len(sys.argv) > 1:
        audio_path = Path(sys.argv[1])
        if not audio_path.exists():
            print(f"Audio file not found: {audio_path}")
            sys.exit(1)
    else:
        print("\nNo audio file provided.")
        audio_path = create_test_audio()
        if not audio_path:
            # Use a sample dental text for classification test
            audio_path = None

    # Test encryption
    test_encryption()

    # Test classification with sample dental text
    sample_texts = [
        "Zahn 16 mesial Karies Grad 2",
        "Taschentiefe 5 Millimeter distal an Zahn 27",
        "Wurzelkanalbehandlung an Zahn 46 durchgeführt",
        "Lockerungsgrad 2, Blutung auf Sondierung positiv",
        "Composite-Füllung bukkal, Artikain zur Anästhesie",
    ]

    print("\n" + "="*60)
    print("Testing Classification with Sample Texts")
    print("="*60)

    for text in sample_texts:
        print(f"\n>>> {text}")
        results = test_classification(text)

    # Test Whisper transcription if audio file available
    if audio_path and audio_path.exists():
        result = test_whisper_transcription(audio_path)

        # Classify transcription result
        if result and result.text:
            test_classification(result.text)

    print("\n" + "="*60)
    print("Test Suite Complete")
    print("="*60)


if __name__ == "__main__":
    main()
