import os
import shutil
import zipfile
import io
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_from_directory, redirect, url_for, send_file
from PIL import Image, ImageEnhance

app = Flask(__name__)

STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nas_storage')
os.makedirs(STORAGE_DIR, exist_ok=True)

app.config['UPLOAD_FOLDER'] = STORAGE_DIR
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024  # 4 GB limit

IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'}
VIDEO_EXTS = {'mp4', 'webm', 'mov', 'mkv', 'avi', 'flv'}
AUDIO_EXTS = {'mp3', 'wav', 'ogg', 'm4a', 'flac'}
DOC_EXTS = {'pdf', 'docx', 'doc', 'txt', 'xlsx', 'pptx', 'csv', 'json', 'py', 'md', 'zip', 'tar', 'gz'}
TEXT_EXTS = {'txt', 'csv', 'json', 'py', 'md', 'html', 'css', 'js', 'log'}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python NAS Storage Hub</title>
    <style>
        :root {
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --danger: #ef4444;
            
            /* Category Colors */
            --color-img: #3b82f6;
            --color-vid: #8b5cf6;
            --color-doc: #10b981;
            --color-aud: #f59e0b;
            --color-other: #64748b;
            --color-free: #e2e8f0;
        }

        [data-theme="dark"] {
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --color-free: #334155;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 16px; max-width: 1100px; margin: 0 auto; transition: background 0.3s, color 0.3s; }

        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
        h1 { font-size: 1.6rem; color: var(--primary); }

        .card { background: var(--card-bg); border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.05); }

        /* Categorized Segmented Storage Bar */
        .storage-bar { display: flex; height: 22px; width: 100%; border-radius: 8px; overflow: hidden; background: var(--color-free); margin: 12px 0; }
        .storage-segment { height: 100%; transition: width 0.4s ease; }
        
        .storage-legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 0.85rem; color: var(--text-muted); margin-top: 8px; }
        .legend-item { display: flex; align-items: center; gap: 6px; }
        .legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }

        /* Toolbar Controls */
        .toolbar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }
        .search-input { flex: 1; min-width: 200px; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--card-bg); color: var(--text); font-size: 0.9rem; }
        .filter-btn { padding: 8px 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--card-bg); color: var(--text); cursor: pointer; font-size: 0.85rem; }
        .filter-btn.active { background: var(--primary); color: white; border-color: var(--primary); }

        /* Upload & Progress */
        .upload-area { border: 2px dashed var(--primary); border-radius: 8px; padding: 20px; text-align: center; cursor: pointer; transition: background 0.2s; }
        .upload-area:hover { background: rgba(37, 99, 235, 0.05); }
        #fileInput { display: none; }
        .progress-wrapper { display: none; margin-top: 15px; }
        .progress-bar-bg { background: var(--border); border-radius: 6px; height: 12px; overflow: hidden; }
        .progress-bar-fill { background: #10b981; height: 100%; width: 0%; transition: width 0.1s; }
        .progress-text { display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 6px; color: var(--text-muted); }

        /* File Cards Grid */
        .file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-top: 15px; }
        .file-card { border: 1px solid var(--border); border-radius: 10px; padding: 14px; background: var(--card-bg); display: flex; flex-direction: column; justify-content: space-between; position: relative; }
        .file-header { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; }
        .file-badge { font-size: 0.7rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; color: white; }
        .badge-image { background: var(--color-img); }
        .badge-video { background: var(--color-vid); }
        .badge-audio { background: var(--color-aud); }
        .badge-document { background: var(--color-doc); }
        .badge-other { background: var(--color-other); }

        .file-name { font-weight: 600; word-break: break-all; font-size: 0.95rem; line-height: 1.3; }
        .file-info { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px; }
        .file-actions { display: flex; gap: 6px; flex-wrap: wrap; margin-top: auto; }

        /* Buttons */
        .btn { padding: 8px 12px; border-radius: 6px; border: none; cursor: pointer; font-size: 0.85rem; font-weight: 500; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 4px; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-danger { background: var(--danger); color: white; }
        .btn-secondary { background: var(--border); color: var(--text); }

        /* Modals */
        .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 1000; justify-content: center; align-items: center; padding: 16px; }
        .modal-content { background: var(--card-bg); color: var(--text); border-radius: 12px; padding: 20px; max-width: 700px; width: 100%; max-height: 90vh; overflow-y: auto; }
        .editor-preview { width: 100%; max-height: 350px; object-fit: contain; background: #000; border-radius: 8px; margin: 12px 0; }
        .controls-group { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
        .control-item { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 120px; }
        textarea.text-editor { width: 100%; height: 300px; font-family: monospace; padding: 10px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); color: var(--text); resize: vertical; margin: 10px 0; }

        @media (max-width: 600px) {
            body { padding: 10px; }
            .file-grid { grid-template-columns: 1fr; }
            .btn { width: 100%; }
            .toolbar { flex-direction: column; align-items: stretch; }
        }
    </style>
</head>
<body>

    <header>
        <div>
            <h1>💾 Python NAS Storage</h1>
            <p style="color: var(--text-muted); font-size: 0.85rem;">Mobile-Friendly Local Cloud</p>
        </div>
        <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary" onclick="toggleTheme()">🌓 Theme</button>
            <button class="btn btn-primary" onclick="downloadSelectedZip()">📦 Zip Selected</button>
        </div>
    </header>

    <!-- Color Categorized Storage Overview -->
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>Storage Usage Breakdown</h3>
            <span style="font-size:0.85rem; color:var(--text-muted);">Total: {{ storage.total_gb }} GB</span>
        </div>

        <div class="storage-bar">
            <div class="storage-segment" style="width: {{ storage.pct_img }}%; background: var(--color-img);" title="Images: {{ storage.gb_img }} GB"></div>
            <div class="storage-segment" style="width: {{ storage.pct_vid }}%; background: var(--color-vid);" title="Videos: {{ storage.gb_vid }} GB"></div>
            <div class="storage-segment" style="width: {{ storage.pct_aud }}%; background: var(--color-aud);" title="Audio: {{ storage.gb_aud }} GB"></div>
            <div class="storage-segment" style="width: {{ storage.pct_doc }}%; background: var(--color-doc);" title="Documents: {{ storage.gb_doc }} GB"></div>
            <div class="storage-segment" style="width: {{ storage.pct_other }}%; background: var(--color-other);" title="Other: {{ storage.gb_other }} GB"></div>
        </div>

        <div class="storage-legend">
            <div class="legend-item"><span class="legend-dot" style="background: var(--color-img);"></span> Images: {{ storage.gb_img }} GB ({{ storage.pct_img }}%)</div>
            <div class="legend-item"><span class="legend-dot" style="background: var(--color-vid);"></span> Videos: {{ storage.gb_vid }} GB ({{ storage.pct_vid }}%)</div>
            <div class="legend-item"><span class="legend-dot" style="background: var(--color-aud);"></span> Audio: {{ storage.gb_aud }} GB ({{ storage.pct_aud }}%)</div>
            <div class="legend-item"><span class="legend-dot" style="background: var(--color-doc);"></span> Documents: {{ storage.gb_doc }} GB ({{ storage.pct_doc }}%)</div>
            <div class="legend-item"><span class="legend-dot" style="background: var(--color-other);"></span> Other: {{ storage.gb_other }} GB ({{ storage.pct_other }}%)</div>
            <div class="legend-item"><span class="legend-dot" style="background: var(--color-free);"></span> Free: {{ storage.free_gb }} GB</div>
        </div>
    </div>

    <!-- Upload Card -->
    <div class="card">
        <h3>Upload Files</h3>
        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            📁 Tap to Select or Drag Files Here
            <input type="file" id="fileInput" multiple onchange="uploadFiles()">
        </div>
        <div class="progress-wrapper" id="progressWrapper">
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progressBar"></div>
            </div>
            <div class="progress-text">
                <span id="progressStatus">Uploading...</span>
                <span id="progressPercent">0%</span>
            </div>
        </div>
    </div>

    <!-- Storage File Manager Card -->
    <div class="card">
        <div class="toolbar">
            <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search files..." oninput="filterFiles()">
            <button class="filter-btn active" onclick="setCategoryFilter('all', this)">All</button>
            <button class="filter-btn" onclick="setCategoryFilter('image', this)">Images</button>
            <button class="filter-btn" onclick="setCategoryFilter('video', this)">Videos</button>
            <button class="filter-btn" onclick="setCategoryFilter('audio', this)">Audio</button>
            <button class="filter-btn" onclick="setCategoryFilter('document', this)">Docs</button>
            <button class="filter-btn" onclick="setCategoryFilter('other', this)">Other</button>
        </div>

        <div class="file-grid" id="fileGrid">
            {% for file in files %}
            <div class="file-card" data-name="{{ file.name|lower }}" data-category="{{ file.category }}">
                <div>
                    <div class="file-header">
                        <input type="checkbox" class="file-select-checkbox" value="{{ file.name }}">
                        <span class="file-badge badge-{{ file.category }}">{{ file.category }}</span>
                    </div>
                    <div class="file-name">{{ file.name }}</div>
                    <div class="file-info">
                        📅 {{ file.date }}<br>
                        📦 {{ file.size_mb }} MB
                    </div>
                </div>

                {% if file.category == 'audio' %}
                <audio controls style="width: 100%; margin-bottom: 10px;">
                    <source src="/files/{{ file.name }}">
                </audio>
                {% endif %}

                <div class="file-actions">
                    <a href="/files/{{ file.name }}" target="_blank" class="btn btn-secondary">Open</a>
                    <button class="btn btn-secondary" onclick="renameFile('{{ file.name }}')">✏️</button>
                    {% if file.category == 'image' %}
                    <button class="btn btn-primary" onclick="openImageEditor('{{ file.name }}')">Edit Image</button>
                    {% endif %}
                    {% if file.category == 'video' %}
                    <button class="btn btn-primary" onclick="openVideoEditor('{{ file.name }}')">Trim Video</button>
                    {% endif %}
                    {% if file.is_text %}
                    <button class="btn btn-primary" onclick="openTextEditor('{{ file.name }}')">Edit Text</button>
                    {% endif %}
                    <a href="/delete/{{ file.name }}" class="btn btn-danger" onclick="return confirm('Delete this file?')">🗑️</a>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Image Editor Modal -->
    <div class="modal" id="imageModal">
        <div class="modal-content">
            <h3>🖼️ Image Editor</h3>
            <img id="imagePreview" class="editor-preview" src="" alt="Preview">
            <div class="controls-group">
                <div class="control-item">
                    <label>Rotate</label>
                    <button class="btn btn-secondary" onclick="rotateImage()">Rotate 90°</button>
                </div>
                <div class="control-item">
                    <label>Brightness: <span id="brightVal">1.0</span></label>
                    <input type="range" id="brightRange" min="0.2" max="2.0" step="0.1" value="1.0" oninput="updateImageParams()">
                </div>
                <div class="control-item">
                    <label>Contrast: <span id="contrastVal">1.0</span></label>
                    <input type="range" id="contrastRange" min="0.2" max="2.0" step="0.1" value="1.0" oninput="updateImageParams()">
                </div>
            </div>
            <div class="file-actions">
                <button class="btn btn-primary" onclick="saveEditedImage()">Save Changes</button>
                <button class="btn btn-secondary" onclick="closeModal('imageModal')">Cancel</button>
            </div>
        </div>
    </div>

    <!-- Video Editor Modal -->
    <div class="modal" id="videoModal">
        <div class="modal-content">
            <h3>🎬 Video Trimmer</h3>
            <video id="videoPreview" class="editor-preview" controls></video>
            <div class="controls-group">
                <div class="control-item">
                    <label>Start (sec)</label>
                    <input type="number" id="trimStart" min="0" value="0">
                </div>
                <div class="control-item">
                    <label>End (sec)</label>
                    <input type="number" id="trimEnd" min="1" value="10">
                </div>
            </div>
            <div class="file-actions">
                <button class="btn btn-primary" onclick="trimVideo()">Trim & Save</button>
                <button class="btn btn-secondary" onclick="closeModal('videoModal')">Close</button>
            </div>
        </div>
    </div>

    <!-- Text Document Editor Modal -->
    <div class="modal" id="textModal">
        <div class="modal-content">
            <h3 id="textEditorTitle">📄 Text Editor</h3>
            <textarea id="textContent" class="text-editor"></textarea>
            <div class="file-actions">
                <button class="btn btn-primary" onclick="saveTextFile()">Save File</button>
                <button class="btn btn-secondary" onclick="closeModal('textModal')">Close</button>
            </div>
        </div>
    </div>

    <script>
        let currentFile = "";
        let currentRotation = 0;
        let activeCategory = "all";

        // Theme Toggle
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
        }

        // Multi-file Upload
        function uploadFiles() {
            const input = document.getElementById('fileInput');
            if (!input.files.length) return;

            const formData = new FormData();
            for (let i = 0; i < input.files.length; i++) {
                formData.append('files', input.files[i]);
            }

            const xhr = new XMLHttpRequest();
            const wrapper = document.getElementById('progressWrapper');
            const bar = document.getElementById('progressBar');
            const percentText = document.getElementById('progressPercent');

            wrapper.style.display = 'block';

            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    bar.style.width = percent + '%';
                    percentText.innerText = percent + '%';
                }
            };

            xhr.onload = function() {
                if (xhr.status === 200) window.location.reload();
                else alert('Upload failed.');
            };

            xhr.open('POST', '/upload', true);
            xhr.send(formData);
        }

        // Search & Category Filtering
        function filterFiles() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.file-card');

            cards.forEach(card => {
                const name = card.getAttribute('data-name');
                const cat = card.getAttribute('data-category');

                const matchesQuery = name.includes(query);
                const matchesCat = (activeCategory === 'all' || cat === activeCategory);

                card.style.display = (matchesQuery && matchesCat) ? 'flex' : 'none';
            });
        }

        function setCategoryFilter(category, btn) {
            activeCategory = category;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterFiles();
        }

        // File Renaming
        function renameFile(filename) {
            const newName = prompt('Enter new filename:', filename);
            if (!newName || newName === filename) return;

            fetch('/api/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_name: filename, new_name: newName })
            }).then(res => res.json()).then(data => {
                if (data.status === 'ok') window.location.reload();
                else alert(data.error || 'Rename failed');
            });
        }

        // Zip Selected Files
        function downloadSelectedZip() {
            const checkboxes = document.querySelectorAll('.file-select-checkbox:checked');
            const selected = Array.from(checkboxes).map(cb => cb.value);

            if (selected.length === 0) {
                alert('Please select at least one file using the checkboxes.');
                return;
            }

            fetch('/api/download-zip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filenames: selected })
            }).then(res => res.blob()).then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'nas_archive.zip';
                document.body.appendChild(a);
                a.click();
                a.remove();
            });
        }

        // Text Editor
        function openTextEditor(filename) {
            currentFile = filename;
            document.getElementById('textEditorTitle').innerText = '📄 Editing ' + filename;
            fetch('/files/' + filename).then(res => res.text()).then(text => {
                document.getElementById('textContent').value = text;
                document.getElementById('textModal').style.display = 'flex';
            });
        }

        function saveTextFile() {
            const content = document.getElementById('textContent').value;
            fetch('/api/save-text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: currentFile, content: content })
            }).then(res => res.json()).then(data => {
                if (data.status === 'ok') closeModal('textModal');
                else alert('Save failed.');
            });
        }

        // Image Editor
        function openImageEditor(filename) {
            currentFile = filename;
            currentRotation = 0;
            document.getElementById('brightRange').value = 1.0;
            document.getElementById('contrastRange').value = 1.0;
            document.getElementById('imagePreview').src = '/files/' + filename + '?t=' + new Date().getTime();
            document.getElementById('imageModal').style.display = 'flex';
        }

        function updateImageParams() {
            document.getElementById('brightVal').innerText = document.getElementById('brightRange').value;
            document.getElementById('contrastVal').innerText = document.getElementById('contrastRange').value;
        }

        function rotateImage() {
            currentRotation = (currentRotation + 90) % 360;
            document.getElementById('imagePreview').style.transform = `rotate(${currentRotation}deg)`;
        }

        function saveEditedImage() {
            fetch('/api/edit-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: currentFile,
                    rotation: currentRotation,
                    brightness: parseFloat(document.getElementById('brightRange').value),
                    contrast: parseFloat(document.getElementById('contrastRange').value)
                })
            }).then(res => res.json()).then(data => {
                if (data.status === 'ok') window.location.reload();
                else alert(data.error || 'Failed to edit image');
            });
        }

        // Video Editor
        function openVideoEditor(filename) {
            currentFile = filename;
            const player = document.getElementById('videoPreview');
            player.src = '/files/' + filename;
            document.getElementById('videoModal').style.display = 'flex';
            player.onloadedmetadata = function() {
                document.getElementById('trimStart').value = 0;
                document.getElementById('trimEnd').value = Math.floor(player.duration);
            };
        }

        function trimVideo() {
            fetch('/api/trim-video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: currentFile,
                    start: parseFloat(document.getElementById('trimStart').value),
                    end: parseFloat(document.getElementById('trimEnd').value)
                })
            }).then(res => res.json()).then(data => {
                if (data.status === 'ok') window.location.reload();
                else alert('Video trimming requires ffmpeg on the host.');
            });
        }

        function closeModal(id) {
            document.getElementById(id).style.display = 'none';
        }
    </script>
</body>
</html>
"""

def categorize_ext(ext):
    ext = ext.lower()
    if ext in IMAGE_EXTS: return 'image'
    if ext in VIDEO_EXTS: return 'video'
    if ext in AUDIO_EXTS: return 'audio'
    if ext in DOC_EXTS: return 'document'
    return 'other'

def get_categorized_storage():
    total, used, free = shutil.disk_usage(STORAGE_DIR)
    cat_sizes = {'image': 0, 'video': 0, 'audio': 0, 'document': 0, 'other': 0}

    for fname in os.listdir(STORAGE_DIR):
        fpath = os.path.join(STORAGE_DIR, fname)
        if os.path.isfile(fpath):
            ext = fname.split('.')[-1] if '.' in fname else ''
            cat = categorize_ext(ext)
            cat_sizes[cat] += os.path.getsize(fpath)

    total_gb = max(total / (1024**3), 0.001)

    return {
        'total_gb': round(total_gb, 2),
        'free_gb': round(free / (1024**3), 2),
        'gb_img': round(cat_sizes['image'] / (1024**3), 3),
        'gb_vid': round(cat_sizes['video'] / (1024**3), 3),
        'gb_aud': round(cat_sizes['audio'] / (1024**3), 3),
        'gb_doc': round(cat_sizes['document'] / (1024**3), 3),
        'gb_other': round(cat_sizes['other'] / (1024**3), 3),
        'pct_img': round((cat_sizes['image'] / total) * 100, 1),
        'pct_vid': round((cat_sizes['video'] / total) * 100, 1),
        'pct_aud': round((cat_sizes['audio'] / total) * 100, 1),
        'pct_doc': round((cat_sizes['document'] / total) * 100, 1),
        'pct_other': round((cat_sizes['other'] / total) * 100, 1),
    }

@app.route('/')
def index():
    files_data = []
    for fname in os.listdir(STORAGE_DIR):
        fpath = os.path.join(STORAGE_DIR, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            ext = fname.split('.')[-1].lower() if '.' in fname else ''
            files_data.append({
                'name': fname,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'category': categorize_ext(ext),
                'is_text': ext in TEXT_EXTS
            })

    files_data.sort(key=lambda x: x['date'], reverse=True)
    return render_template_string(HTML_TEMPLATE, storage=get_categorized_storage(), files=files_data)

@app.route('/upload', methods=['POST'])
def upload():
    uploaded_files = request.files.getlist('files')
    for file in uploaded_files:
        if file.filename != '':
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
    return jsonify({'status': 'success'})

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<filename>')
def delete_file(filename):
    fpath = os.path.join(STORAGE_DIR, filename)
    if os.path.exists(fpath): os.remove(fpath)
    return redirect(url_for('index'))

@app.route('/api/rename', methods=['POST'])
def rename_file():
    data = request.json
    old_path = os.path.join(STORAGE_DIR, data.get('old_name'))
    new_path = os.path.join(STORAGE_DIR, data.get('new_name'))
    if os.path.exists(old_path) and not os.path.exists(new_path):
        os.rename(old_path, new_path)
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Invalid rename operation'}), 400

@app.route('/api/save-text', methods=['POST'])
def save_text():
    data = request.json
    filepath = os.path.join(STORAGE_DIR, data.get('filename'))
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(data.get('content', ''))
    return jsonify({'status': 'ok'})

@app.route('/api/download-zip', methods=['POST'])
def download_zip():
    data = request.json
    filenames = data.get('filenames', [])
    memory_file = io.BytesIO()

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in filenames:
            fpath = os.path.join(STORAGE_DIR, fname)
            if os.path.exists(fpath):
                zf.write(fpath, fname)

    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='nas_files.zip')

@app.route('/api/edit-image', methods=['POST'])
def edit_image():
    data = request.json
    filepath = os.path.join(STORAGE_DIR, data.get('filename'))
    if not os.path.exists(filepath): return jsonify({'error': 'File not found'}), 404

    try:
        with Image.open(filepath) as img:
            if data.get('rotation'): img = img.rotate(-data['rotation'], expand=True)
            if 'brightness' in data: img = ImageEnhance.Brightness(img).enhance(data['brightness'])
            if 'contrast' in data: img = ImageEnhance.Contrast(img).enhance(data['contrast'])
            img.save(filepath)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trim-video', methods=['POST'])
def trim_video():
    import subprocess
    data = request.json
    input_path = os.path.join(STORAGE_DIR, data.get('filename'))
    name, ext = os.path.splitext(data.get('filename'))
    output_path = os.path.join(STORAGE_DIR, f"{name}_trimmed{ext}")
    duration = data.get('end', 10) - data.get('start', 0)

    cmd = ['ffmpeg', '-y', '-ss', str(data.get('start', 0)), '-i', input_path, '-t', str(duration), '-c', 'copy', output_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return jsonify({'status': 'ok'})
    except Exception:
        return jsonify({'error': 'FFmpeg execution failed'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
