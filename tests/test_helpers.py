import os
import tempfile
from pathlib import Path
import json

from inspector.helpers import (
    read_file_contents,
    smart_resolve_path,
    normalize_and_expand_paths,
    get_all_files_in_directory,
    code_location_expander,
    get_version_info,
    is_valid_scanner_directory,
)


class TestHelpers:
    def test_parse_scope_given_clean_list(self):
        """Clean list of files should be properly matched"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the directory structure
            root = Path(tmpdir)
            (root / "dir1" / "dir2" / "dir3").mkdir(parents=True)
            (root / "dir11" / "dir22" / "dir33").mkdir(parents=True)
            (root / "dir11" / "dir22" / "dir33" / "file.ext").touch()

            valid_files = ["dir1/dir2/dir3", "dir11/dir22/dir33/file.ext"]
            raw_lines = ["dir1/dir2/dir3", "dir11/dir22/dir33/file.ext"]
            valid_paths, invalid_paths = normalize_and_expand_paths(
                raw_lines, project_root=root, label="scope", prefer_project_root=True
            )

            # Convert both to sorted lists for comparison
            relative_paths = sorted(str(path.relative_to(root)) for path in valid_paths)
            sorted_valid_files = sorted(valid_files)

            assert len(valid_files) == len(
                valid_paths
            ), "mismatch between expected and actual scope length"
            assert relative_paths == sorted_valid_files, "mismatch in path contents"
            assert len(invalid_paths) == 0, "should not have any invalid paths"

    def test_parse_scope_incorrect_filenames(self):
        """Scope files with multiple spaces before the filename"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the test file
            root = Path(tmpdir)
            (root / "contract.sol").touch()

            valid_files = [
                "contract.sol",
            ]
            raw_lines = [
                "   ./contract.sol",
            ]
            valid_paths, invalid_paths = normalize_and_expand_paths(
                raw_lines, project_root=root, label="scope", prefer_project_root=True
            )

            assert len(valid_files) == len(
                valid_paths
            ), "mismatch between expected and actual scope length"

            # Compare relative paths by converting both to relative paths
            for i, path in enumerate(valid_paths):
                relative_path = path.relative_to(root)
                assert (
                    str(relative_path) == valid_files[i]
                ), f"mismatch when parsing scope line #{i}"
            assert len(invalid_paths) == 0, "should not have any invalid paths"

    def test_read_file(self):
        """Given a text file, it should return a list with each file line"""
        # Test file with predefined contents
        filename = "/tmp/testing_scope_file_12345.scope"
        file_contents = [
            "============ File contents ============\n",
            "1) dir1/dir2/dir3/file.ext    1   2   3\n",
            "2) dir-11/dir-22/dir-33/file.ext    100   250   355\n",
            "invalid scope line\n",
            "-> End of file.\n",
        ]
        with open(filename, "w") as outfile:
            for line in file_contents:
                outfile.write(line)

        # Read the file and retrieve the list of lines
        file_lines = read_file_contents(filename)

        assert len(file_contents) == len(file_lines), "line count mismatch"
        for i in range(0, len(file_lines)):
            assert file_contents[i] == file_lines[i], f"mismatch on line #{i}"
        os.remove(filename)
        assert not os.path.exists(filename), "test filename not removed correctly"

    def test_get_invalid_scope_paths(self):
        """Test getting invalid scope paths"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files and directories
            valid_file = Path(tmpdir) / "valid.txt"
            valid_file.touch()
            invalid_file = Path(tmpdir) / "invalid.txt"

            raw_lines = [str(valid_file), str(invalid_file)]
            valid_paths, invalid_paths = normalize_and_expand_paths(
                raw_lines,
                project_root=Path(tmpdir),
                label="scope",
                prefer_project_root=True,
            )

            assert len(valid_paths) == 1, "should have one valid path"
            assert len(invalid_paths) == 1, "should have one invalid path"
            assert valid_file in valid_paths, "valid file should be in valid paths"
            assert (
                invalid_file in invalid_paths
            ), "invalid file should be in invalid paths"

    def test_get_all_files_in_directory(self):
        """Test getting all files in a directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test directory structure
            root = Path(tmpdir)
            (root / "dir1").mkdir()
            (root / "dir1" / "file1.txt").touch()
            (root / "file2.txt").touch()

            files = get_all_files_in_directory(root)
            assert len(files) == 2
            assert any("file1.txt" in str(f) for f in files)
            assert any("file2.txt" in str(f) for f in files)

    def test_get_all_files_in_directory_edge_cases(self):
        """Test getting all files in directory with edge cases"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Test empty directory
            assert get_all_files_in_directory(root) == set()

            # Test with hidden files
            (root / ".hidden").touch()
            files = get_all_files_in_directory(root)
            assert len(files) == 1
            assert any(".hidden" in str(f) for f in files)

            # Test with nested empty directories
            (root / "empty_dir").mkdir()
            (root / "empty_dir" / "nested_empty").mkdir()
            assert len(get_all_files_in_directory(root)) == 1  # Only .hidden file

    def test_code_location_expander(self):
        """Test code location expansion"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            root = Path(tmpdir)
            (root / "test.sol").touch()
            (root / "test.txt").touch()

            # Test with both file and directory
            paths = {root / "test.sol", root}
            expanded = code_location_expander(paths)
            assert len(expanded) == 2
            assert any("test.sol" in str(f) for f in expanded)

    def test_code_location_expander_edge_cases(self):
        """Test code location expansion with edge cases"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Empty set
            assert code_location_expander(set()) == set()

            # None values
            assert code_location_expander({None}) == set()

            # Non-existent paths
            assert code_location_expander({root / "nonexistent"}) == set()

            # Single text file
            (root / "test.txt").touch()

            # Multiple .sol files
            (root / "test1.sol").touch()
            (root / "test2.sol").touch()
            expanded = code_location_expander({root})
            assert len(expanded) == 3
            assert any("test1.sol" in str(f) for f in expanded)
            assert any("test2.sol" in str(f) for f in expanded)
            assert any("test.txt" in str(f) for f in expanded)

    def test_is_valid_scanner_directory(self):
        """Test scanner directory validation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # pyproject.toml
            root = Path(tmpdir)
            (root / "pyproject.toml").touch()
            assert is_valid_scanner_directory(root)

            # Executable file
            (root / "scanner").touch()
            os.chmod(root / "scanner", 0o755)
            assert is_valid_scanner_directory(root)

            # Invalid directory
            assert not is_valid_scanner_directory(root / "nonexistent")

    def test_version_info_edge_cases(self):
        """Test version info functions with edge cases"""
        # Test with empty scan results
        md_info = get_version_info([], format="md")
        assert "OpenZeppelin Inspector version" in md_info
        # Test with invalid format, as it defaults to md
        md_info = get_version_info([], format="invalid")
        assert "OpenZeppelin Inspector version" in md_info

    def test_get_version_info_json_string(self):
        """Test get_version_info_string function"""
        string_info = get_version_info([], format="json")
        assert isinstance(string_info, str)
        # Verify the string is valid JSON by attempting to parse it
        parsed_json = json.loads(string_info)
        assert isinstance(parsed_json, dict)
        assert "contract-inspector-version" in parsed_json

    def test_smart_resolve_path(self):
        """Test smart_resolve_path with various path scenarios"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files and directories
            root = Path(tmpdir)
            (root / "test.txt").touch()
            (root / "dir1" / "dir2").mkdir(parents=True)
            (root / "dir1" / "dir2" / "test2.txt").touch()

            # Test absolute path that exists
            abs_path = root / "test.txt"
            resolved = smart_resolve_path(str(abs_path), root)
            assert resolved == abs_path.resolve()

            # Test relative path with project root preferred
            rel_path = "test.txt"
            resolved = smart_resolve_path(rel_path, root, prefer_project_root=True)
            assert resolved == (root / rel_path).resolve()

            # Test relative path with cwd preferred
            rel_path = "test.txt"
            resolved = smart_resolve_path(rel_path, root, prefer_project_root=False)
            assert resolved == (root / rel_path).resolve()

            # Test nested relative path
            rel_path = "dir1/dir2/test2.txt"
            resolved = smart_resolve_path(rel_path, root)
            assert resolved == (root / rel_path).resolve()

            # Test non-existent path
            non_existent = "nonexistent.txt"
            resolved = smart_resolve_path(non_existent, root)
            assert resolved is None

            # Test path with spaces
            spaced_path = root / "path with spaces.txt"
            spaced_path.touch()
            resolved = smart_resolve_path("path with spaces.txt", root)
            assert resolved == spaced_path.resolve()

    def test_smart_resolve_path_edge_cases(self):
        """Test smart_resolve_path with edge cases"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Test empty string
            resolved = smart_resolve_path("", root)
            assert resolved == Path.cwd()

            # Test None input
            resolved = smart_resolve_path(None, root)
            assert resolved is None

            # Test path with special characters
            special_path = root / "test@#$%.txt"
            special_path.touch()
            resolved = smart_resolve_path("test@#$%.txt", root)
            assert resolved == special_path.resolve()

            # Test path with leading/trailing spaces
            spaced_path = root / "test.txt"
            spaced_path.touch()
            resolved = smart_resolve_path("   test.txt   ", root)
            assert resolved == spaced_path.resolve()

            # Test path with multiple slashes, incorrect path so it is None
            resolved = smart_resolve_path("dir1//dir2/test2.txt", root)
            assert resolved is None
