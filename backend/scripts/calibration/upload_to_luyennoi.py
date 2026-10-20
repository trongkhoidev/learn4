import os
import json

def upload_and_get_ground_truth(audio_path):
    """
    Mock logic to upload to luyennoi.com and parse the ground truth band score.
    """
    print(f"Uploading {audio_path} to luyennoi.com...")
    # Simulated API call
    return {
        "overall": 6.5,
        "pronunciation": 6.5,
        "fluency": 7.0,
        "grammar": 6.0,
        "vocabulary": 6.5
    }

def main():
    samples_dir = 'data/samples'
    if not os.path.exists(samples_dir):
        print("No samples found. Run collect_samples.py first.")
        return
        
    results = {}
    for filename in os.listdir(samples_dir):
        if filename.endswith(".wav"):
            path = os.path.join(samples_dir, filename)
            truth = upload_and_get_ground_truth(path)
            results[filename] = truth
            
    with open('ground_truth.json', 'w') as f:
        json.dump(results, f, indent=4)
    print("Ground truth data saved to ground_truth.json")

if __name__ == "__main__":
    main()
