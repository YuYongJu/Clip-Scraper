#!/usr/bin/env python3
import os
import sys
import cv2
import torch
import numpy as np
from pathlib import Path
import argparse
import time
from tqdm import tqdm
import subprocess
import tempfile
import shutil

# Check if RealESRGAN is available
try:
    from realesrgan import RealESRGANer
    from realesrgan.archs.srvgg_arch import SRVGGNetCompact
    HAS_REALESRGAN = True
except ImportError:
    HAS_REALESRGAN = False
    print("Warning: RealESRGAN not found. Super resolution features will be disabled.")
    print("Install with: pip install realesrgan")

class SuperResolution:
    def __init__(self, model_name='realesr-animevideov3', device='auto', scale=2, denoise_strength=0.5):
        """Initialize the super resolution enhancer
        
        Args:
            model_name (str): Model name. Options: 'realesr-animevideov3' (for anime), 
                              'realesrgan-x4plus' (for general content)
            device (str): Device to use. 'auto', 'cuda', or 'cpu'
            scale (int): Upscale factor (2, 3, 4)
            denoise_strength (float): Denoise strength from 0 to 1
        """
        self.model_name = model_name
        
        if not HAS_REALESRGAN:
            raise ImportError("RealESRGAN is required for super resolution. Install with pip install realesrgan")
        
        # Determine device
        if device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        # Ensure scale is valid
        self.scale = max(min(scale, 4), 2)  # Between 2 and 4
        
        # Validate denoise_strength
        self.denoise_strength = max(min(denoise_strength, 1.0), 0.0)  # Between 0 and 1
        
        # Initialize model
        self.initialize_model()
        
        print(f"Super resolution initialized with {self.model_name} on {self.device}")
        print(f"Scale: {self.scale}x, Denoise Strength: {self.denoise_strength}")
    
    def initialize_model(self):
        """Initialize the RealESRGAN model"""
        # Model selection
        if self.model_name == 'realesr-animevideov3':
            model_path = os.path.join(os.path.expanduser('~'), '.cache/realesrgan/realesr-animevideov3.pth')
            if not os.path.exists(model_path):
                # Model will be downloaded if not available
                pass
            
            # Initialize the model architecture
            model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=16, upscale=self.scale, act_type='prelu')
            netscale = self.scale
        elif self.model_name == 'realesrgan-x4plus':
            model_path = os.path.join(os.path.expanduser('~'), '.cache/realesrgan/realesrgan-x4plus.pth')
            if not os.path.exists(model_path):
                # Model will be downloaded if not available
                pass
            
            # Initialize the model architecture
            model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4, act_type='leakyrelu')
            netscale = 4
        else:
            raise ValueError(f"Unknown model: {self.model_name}")
        
        # Initialize the RealESRGANer
        self.upsampler = RealESRGANer(
            scale=netscale,
            model_path=model_path,
            model=model,
            dni_weight=self.denoise_strength,
            half=self.device == 'cuda',  # Use half precision on CUDA for memory efficiency
            device=self.device
        )
    
    def process_image(self, input_img):
        """Process a single image with super resolution
        
        Args:
            input_img: Input image as a numpy array (BGR)
            
        Returns:
            Super-resolved image as a numpy array (BGR)
        """
        # Process the image with the model
        try:
            output, _ = self.upsampler.enhance(input_img, outscale=self.scale)
            return output
        except Exception as e:
            print(f"Error during super resolution: {str(e)}")
            # Return original image if enhancement fails
            return input_img
    
    def process_video(self, input_path, output_path=None, fps=None, chunk_size=30, progress=True):
        """Process a video with super resolution
        
        Args:
            input_path (str): Path to input video
            output_path (str, optional): Path to output video. If None, will be inferred
            fps (int, optional): Output FPS. If None, use original FPS
            chunk_size (int): Number of frames to process at once
            progress (bool): Whether to show progress bar
            
        Returns:
            Path to processed video
        """
        input_path = Path(input_path)
        
        # Determine output path if not provided
        if output_path is None:
            filename = input_path.stem + f"_upscaled{input_path.suffix}"
            output_path = input_path.parent / filename
        else:
            output_path = Path(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Open the video
        cap = cv2.VideoCapture(str(input_path))
        
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Use original FPS if not specified
        if fps is None:
            fps = original_fps
        
        # Calculate new dimensions
        new_width = width * self.scale
        new_height = height * self.scale
        
        print(f"Processing video: {input_path}")
        print(f"Original size: {width}x{height}, New size: {new_width}x{new_height}")
        print(f"Total frames: {total_frames}, FPS: {fps}")
        
        # Use temporary directory for frames
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            
            # Setup progress bar
            if progress:
                pbar = tqdm(total=total_frames, desc="Processing frames")
            
            frame_count = 0
            frames_processed = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process the frame
                upscaled_frame = self.process_image(frame)
                
                # Save the frame to temp directory
                cv2.imwrite(str(temp_dir / f"frame_{frame_count:08d}.png"), upscaled_frame)
                
                frame_count += 1
                frames_processed += 1
                
                if progress:
                    pbar.update(1)
                
                # Process in chunks to avoid memory issues and provide better progress feedback
                if frames_processed >= chunk_size or frame_count >= total_frames:
                    if frame_count >= total_frames:
                        break
            
            if progress:
                pbar.close()
            
            # Use FFmpeg to combine frames into video
            print("Combining frames into video...")
            
            # Determine video codec based on output file extension
            if output_path.suffix.lower() in ['.mp4', '.m4v']:
                codec = 'libx264'
                pix_fmt = 'yuv420p'
            elif output_path.suffix.lower() in ['.webm']:
                codec = 'libvpx-vp9'
                pix_fmt = 'yuv420p'
            else:
                # Default to mp4
                codec = 'libx264'
                pix_fmt = 'yuv420p'
            
            # FFmpeg command to combine frames
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file if it exists
                '-framerate', str(fps),
                '-i', str(temp_dir / 'frame_%08d.png'),
                '-c:v', codec,
                '-pix_fmt', pix_fmt,
                '-preset', 'slow',  # Slower preset for better compression
                '-crf', '23',  # Constant Rate Factor (lower is better quality, 18-28 is good range)
                '-r', str(fps),
                str(output_path)
            ]
            
            # Run FFmpeg
            try:
                subprocess.run(ffmpeg_cmd, check=True)
                print(f"Super resolution complete: {output_path}")
                return str(output_path)
            except subprocess.CalledProcessError as e:
                print(f"Error during video encoding: {str(e)}")
                return str(input_path)  # Return original path on error
            finally:
                cap.release()
    
    def batch_process_directory(self, input_dir, output_dir=None, file_types=('.mp4', '.webm', '.mkv'), 
                                recursive=False, skip_existing=True):
        """Process all videos in a directory
        
        Args:
            input_dir (str): Input directory
            output_dir (str, optional): Output directory. If None, will create 'upscaled' subdirectory
            file_types (tuple): File extensions to process
            recursive (bool): Whether to process subdirectories
            skip_existing (bool): Whether to skip existing output files
            
        Returns:
            List of processed video paths
        """
        input_dir = Path(input_dir)
        
        if output_dir is None:
            output_dir = input_dir / 'upscaled'
        else:
            output_dir = Path(output_dir)
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all videos
        if recursive:
            video_files = []
            for ext in file_types:
                video_files.extend(list(input_dir.glob(f'**/*{ext}')))
        else:
            video_files = []
            for ext in file_types:
                video_files.extend(list(input_dir.glob(f'*{ext}')))
        
        processed_videos = []
        
        print(f"Found {len(video_files)} video files to process")
        
        for i, video_file in enumerate(video_files):
            # Determine output path
            rel_path = video_file.relative_to(input_dir)
            output_path = output_dir / rel_path
            
            # Create parent directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Skip if output file exists
            if skip_existing and output_path.exists():
                print(f"Skipping existing file: {output_path}")
                processed_videos.append(str(output_path))
                continue
            
            print(f"Processing video {i+1}/{len(video_files)}: {video_file}")
            
            try:
                # Process the video
                processed_path = self.process_video(video_file, output_path)
                processed_videos.append(processed_path)
            except Exception as e:
                print(f"Error processing {video_file}: {str(e)}")
        
        return processed_videos

def main():
    parser = argparse.ArgumentParser(description="Super Resolution for Anime Videos")
    parser.add_argument("input", help="Input video file or directory")
    parser.add_argument("--output", "-o", help="Output video file or directory")
    parser.add_argument("--model", "-m", choices=["anime", "general"], default="anime",
                        help="Model to use (anime or general)")
    parser.add_argument("--scale", "-s", type=int, choices=[2, 3, 4], default=2,
                        help="Scale factor (2, 3, or 4)")
    parser.add_argument("--denoise", "-d", type=float, default=0.5,
                        help="Denoise strength (0.0 to 1.0)")
    parser.add_argument("--fps", type=int, help="Output FPS (default: same as input)")
    parser.add_argument("--batch", "-b", action="store_true", 
                        help="Process all videos in input directory")
    parser.add_argument("--recursive", "-r", action="store_true", 
                        help="Process subdirectories when using batch mode")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto",
                        help="Device to use for processing")
    
    args = parser.parse_args()
    
    # Select model based on argument
    model_name = "realesr-animevideov3" if args.model == "anime" else "realesrgan-x4plus"
    
    # Initialize super resolution
    try:
        sr = SuperResolution(model_name=model_name, device=args.device, 
                             scale=args.scale, denoise_strength=args.denoise)
        
        input_path = Path(args.input)
        
        if args.batch or input_path.is_dir():
            # Process directory
            if args.output:
                output_dir = args.output
            else:
                output_dir = input_path / f"upscaled_{args.scale}x"
            
            sr.batch_process_directory(input_path, output_dir, recursive=args.recursive)
        else:
            # Process single file
            if args.output:
                output_path = args.output
            else:
                # Default output path
                filename = input_path.stem + f"_upscaled_{args.scale}x{input_path.suffix}"
                output_path = input_path.parent / filename
            
            sr.process_video(input_path, output_path, fps=args.fps)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 