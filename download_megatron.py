"""
Download Megatron liveness detection model from InsightFace
"""
import os
from pathlib import Path
import requests
from tqdm import tqdm

def download_file(url, dest_path):
    """Download file with progress bar"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(dest_path, 'wb') as f, tqdm(
        desc=dest_path.name,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            pbar.update(size)

# Create models directory
models_dir = Path.home() / '.insightface' / 'models' / 'liveness'
models_dir.mkdir(parents=True, exist_ok=True)

print("Downloading Megatron liveness model...")
print(f"Destination: {models_dir}")

# Megatron model URLs (these are example URLs - need to find actual model)
# InsightFace Megatron models are typically hosted on their GitHub releases
model_urls = {
    'megatron_liveness.onnx': 'https://github.com/deepinsight/insightface/releases/download/v0.7/megatron_liveness.onnx',
}

for filename, url in model_urls.items():
    dest_path = models_dir / filename
    if dest_path.exists():
        print(f"✅ {filename} already exists")
        continue
    
    try:
        print(f"\nDownloading {filename}...")
        download_file(url, dest_path)
        print(f"✅ Downloaded {filename}")
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")
        print(f"   URL: {url}")

print("\n" + "="*80)
print("Note: If download failed, the Megatron model may not be publicly available.")
print("Alternative: Use InsightFace's FaceAnalysis with proper liveness configuration")
print("="*80)
