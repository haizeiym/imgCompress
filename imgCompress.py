#!/usr/bin/env python3
import os
import subprocess
import logging
from pathlib import Path
import shutil
import argparse
import tempfile
import sys
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_installation_instructions():
    """Get installation instructions based on the operating system."""
    system = platform.system().lower()
    if system == 'darwin':  # macOS
        return """
请使用 Homebrew 安装所需工具：
1. 安装 Homebrew（如果尚未安装）:
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
2. 安装 pngquant:
   brew install pngquant
3. 安装 mozjpeg:
   brew install mozjpeg
"""
    elif system == 'linux':
        return """
请使用包管理器安装所需工具：

Ubuntu/Debian:
sudo apt-get update
sudo apt-get install pngquant
sudo apt-get install mozjpeg

CentOS/RHEL:
sudo yum install pngquant
sudo yum install mozjpeg

Arch Linux:
sudo pacman -S pngquant
sudo pacman -S mozjpeg
"""
    elif system == 'windows':
        return """
请使用以下方法安装所需工具：

1. 安装 pngquant:
   - 访问 https://pngquant.org/
   - 下载 Windows 版本
   - 将可执行文件添加到系统 PATH

2. 安装 mozjpeg:
   - 访问 https://github.com/mozilla/mozjpeg/releases
   - 下载最新版本
   - 将可执行文件添加到系统 PATH
"""
    else:
        return "请访问 https://pngquant.org/ 和 https://github.com/mozilla/mozjpeg 获取安装说明"

def check_dependencies():
    """Check if required tools are installed."""
    missing_tools = []
    
    # Check pngquant
    try:
        subprocess.run(['pngquant', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing_tools.append('pngquant')
    
    # Check cjpeg (mozjpeg)
    try:
        subprocess.run(['cjpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing_tools.append('cjpeg (mozjpeg)')
    
    if missing_tools:
        logger.error("缺少必要的工具: " + ", ".join(missing_tools))
        logger.error("请安装以下工具后再运行脚本：")
        logger.error(get_installation_instructions())
        return False
    
    return True

def compress_png(input_path, output_path):
    """Compress PNG image using pngquant."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Run pngquant with quality settings
        cmd = [
            'pngquant',
            '--force',
            '--quality=65-80',  # Adjust quality range as needed
            '--output', output_path,
            input_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Successfully compressed PNG: {input_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error compressing PNG {input_path}: {e.stderr.decode()}")
        return False

def compress_jpeg(input_path, output_path):
    """Compress JPEG image using cjpeg (mozjpeg)."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Run cjpeg with quality settings
        cmd = [
            'cjpeg',
            '-quality', '70',  # Adjust quality as needed
            '-optimize',
            '-outfile', output_path,
            input_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Successfully compressed JPEG: {input_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error compressing JPEG {input_path}: {e.stderr.decode()}")
        return False

def process_directory(input_dir, output_dir, replace_original=False):
    """Process all PNG and JPEG images in the directory and its subdirectories."""
    input_path = Path(input_dir)
    
    if replace_original:
        # Create a temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Walk through all files in the input directory
            for root, _, files in os.walk(input_path):
                for file in files:
                    input_file = Path(root) / file
                    # Calculate relative path for temp file
                    rel_path = input_file.relative_to(input_path)
                    temp_file = temp_path / rel_path
                    
                    # Process PNG files
                    if file.lower().endswith('.png'):
                        if compress_png(str(input_file), str(temp_file)):
                            # Replace original with compressed version
                            shutil.move(str(temp_file), str(input_file))
                    # Process JPEG files
                    elif file.lower().endswith(('.jpg', '.jpeg')):
                        if compress_jpeg(str(input_file), str(temp_file)):
                            # Replace original with compressed version
                            shutil.move(str(temp_file), str(input_file))
    else:
        output_path = Path(output_dir)
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Walk through all files in the input directory
        for root, _, files in os.walk(input_path):
            for file in files:
                input_file = Path(root) / file
                # Calculate relative path for output
                rel_path = input_file.relative_to(input_path)
                output_file = output_path / rel_path
                
                # Process PNG files
                if file.lower().endswith('.png'):
                    compress_png(str(input_file), str(output_file))
                # Process JPEG files
                elif file.lower().endswith(('.jpg', '.jpeg')):
                    compress_jpeg(str(input_file), str(output_file))

def main():
    """Main function to handle the compression process."""
    parser = argparse.ArgumentParser(description='Compress PNG and JPEG images using pngquant and mozjpeg')
    parser.add_argument('-i', '--input', 
                      help='Input directory containing images to compress (default: current directory)',
                      default=os.getcwd())
    parser.add_argument('-o', '--output',
                      help='Output directory for compressed images (default: input_directory/compressed)',
                      default=None)
    parser.add_argument('-r', '--replace',
                      help='Replace original files with compressed versions',
                      action='store_true')
    
    args = parser.parse_args()
    
    if not check_dependencies():
        sys.exit(1)
    
    # Get input directory
    input_dir = os.path.abspath(args.input)
    
    # Set output directory
    if args.output:
        output_dir = os.path.abspath(args.output)
    else:
        output_dir = os.path.join(input_dir, 'compressed')
    
    logger.info(f"Starting compression process...")
    logger.info(f"Input directory: {input_dir}")
    if not args.replace:
        logger.info(f"Output directory: {output_dir}")
    else:
        logger.info("Mode: Replace original files")
    
    process_directory(input_dir, output_dir, args.replace)
    logger.info("Compression process completed!")

if __name__ == "__main__":
    main()
