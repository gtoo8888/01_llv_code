"""
论文库可视化 - 后端
使用 FastAPI
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from subjects import translate_name


STATIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class TreeNode(BaseModel):
    name: str
    children: list["TreeNode"] = []
    paper_count: int = 0


class DirScanRequest(BaseModel):
    path: str
    include_files: bool = False


def count_pdfs(base_path: str) -> int:
    """统计目录下所有 PDF 文件数量（含子目录）"""
    count = 0
    try:
        for entry in os.listdir(base_path):
            entry_path = os.path.join(base_path, entry)
            if os.path.isdir(entry_path):
                count += count_pdfs(entry_path)
            elif os.path.isfile(entry_path) and entry.lower().endswith(".pdf"):
                count += 1
    except (PermissionError, FileNotFoundError, OSError):
        pass
    return count


def scan_dir(base_path: str, include_files: bool = False) -> list[TreeNode]:
    """
    扫描目录，返回树结构。
    - include_files=True：文件作为节点加入 children
    - paper_count：始终反映该目录下所有 PDF 总数
    """
    result = []
    try:
        entries = sorted(os.listdir(base_path))
    except (PermissionError, FileNotFoundError, OSError):
        return result

    for entry in entries:
        entry_path = os.path.join(base_path, entry)
        if os.path.isdir(entry_path):
            children = scan_dir(entry_path, include_files)
            paper_count = count_pdfs(entry_path)
            result.append(TreeNode(name=entry, children=children, paper_count=paper_count))
        elif include_files and os.path.isfile(entry_path):
            is_pdf = entry.lower().endswith(".pdf")
            result.append(TreeNode(name=entry, children=[], paper_count=1 if is_pdf else 0))

    return result


def scan_dir_with_translation(base_path: str, depth: int = 0) -> list[TreeNode]:
    """
    扫描目录并翻译目录名为中文（用于旭日图）。
    只扫描到第三层（学科体系），不包含文件。
    """
    result = []
    try:
        entries = sorted(os.listdir(base_path))
    except (PermissionError, FileNotFoundError, OSError):
        return result

    for entry in entries:
        entry_path = os.path.join(base_path, entry)
        if os.path.isdir(entry_path):
            paper_count = count_pdfs(entry_path)
            chinese_name = translate_name(entry)
            if depth < 2:
                children = scan_dir_with_translation(entry_path, depth + 1)
                result.append(TreeNode(name=chinese_name, children=children, paper_count=paper_count))
            else:
                result.append(TreeNode(name=chinese_name, children=[], paper_count=paper_count))

    return result


app = FastAPI(title="论文库可视化")

app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


@app.post("/tree")
async def get_tree(req: DirScanRequest) -> list[TreeNode]:
    return scan_dir(req.path, req.include_files)


@app.post("/sunburst")
async def get_sunburst(req: DirScanRequest) -> list[TreeNode]:
    """
    旭日图专用接口：返回中文目录名（不含文件）。
    """
    return scan_dir_with_translation(req.path)


@app.get("/", response_class=HTMLResponse)
async def root():
    with open(os.path.join(STATIC_PATH, "overview.html"), "r", encoding="utf-8") as f:
        return f.read()


@app.get("/tree.html", response_class=HTMLResponse)
async def tree():
    with open(os.path.join(STATIC_PATH, "tree.html"), "r", encoding="utf-8") as f:
        return f.read()


@app.get("/sunburst.html", response_class=HTMLResponse)
async def sunburst():
    with open(os.path.join(STATIC_PATH, "sunburst.html"), "r", encoding="utf-8") as f:
        return f.read()


@app.get("/wordcloud.html", response_class=HTMLResponse)
async def wordcloud():
    with open(os.path.join(STATIC_PATH, "wordcloud.html"), "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
