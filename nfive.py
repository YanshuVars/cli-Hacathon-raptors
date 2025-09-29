import os, sys, argparse, subprocess, shutil, hashlib, concurrent.futures, tarfile, zipfile
from pathlib import Path
def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
def run_cmd(cmd, verbose=False):
    if verbose:
        print("🔧", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, capture_output=not verbose)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error: {e}")
def human_size(num):
    for unit in ["B","KB","MB","GB","TB"]:
        if num < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"
def transcode_file(src, dst, quality="medium", verbose=False, skip_hevc=True):
    ext = Path(src).suffix.lower()
    qmap = {"low": 32, "medium": 28, "high": 23}
    crf = qmap.get(quality, 28)
    if skip_hevc and ext in [".hevc", ".265", ".h265"]:
        print(f"⏩ Skipped HEVC file (already compressed): {Path(src).name}")
        return None
    if ext in [".mp4", ".mkv", ".avi", ".mov", ".hevc", ".265", ".h265", ".av1"]:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-c:v", "libx265", "-preset", "slow", "-crf", str(crf),
            "-c:a", "aac", "-b:a", "96k",
            str(dst)
        ]
        tag = f"🎞️ Video -> H.265: {Path(src).name}"
    elif ext in [".mp3", ".wav", ".aac", ".flac", ".m4a"]:
        cmd = ["ffmpeg", "-y", "-i", str(src),
               "-c:a", "libopus", "-b:a", "96k", str(dst)]
        tag = f"🎵 Audio -> Opus: {Path(src).name}"
    elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
        q = {"low": "70", "medium": "80", "high": "90"}[quality]
        cmd = ["ffmpeg", "-y", "-i", str(src),
               "-c:v", "libwebp", "-q:v", q, str(dst)]
        tag = f"🖼️ Image -> WebP: {Path(src).name}"

    else:
        return False

    run_cmd(cmd, verbose)
    print(f"✅ {tag}")
    return True

def organize_files(base_dir, mode="type", dry=False):
    for f in Path(base_dir).glob("**/*"):
        if f.is_file():
            if mode == "type":
                folder = f.suffix.lower()[1:] or "noext"
            elif mode == "size":
                folder = f"{os.path.getsize(f)//(1024*1024)}MB"
            elif mode == "date":
                folder = str(Path(f).stat().st_mtime_ns)
            else:
                folder = "organized"
            target = Path(base_dir) / folder
            if dry:
                print(f"📂 Would move {f.name} -> {folder}")
            else:
                target.mkdir(exist_ok=True)
                shutil.move(str(f), target / f.name)
                print(f"📂 Moved: {f.name} -> {folder}")

def dedupe_files(base_dir, dry=False):
    seen = {}
    for f in Path(base_dir).glob("**/*"):
        if f.is_file():
            h = file_hash(f)
            if h in seen:
                if dry:
                    print(f"🗑️ Would remove {f.name} (duplicate of {seen[h].name})")
                else:
                    print(f"🗑️ Removed duplicate: {f.name}")
                    f.unlink()
            else:
                seen[h] = f

def backup_file(src, backup_dir):
    backup_dir.mkdir(exist_ok=True)
    shutil.copy2(src, backup_dir / src.name)

def restore_backup(backup_dir, target_dir):
    for f in backup_dir.glob("*"):
        shutil.copy2(f, target_dir / f.name)
    print("✅ Undo complete: originals restored")

def compress_folder(folder, method="zip"):
    folder = Path(folder)
    archive_name = f"{folder}_compressed"

    if method == "zip":
        out = f"{archive_name}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in folder.glob("**/*"):
                if f.is_file():
                    zf.write(f, f.relative_to(folder))
        print(f"📦 Compressed into: {Path(out).name}")

    elif method == "tar":
        out = f"{archive_name}.tar.gz"
        with tarfile.open(out, "w:gz") as tf:
            for f in folder.glob("**/*"):
                if f.is_file():
                    tf.add(f, arcname=f.relative_to(folder))
        print(f"📦 Compressed into: {Path(out).name}")

def process_file(f, args, backup_dir, stats):
    ext = f.suffix.lower()
    new_file = None
    if args.transcode:
        if ext in [".mp4", ".mkv", ".avi", ".mov", ".hevc", ".265", ".h265", ".av1"]:
            new_file = f.with_stem(f.stem + "_new").with_suffix(".mp4")
        elif ext in [".mp3", ".wav", ".aac", ".flac", ".m4a"]:
            new_file = f.with_stem(f.stem + "_new").with_suffix(".opus")
        elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            new_file = f.with_stem(f.stem + "_new").with_suffix(".webp")

    if not new_file:
        return

    old_size = f.stat().st_size

    if args.backup_dir:
        backup_dir.mkdir(exist_ok=True)
        shutil.copy2(f, backup_dir / f.name)

    ok = transcode_file(f, new_file, args.quality, args.verbose, skip_hevc=not args.force_hevc)
    if not ok:
        return
    new_size = new_file.stat().st_size if new_file.exists() else old_size
    saved = old_size - new_size
    pct = (saved / old_size * 100) if old_size > 0 else 0
    if new_size >= old_size:
        print(f"⚖️ Skipped replacement (new file larger): {f.name} "
              f"({human_size(old_size)} vs {human_size(new_size)})")
        new_file.unlink(missing_ok=True)
        return
    print(f"📉 {f.name}: {human_size(old_size)} → {human_size(new_size)} "
          f"({pct:.1f}% smaller)")
    stats["old"] += old_size
    stats["new"] += new_size
    if args.replace:
        f.unlink(missing_ok=True)
        shutil.move(new_file, f.with_suffix(new_file.suffix))
        print(f"♻️ Replaced original: {f.name} -> {f.with_suffix(new_file.suffix).name}")
def main():
    p = argparse.ArgumentParser(description="Universal Media Optimizer CLI")
    p.add_argument("folder", help="Folder to process")
    p.add_argument("--transcode", action="store_true", help="Transcode/re-encode media")
    p.add_argument("--replace", action="store_true", help="Replace originals")
    p.add_argument("--backup-dir", type=str, help="Folder to save originals")
    p.add_argument("--undo", action="store_true", help="Restore from backup")
    p.add_argument("--dry-run", action="store_true", help="Show actions only")
    p.add_argument("--dedup", action="store_true", help="Remove duplicates")
    p.add_argument("--organize", choices=["type","size","date"], help="Organize files")
    p.add_argument("--quality", choices=["low","medium","high"], default="medium")
    p.add_argument("--threads", type=int, default=1, help="Parallel jobs")
    p.add_argument("--verbose", action="store_true", help="Verbose logging")
    p.add_argument("--force", action="store_true", help="Skip confirmations")
    p.add_argument("--compress", choices=["zip","tar"], help="Compress final output")
    p.add_argument("--force-hevc", action="store_true", help="Force re-encode HEVC/H.265")
    args = p.parse_args()
    folder = Path(args.folder)
    if not folder.exists():
        sys.exit("❌ Folder not found!")
    backup_dir = Path(args.backup_dir) if args.backup_dir else None
    if args.undo and backup_dir:
        restore_backup(backup_dir, folder)
        return
    files = [f for f in folder.glob("**/*") if f.is_file()]
    if args.dry_run:
        for f in files:
            print("🔍 Would process:", f.name)
        return
    if args.dedup:
        dedupe_files(folder, dry=False)
    if args.organize:
        organize_files(folder, args.organize, dry=False)
    stats = {"old": 0, "new": 0}
    if args.transcode:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as ex:
            futures = [ex.submit(process_file, f, args, backup_dir, stats) for f in files]
            concurrent.futures.wait(futures)
    if stats["old"] > 0:
        saved_total = stats["old"] - stats["new"]
        pct_total = saved_total / stats["old"] * 100
        print("\n📊 Summary:")
        print(f"   Original size: {human_size(stats['old'])}")
        print(f"   New size:      {human_size(stats['new'])}")
        print(f"   Space saved:   {human_size(saved_total)} ({pct_total:.1f}%)")
    if args.compress:
        compress_folder(folder, args.compress)
if __name__ == "__main__":
    main()


