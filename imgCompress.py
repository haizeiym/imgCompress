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

def validate_png(input_path):
    """验证PNG文件格式是否正确"""
    try:
        # 使用magick命令验证PNG文件
        cmd = ['magick', 'identify', '-verbose', input_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"PNG文件格式验证失败: {input_path}")
            logger.error(f"错误输出: {result.stderr}")
            return False
        return True
    except Exception as e:
        logger.error(f"验证PNG文件时发生错误: {str(e)}")
        return False

def compress_png(input_path, output_path, quality_ranges=None):
    """
    Compress PNG image using pngquant.
    :param input_path: 输入文件路径
    :param output_path: 输出文件路径
    :param quality_ranges: 质量范围列表，按优先级尝试，格式如 [('50-70', '40-60', '30-50')]
    :return: 是否成功
    """
    if quality_ranges is None:
        quality_ranges = ['50-70', '40-60', '30-50']  # 默认质量范围，从高到低尝试
        
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"输入文件不存在: {input_path}")
            return False
            
        # 检查输入文件是否为PNG
        if not input_path.lower().endswith('.png'):
            logger.error(f"输入文件不是PNG格式: {input_path}")
            return False
            
        # 检查输入文件是否可读
        if not os.access(input_path, os.R_OK):
            logger.error(f"无法读取输入文件: {input_path}")
            return False
            
        # 创建临时目录用于处理
        temp_dir = tempfile.mkdtemp(prefix='png_compress_')
        try:
            # 在临时目录中创建输出文件
            temp_output = os.path.join(temp_dir, os.path.basename(output_path))
            
            # 尝试不同的质量范围
            last_error = None
            successful_quality = None
            
            for quality in quality_ranges:
                try:
                    # Run pngquant with quality settings
                    cmd = [
                        'pngquant',
                        '--force',
                        f'--quality={quality}',
                        '--output', temp_output,
                        input_path
                    ]
                    
                    # 执行命令并捕获详细输出
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    
                    # 记录成功使用的质量范围
                    successful_quality = quality
                    
                    # 记录压缩信息
                    if result.stdout:
                        logger.info(f"压缩信息: {result.stdout.strip()}")
                    
                    # 如果成功执行到这里，说明压缩成功
                    break
                except subprocess.CalledProcessError as e:
                    last_error = e
                    if e.returncode == 99:
                        logger.warning(f"使用质量范围 {quality} 压缩失败，尝试下一个质量范围")
                        if e.stdout:
                            logger.info(f"压缩信息: {e.stdout.strip()}")
                        continue
                    else:
                        raise  # 如果是其他错误，直接抛出
            else:
                # 如果所有质量范围都失败了
                if last_error and last_error.returncode == 99:
                    logger.error(f"所有质量范围都无法达到要求，使用原始文件")
                    # 复制原始文件作为输出
                    shutil.copy2(input_path, temp_output)
                else:
                    raise last_error
            
            # 检查临时输出文件是否成功创建
            if not os.path.exists(temp_output):
                logger.error(f"压缩后的文件未创建: {temp_output}")
                return False
                
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
            # 移动临时文件到最终位置
            shutil.move(temp_output, output_path)
            
            # 检查输出文件大小
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            compression_ratio = (1 - output_size / input_size) * 100
            
            logger.info(f"成功压缩PNG: {input_path}")
            if successful_quality:
                logger.info(f"使用的质量范围: {successful_quality}")
            logger.info(f"压缩率: {compression_ratio:.2f}%")
            logger.info(f"原始大小: {input_size/1024:.2f}KB")
            logger.info(f"压缩后大小: {output_size/1024:.2f}KB")
            
            return True
            
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"清理临时目录失败: {temp_dir}, 错误: {str(e)}")
                
    except subprocess.CalledProcessError as e:
        error_msg = ""
        if e.returncode == 99:
            error_msg = "无法达到指定的质量要求"
        elif e.returncode == 98:
            error_msg = "无法创建输出文件"
        elif e.returncode == 97:
            error_msg = "无法读取输入文件"
        elif e.returncode == 2:
            error_msg = "参数错误"
        else:
            error_msg = f"未知错误 (代码: {e.returncode})"
            
        logger.error(f"PNG压缩失败 {input_path}: {error_msg}")
        if e.stderr:
            logger.error(f"错误输出: {e.stderr}")
        if e.stdout:
            logger.error(f"标准输出: {e.stdout}")
        return False
    except Exception as e:
        logger.error(f"处理PNG时发生未知错误 {input_path}: {str(e)}")
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
