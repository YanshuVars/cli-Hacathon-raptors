# ⚡ FILESQUASH CLI

A powerful **command-line tool** to manage, optimize, and organize your media library.  
Easily compress videos, audios, and images with **FFmpeg**, remove duplicates, organize files, generate reports, and extract metadata — all from a single CLI.  

# cli-Hacathon-raptors
For Hackathon Raptors
## 🚀 CLI Commands

### 🎯 Core Processing
- `--transcode` → Re-encode media  
   - Video → H.265 (`libx265`)  
   - Audio → Opus (`.opus`)  
   - Images → WebP (`.webp`)  
- `--replace` → Replace originals with optimized versions  
- `--quality {low|medium|high}` → Set compression quality  
- `--thread N` → Process files in parallel with N threads  

---

### 🗂 File Management
- `--dedup` → Detect and remove duplicate files (SHA256 hash)  
- `--organize {type|size|date}` → Organize files into subfolders  
- `--compress {zip|tar}` → Compress the final folder into ZIP or TAR  

---

### 🔄 Backup & Restore
- `--backup-dir <path>` → Save original files in backup folder  
- `--undo` → Restore files from backup  

---

### 📊 Insights & Debugging
- `--verbose` → Show detailed logs and executed commands  
- `--report` → Generate summary of folder (total files, size, types, largest/smallest)  
- `--analyze` → Inspect technical details (codec, resolution, duration, bitrate)  
- `--metadata` → Extract and display **EXIF / media metadata**  

FFMPEG DOWLOAD LINK:-
                 https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
