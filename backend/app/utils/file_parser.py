"""
文件解析工具
支持PDF、Markdown、TXT文件的文本提取，以及包装图片素材的元信息提取
"""

import os
from pathlib import Path
from typing import List, Optional


def _read_text_with_fallback(file_path: str) -> str:
    """
    读取文本文件，UTF-8失败时自动探测编码。
    
    采用多级回退策略：
    1. 首先尝试 UTF-8 解码
    2. 使用 charset_normalizer 检测编码
    3. 回退到 chardet 检测编码
    4. 最终使用 UTF-8 + errors='replace' 兜底
    
    Args:
        file_path: 文件路径
        
    Returns:
        解码后的文本内容
    """
    data = Path(file_path).read_bytes()
    
    # 首先尝试 UTF-8
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        pass
    
    # 尝试使用 charset_normalizer 检测编码
    encoding = None
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data).best()
        if best and best.encoding:
            encoding = best.encoding
    except Exception:
        pass
    
    # 回退到 chardet
    if not encoding:
        try:
            import chardet
            result = chardet.detect(data)
            encoding = result.get('encoding') if result else None
        except Exception:
            pass
    
    # 最终兜底：使用 UTF-8 + replace
    if not encoding:
        encoding = 'utf-8'
    
    return data.decode(encoding, errors='replace')


class FileParser:
    """文件解析器"""
    
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
    SUPPORTED_EXTENSIONS = {'.pdf', '.md', '.markdown', '.txt', *IMAGE_EXTENSIONS}
    
    @classmethod
    def extract_text(cls, file_path: str) -> str:
        """
        从文件中提取文本
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的文本内容
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        suffix = path.suffix.lower()
        
        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {suffix}")
        
        if suffix == '.pdf':
            return cls._extract_from_pdf(file_path)
        elif suffix in {'.md', '.markdown'}:
            return cls._extract_from_md(file_path)
        elif suffix == '.txt':
            return cls._extract_from_txt(file_path)
        elif suffix in cls.IMAGE_EXTENSIONS:
            return cls._extract_from_image(file_path)
        
        raise ValueError(f"无法处理的文件格式: {suffix}")
    
    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """从PDF提取文本"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("需要安装PyMuPDF: pip install PyMuPDF")
        
        text_parts = []
        with fitz.open(file_path) as doc:
            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    @staticmethod
    def _extract_from_md(file_path: str) -> str:
        """从Markdown提取文本，支持自动编码检测"""
        return _read_text_with_fallback(file_path)
    
    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """从TXT提取文本，支持自动编码检测"""
        return _read_text_with_fallback(file_path)

    @staticmethod
    def _extract_from_image(file_path: str) -> str:
        """为包装图片生成可进入研究上下文的素材说明。"""
        path = Path(file_path)
        try:
            from PIL import Image
        except ImportError:
            Image = None

        image_meta = []
        visual_summary = []
        if Image is not None:
            try:
                with Image.open(file_path) as image:
                    width, height = image.size
                    orientation = "方形包装图"
                    if width > height:
                        orientation = "横版包装图"
                    elif height > width:
                        orientation = "竖版包装图"
                    dominant_colors = _dominant_hex_colors(image)
                    if dominant_colors:
                        visual_summary.append(
                            f"视觉摘要：{orientation}，主色 {dominant_colors[0]}，主要配色 {', '.join(dominant_colors)}"
                        )
                    else:
                        visual_summary.append(f"视觉摘要：{orientation}")
                    image_meta = [
                        f"格式：{image.format or path.suffix.lstrip('.').upper()}",
                        f"尺寸：{width}x{height}",
                        f"色彩模式：{image.mode}",
                    ]
            except Exception:
                image_meta = [f"格式：{path.suffix.lstrip('.').upper()}"]
        else:
            image_meta = [f"格式：{path.suffix.lstrip('.').upper()}"]

        size_kb = max(1, round(path.stat().st_size / 1024)) if path.exists() else 0
        return "\n".join([
            "包装/图片素材",
            f"文件名：{path.name}",
            *image_meta,
            *visual_summary,
            f"文件大小：{size_kb} KB",
            "说明：该文件为消费者测试中的包装视觉素材，重点关注版面、颜色、主视觉、声明和信息层级。",
        ])
    
    @classmethod
    def extract_from_multiple(cls, file_paths: List[str]) -> str:
        """
        从多个文件提取文本并合并
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            合并后的文本
        """
        all_texts = []
        
        for i, file_path in enumerate(file_paths, 1):
            try:
                text = cls.extract_text(file_path)
                filename = Path(file_path).name
                all_texts.append(f"=== 文档 {i}: {filename} ===\n{text}")
            except Exception as e:
                all_texts.append(f"=== 文档 {i}: {file_path} (提取失败: {str(e)}) ===")
        
        return "\n\n".join(all_texts)


def split_text_into_chunks(
    text: str, 
    chunk_size: int = 500, 
    overlap: int = 50
) -> List[str]:
    """
    将文本分割成小块
    
    Args:
        text: 原始文本
        chunk_size: 每块的字符数
        overlap: 重叠字符数
        
    Returns:
        文本块列表
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # 尝试在句子边界处分割
        if end < len(text):
            # 查找最近的句子结束符
            for sep in ['。', '！', '？', '.\n', '!\n', '?\n', '\n\n', '. ', '! ', '? ']:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1 and last_sep > chunk_size * 0.3:
                    end = start + last_sep + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # 下一个块从重叠位置开始
        start = end - overlap if end < len(text) else len(text)
    
    return chunks


def _dominant_hex_colors(image, max_colors: int = 3) -> List[str]:
    """Extract a tiny deterministic dominant-color summary for packaging images."""
    rgb_image = image.convert("RGB")
    rgb_image.thumbnail((64, 64))
    colors = rgb_image.getcolors(maxcolors=64 * 64) or []
    colors.sort(reverse=True, key=lambda item: item[0])
    result: List[str] = []
    for _count, (red, green, blue) in colors:
        hex_color = f"#{red:02x}{green:02x}{blue:02x}"
        if hex_color not in result:
            result.append(hex_color)
        if len(result) >= max_colors:
            break
    return result

