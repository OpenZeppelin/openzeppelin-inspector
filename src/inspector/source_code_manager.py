from pathlib import Path
import bisect


class SourceCodeManager:
    """
    Manages efficient access to source files for offset-based lookups.

    Caches file contents and builds fast lookup tables
    to map character offsets to (line, column) positions.
    """

    def __init__(self):
        self._file_contents: dict[Path, str] = {}
        self._file_line_offsets: dict[Path, list[int]] = {}

    def load_file(self, path: Path) -> None:
        """
        Load a file into cache and precompute line starting offsets.

        Args:
            path: Path to the file to load.
        """
        if path in self._file_contents:
            return  # Already loaded

        text = path.read_text(encoding="utf-8")
        self._file_contents[path] = text

        offsets = [0]
        for line in text.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        self._file_line_offsets[path] = offsets

    def offset_to_line_col(self, path: Path, offset: int) -> tuple[int, int]:
        """
        Convert a file offset to (line, col).

        Args:
            path: Path to the file.
            offset: Character offset from start of file.

        Returns:
            (line_number, column_number), both 1-indexed.
        """
        if path not in self._file_contents:
            self.load_file(path)

        line_offsets = self._file_line_offsets[path]
        line_idx = bisect.bisect_right(line_offsets, offset) - 1
        line_number = line_idx + 1  # 1-based
        column_number = offset - line_offsets[line_idx] + 1  # 1-based
        return line_number, column_number

    def get_text_range(
        self, path: Path, offset_start: int, offset_end: int
    ) -> list[str]:
        """
        Get the text slice between two offsets in a file, split by lines.

        Args:
            path: Path to the file.
            offset_start: Start offset (inclusive).
            offset_end: End offset (exclusive).

        Returns:
            A list of strings, one per line within the range.
        """
        if path not in self._file_contents:
            self.load_file(path)

        text = self._file_contents[path]
        return text[offset_start:offset_end].splitlines()
