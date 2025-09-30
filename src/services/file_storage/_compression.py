import logging
import zstandard as zstd

from .service import Compressor, CompressionService, CompressionStandard

logger = logging.getLogger(__name__)


ZSTD_MAGIC = b'\x28\xb5\x2f\xfd'  # zstd magic number for file header detection
ZSTD_LEVEL = 1  # low CPU, reasonable compression


class ZstdCompressor(Compressor):
    """
    Compressor implementation using Zstandard (zstd) algorithm.
    """

    def __init__(self, level: int = ZSTD_LEVEL):
        self.level = level
        self.compressor = zstd.ZstdCompressor(level=level)
        self.decompressor = zstd.ZstdDecompressor()
        self.compress_obj = self.compressor.compressobj()
        self.decompress_obj = self.decompressor.decompressobj()

    def compress(self, data: bytes) -> bytes:
        return self.compress_obj.compress(data)

    def decompress(self, data: bytes) -> bytes:
        return self.decompress_obj.decompress(data)

    def flush_compression(self) -> bytes:
        return self.compress_obj.flush()

    def flush_decompression(self) -> bytes:
        return self.decompress_obj.flush()


class CompressionServiceImpl(CompressionService):
    """
    Compression service that provides ZstdCompressor instances.
    """

    def get_compressor(self, compression_standard: CompressionStandard) -> Compressor:
        if compression_standard == CompressionStandard.ZSTD:
            return ZstdCompressor(level=ZSTD_LEVEL)
        else:
            raise ValueError(f"Unsupported compression standard: {compression_standard}")
        
    def get_decompressor(self, compression_standard: CompressionStandard) -> Compressor:
        if compression_standard == CompressionStandard.ZSTD:
            return ZstdCompressor(level=ZSTD_LEVEL)
        else:
            raise ValueError(f"Unsupported compression standard: {compression_standard}")
        
    def detect_compression(self, compression_meta: dict | None = None, data_chunk: bytes | None = None) -> CompressionStandard | None:
        if compression_meta and "compression" in compression_meta:
            comp = compression_meta["compression"].lower()
            if comp == "zstd":
                return CompressionStandard.ZSTD
            else:
                logger.warning(f"Unknown compression defined in metadata: {comp}")
                return None
        
        if data_chunk and len(data_chunk) >= 4:
            # Check for zstd magic number
            if data_chunk.startswith(ZSTD_MAGIC):
                return CompressionStandard.ZSTD

        return None
