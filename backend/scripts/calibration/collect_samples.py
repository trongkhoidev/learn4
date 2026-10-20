import os
import argparse
import time

def record_audio(filename, duration=15):
    """
    Placeholder for actual recording logic using pyaudio or sounddevice
    """
    print(f"Recording for {duration} seconds to {filename}...")
    time.sleep(1) # mock recording
    print("Recording saved.")

def main():
    parser = argparse.ArgumentParser(description='Collect audio samples for calibration.')
    parser.add_argument('--num', type=int, default=15, help='Number of samples to collect')
    parser.add_argument('--out', type=str, default='data/samples', help='Output directory')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    
    print("=== Audio Sample Collection Pipeline ===")
    for i in range(1, args.num + 1):
        print(f"\n--- Sample {i}/{args.num} ---")
        input("Press Enter to start recording (mock)...")
        record_audio(os.path.join(args.out, f"sample_{i}.wav"))

if __name__ == "__main__":
    main()
