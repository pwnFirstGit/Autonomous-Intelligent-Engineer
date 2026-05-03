import os
from typing import List, Dict
from tree_sitter import Parser
from tree_sitter_languages import get_language


class CodeParser:
    def __init__(self, language: str = "python"):
        self.language_name = language
        self.language = None
        self.parser = None

        try:
            self.language = get_language(language)
            self.parser = Parser()
            self.parser.set_language(self.language)
        except Exception as e:
            print(f"Tree-sitter unavailable, falling back to line chunks: {e}")

    def parse_file(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception:
            return []

        # Try tree-sitter first
        try:
            if self.parser is None:
                raise RuntimeError("Parser unavailable")
            tree = self.parser.parse(bytes(code, "utf-8"))
            extracted = []
            self._traverse_tree(tree.root_node, code, extracted, file_path)
            if extracted:
                return extracted
        except Exception:
            pass

        # Fallback: chunk by lines (handles broken/flat files)
        return self._chunk_by_lines(file_path, code)

    def _chunk_by_lines(self, file_path: str, code: str = None, chunk_size: int = 50) -> List[Dict]:
        """Split file into line-based chunks as fallback."""
        if code is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception:
                return []

        lines = code.splitlines()
        chunks = []

        for i in range(0, len(lines), chunk_size):
            chunk = "\n".join(lines[i:i + chunk_size])
            if chunk.strip():
                chunks.append({
                    "type": "chunk",
                    "file": file_path,
                    "start_line": i,
                    "end_line": min(i + chunk_size, len(lines)),
                    "code": chunk,
                })

        return chunks

    def _traverse_tree(self, node, code: str, extracted: List, file_path: str):
        if self.language_name == "python":
            if node.type in ("function_definition", "class_definition"):
                extracted.append(self._extract_node(
                    node, code, file_path,
                    "function" if node.type == "function_definition" else "class"
                ))
        elif self.language_name == "cpp":
            if node.type in ("function_definition", "class_specifier"):
                extracted.append(self._extract_node(
                    node, code, file_path,
                    "function" if node.type == "function_definition" else "class"
                ))

        for child in node.children:
            self._traverse_tree(child, code, extracted, file_path)

    def _extract_node(self, node, code: str, file_path: str, node_type: str) -> Dict:
        snippet = code[node.start_byte:node.end_byte]
        return {
            "type": node_type,
            "file": file_path,
            "start_line": node.start_point[0],
            "end_line": node.end_point[0],
            "code": snippet,
        }

    def parse_repository(self, repo_path: str) -> List[Dict]:
        all_data = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                if self._is_valid_file(file):
                    file_path = os.path.join(root, file)
                    parsed = self.parse_file(file_path)
                    for item in parsed:
                        item["file"] = os.path.relpath(item["file"], repo_path)
                    all_data.extend(parsed)
        return all_data

    def _is_valid_file(self, filename: str) -> bool:
        extensions = {
            "python": [".py"],
            "cpp": [".cpp", ".hpp", ".h"]
        }
        return any(filename.endswith(ext) for ext in extensions.get(self.language_name, []))
