// API 调用封装

async function fetchTree(path, includeFiles = false) {
    const res = await fetch("/tree", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, include_files: includeFiles }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "未知错误" }));
        throw new Error(err.detail || `请求失败 (${res.status})`);
    }
    return res.json();
}

async function fetchSunburst(path) {
    const res = await fetch("/sunburst", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "未知错误" }));
        throw new Error(err.detail || `请求失败 (${res.status})`);
    }
    return res.json();
}
