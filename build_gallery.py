#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ローカルの media/ 配下を走査して、タブ付きのギャラリー index.html を自動生成します。
- サブフォルダーごとにタブ（例: artist1, artist2）を作成
- 画像はサムネイル表示 → クリックで拡大表示
- 動画は再生アイコン付きのサムネ表示 → クリックでモーダル再生
- pathlib のみを使用（os.path 非使用）

使い方:
  $ python build_gallery.py
  # your_project/index.html が生成されます

構成（例）:
  your_project/
  ├─ media/
  │   ├─ artist1/
  │   │   └─ cat.jpg
  │   ├─ artist2/
  │   │   └─ cat2.jpg
  │   │   └─ cat3.jpg
  └─ build_gallery.py

必要に応じて MEDIA_DIR や OUTPUT_HTML を調整してください。
"""

from __future__ import annotations
from pathlib import Path
from html import escape

# ===== 設定 =====
ROOT_DIR: Path = Path(__file__).parent.resolve()
MEDIA_DIR: Path = ROOT_DIR / "media"
OUTPUT_HTML: Path = ROOT_DIR / "index.html"

# 対応拡張子（すべて小文字・ドット無し）
IMAGE_EXTS = {
    "jpg", "jpeg", "png", "gif", "webp", "avif", "bmp", "svg"
}
VIDEO_EXTS = {
    "mp4", "webm", "ogv", "mov", "m4v"
}
ALL_EXTS = IMAGE_EXTS | VIDEO_EXTS


def is_media_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower().lstrip(".") in ALL_EXTS


def is_image(p: Path) -> bool:
    return p.suffix.lower().lstrip(".") in IMAGE_EXTS


def is_video(p: Path) -> bool:
    return p.suffix.lower().lstrip(".") in VIDEO_EXTS




def rel_url(path: Path) -> str:
    """index.html からの相対パス URL を生成（/ 区切り）。"""
    return path.relative_to(ROOT_DIR).as_posix()


def build_gallery_data(media_root: Path) -> list[dict]:
    """
    media_root 直下のディレクトリをアーティスト（タブ）として扱い、
    その中のメディアファイルを列挙したデータ構造を返します。
    戻り値の各要素：{
      "name": フォルダー名,
      "slug": スラッグ,
      "items": [ {"url": 相対URL, "name": ファイル名, "kind": "image"|"video"}, ... ]
    }
    """
    if not media_root.exists():
        raise FileNotFoundError(f"MEDIA_DIR が見つかりません: {media_root}")

    tabs: list[dict] = []
    for sub in sorted(media_root.iterdir(), key=lambda p: p.name.lower()):
        if not sub.is_dir():
            continue
        files = [p for p in sorted(sub.iterdir(), key=lambda p: p.name.lower()) if is_media_file(p)]
        if not files:
            continue
        tab = {
            "name": sub.name,
            "slug": sub.name,
            "items": [],
        }
        for f in files:
            tab["items"].append({
                "url": rel_url(f),
                "name": f.name,
                "kind": "image" if is_image(f) else ("video" if is_video(f) else "other"),
            })
        tabs.append(tab)
    return tabs


def render_index_html(tabs: list[dict]) -> str:
    """タブ・グリッド・モーダル付きの単一 HTML を返す。CSS/JS も同梱。"""
    # タブボタン
    tab_buttons_html = []
    tab_panels_html = []

    # 最初のタブをデフォルトでアクティブ
    default_active = tabs[0]["slug"] if tabs else ""

    for tab in tabs:
        name = escape(tab["name"])  # 表示用
        slug = escape(tab["slug"])  # id/属性用
        count = len(tab["items"])   # カウント表示

        tab_buttons_html.append(
            f'<button class="tab-btn" role="tab" data-target="{slug}">' \
            f'<span class="tab-name">{name}</span>' \
            f'<span class="tab-count">{count}</span>' \
            f"</button>"
        )

        # 各パネルのグリッド
        tiles = []
        for item in tab["items"]:
            url = escape(item["url"])  # 相対URL
            fname = escape(item["name"])  # alt/label
            if item["kind"] == "image":
                tiles.append(
                    """
<li class="tile" data-kind="image" data-src="{url}" aria-label="{fname}">
  <img src="{url}" alt="{fname}" loading="lazy" />
</li>
                    """.strip().format(url=url, fname=fname)
                )
            elif item["kind"] == "video":
                tiles.append(
                    """
<li class="tile video" data-kind="video" data-src="{url}" aria-label="{fname}">
  <div class="video-thumb" title="{fname}">
    <div class="play-icon" aria-hidden="true"></div>
    <div class="filename">{short}</div>
  </div>
</li>
                    """.strip().format(url=url, fname=fname, short=escape(shorten_name(item["name"])) )
                )
        panel_html = (
            f'<section id="{slug}" class="panel" role="tabpanel" aria-labelledby="tab-{slug}">\n'
            f'  <ul class="grid">\n    ' + "\n    ".join(tiles) + "\n  </ul>\n"
            f"</section>"
        )
        tab_panels_html.append(panel_html)

    html_doc = f"""<!doctype html>
<html lang=\"ja\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Local Media Gallery</title>
  <style>
    :root {{
      --bg: #0b0c10;
      --panel: #111217;
      --text: #e6e6e6;
      --muted: #a0a0a0;
      --accent: #4f46e5;
      --accent-2: #22d3ee;
      --border: #23242c;
      --tile: #151722;
      --shadow: 0 6px 24px rgba(0,0,0,.35);
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ height: 100%; }}
    body {{
      margin: 0; padding: 0;
      background: linear-gradient(180deg, #0b0c10 0%, #0e1018 100%);
      color: var(--text);
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, \"Apple Color Emoji\", \"Segoe UI Emoji\";
    }}
    header {{ position: sticky; top: 0; z-index: 20; backdrop-filter: blur(8px); background: rgba(11,12,16,.6); border-bottom: 1px solid var(--border); }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 12px 16px; }}

    .title {{ display: flex; align-items: center; gap: 10px; padding: 8px 0 12px; }}
    .title h1 {{ font-size: 20px; margin: 0; letter-spacing: .2px; }}
    .badge {{ font-size: 12px; padding: 2px 8px; background: #0f172a; border: 1px solid var(--border); border-radius: 999px; color: var(--muted); }}

    .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; padding-bottom: 10px; }}
    .tab-btn {{
      border: 1px solid var(--border);
      background: linear-gradient(180deg, #151823, #121521);
      color: var(--text);
      padding: 8px 10px; border-radius: 10px;
      cursor: pointer; box-shadow: var(--shadow);
      display: inline-flex; align-items: center; gap: 8px;
      transition: transform .08s ease, border-color .15s ease, box-shadow .15s ease;
    }}
    .tab-btn:hover {{ transform: translateY(-1px); border-color: #2a2d3a; }}
    .tab-btn.active {{ outline: 2px solid var(--accent); }}
    .tab-name {{ font-weight: 600; }}
    .tab-count {{ font-size: 12px; color: var(--muted); background: #0b0d14; border: 1px solid var(--border); padding: 2px 6px; border-radius: 999px; }}

    main {{ max-width: 1200px; margin: 0 auto; padding: 16px; }}
    .panel {{ display: none; }}
    .panel.active {{ display: block; }}

    .grid {{ list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }}
    .tile {{
      position: relative; background: var(--tile); border: 1px solid var(--border);
      border-radius: 16px; overflow: hidden; aspect-ratio: 1 / 1; box-shadow: var(--shadow);
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      transition: transform .08s ease, border-color .15s ease, box-shadow .15s ease;
    }}
    .tile:hover {{ transform: translateY(-2px); border-color: #2a2d3a; }}
    .tile img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}

    /* 動画タイル */
    .video .video-thumb {{
      width: 100%; height: 100%; display: grid; place-items: center;
      background: radial-gradient(60% 60% at 50% 50%, rgba(34,211,238,.08) 0%, rgba(79,70,229,.08) 100%), #0d101a;
    }}
    .video .filename {{ position: absolute; left: 8px; bottom: 8px; font-size: 12px; color: var(--muted); background: rgba(0,0,0,.45); padding: 2px 6px; border-radius: 6px; border: 1px solid rgba(255,255,255,.1); }}
    .play-icon {{
      width: 54px; height: 54px; border-radius: 999px; border: 2px solid rgba(255,255,255,.7);
      display: grid; place-items: center; box-shadow: 0 0 0 6px rgba(255,255,255,.08);
    }}
    .play-icon::before {{
      content: ""; display: block; width: 0; height: 0;
      border-left: 16px solid rgba(255,255,255,.9);
      border-top: 10px solid transparent; border-bottom: 10px solid transparent;
      margin-left: 4px;
    }}

    /* ビューア（モーダル） */
    .viewer {{
      position: fixed; inset: 0; background: rgba(3,6,12,.9);
      display: none; align-items: center; justify-content: center; padding: 24px; z-index: 50;
    }}
    .viewer.active {{ display: flex; }}
    .viewer .inner {{ position: relative; max-width: 96vw; max-height: 90vh; width: min(1200px, 96vw); }}
    .viewer .frame {{ background: #000; border-radius: 16px; overflow: hidden; border: 1px solid var(--border); box-shadow: var(--shadow); }}
    .viewer img, .viewer video {{ display: block; max-width: 100%; max-height: 80vh; margin: 0 auto; }}
    .viewer .close {{ position: absolute; top: -12px; right: -12px; background: #0f172a; color: #fff; border: 1px solid var(--border); border-radius: 999px; width: 36px; height: 36px; display: grid; place-items: center; cursor: pointer; box-shadow: var(--shadow); }}
    .viewer .meta {{ margin-top: 10px; text-align: center; color: var(--muted); font-size: 13px; }}

    footer {{ max-width: 1200px; margin: 32px auto 48px; padding: 0 16px; color: var(--muted); font-size: 12px; text-align: center; }}
    a, a:visited {{ color: var(--accent-2); }}
  </style>
</head>
<body>
  <header>
    <div class=\"container\">
      <div class=\"title\">
        <h1>Local Media Gallery</h1>
        <span class=\"badge\">static / generated</span>
      </div>
      <nav class=\"tabs\" role=\"tablist\" aria-label=\"Folders\">
        {''.join(tab_buttons_html)}
      </nav>
    </div>
  </header>

  <main>
    {''.join(tab_panels_html)}
  </main>

  <div id=\"viewer\" class=\"viewer\" aria-hidden=\"true\">
    <div class=\"inner\">
      <button class=\"close\" aria-label=\"Close\">✕</button>
      <div class=\"frame\"></div>
      <div class=\"meta\"></div>
    </div>
  </div>

  <footer>
    生成物: <code>index.html</code> ・ メディアは <code>media/</code> 配下の各フォルダへ入れるだけ
  </footer>

<script>
(function(){{
  const $ = (sel, root=document) => root.querySelector(sel);
  const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

  // タブ切り替え
  const tabs = $$('.tab-btn');
  const panels = $$('.panel');
  const KEY = 'gallery:lastTab';

  function activate(slug) {{
    tabs.forEach(btn => btn.classList.toggle('active', btn.dataset.target === slug));
    panels.forEach(p => p.classList.toggle('active', p.id === slug));
    localStorage.setItem(KEY, slug);
  }}

  tabs.forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.target)));

  // 初期アクティブ（ローカルストレージ優先）
  const initial = localStorage.getItem(KEY) || '{default_active}';
  if (initial) activate(initial);

  // ビューア（モーダル）
  const viewer = $('#viewer');
  const frame = $('.frame', viewer);
  const meta = $('.meta', viewer);
  const closeBtn = $('.close', viewer);

  function openViewer(kind, src, name) {{
    frame.innerHTML = '';
    meta.textContent = name || '';
    if (kind === 'image') {{
      const img = new Image();
      img.src = src; img.alt = name || '';
      img.loading = 'eager';
      frame.appendChild(img);
    }} else if (kind === 'video') {{
      const v = document.createElement('video');
      v.src = src; v.controls = true; v.autoplay = true; v.playsInline = true;
      frame.appendChild(v);
    }}
    viewer.classList.add('active');
    viewer.setAttribute('aria-hidden', 'false');
  }}

  function closeViewer() {{
    viewer.classList.remove('active');
    viewer.setAttribute('aria-hidden', 'true');
    frame.innerHTML = '';
  }}

  closeBtn.addEventListener('click', closeViewer);
  viewer.addEventListener('click', (e) => {{ if (e.target === viewer) closeViewer(); }});
  document.addEventListener('keydown', (e) => {{ if (e.key === 'Escape') closeViewer(); }});

  // タイルクリックで開く
  $$('.grid .tile').forEach(tile => {{
    tile.addEventListener('click', () => {{
      const kind = tile.dataset.kind;
      const src  = tile.dataset.src;
      const name = tile.getAttribute('aria-label') || '';
      openViewer(kind, src, name);
    }});
  }});
}})();

</script>
</body>
</html>
"""
    return html_doc


def shorten_name(name: str, max_len: int = 22) -> str:
    base = name
    if len(base) <= max_len:
        return base
    # 拡張子はなるべく残す
    stem = Path(base).stem
    ext = Path(base).suffix
    if len(ext) > 6:
        ext = ext[:6] + '…'
    keep = max_len - len(ext) - 1  # 1 は省略記号
    if keep < 3:
        keep = 3
    return stem[:keep] + '…' + ext


def main() -> None:
    tabs = build_gallery_data(MEDIA_DIR)
    html = render_index_html(tabs)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"✅ ギャラリーを生成しました: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
