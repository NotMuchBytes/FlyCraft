"""Verify and preserve original milestone footage; never regenerate AI actions."""

import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
FFMPEG=ROOT/".runtime/ffmpeg/bin/ffmpeg.exe"
FFPROBE=FFMPEG.with_name("ffprobe.exe")
MILESTONES=(1,10,25,50,100,250,500,1000,2500,5000,7500,10000)


def require_video_tools():
    if not FFMPEG.is_file() or not FFPROBE.is_file():
        raise RuntimeError("Milestone recording requires local FFmpeg and ffprobe")


def file_digest(path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        while chunk:=handle.read(1024**2): digest.update(chunk)
    return digest.hexdigest()


def compare_capture_frames(game_frame,obs_frame,*,threshold=.10):
    """Compare real Minecraft and OBS PNGs before allowing policy actions."""
    def pixels(path):
        decoded=subprocess.run([str(FFMPEG),"-nostdin","-v","error","-threads","2","-filter_threads","1",
            "-i",str(path),"-frames:v","1","-vf","scale=32:18:flags=area","-pix_fmt","rgb24","-f","rawvideo","-"],
            capture_output=True,timeout=15)
        if decoded.returncode or len(decoded.stdout)!=32*18*3:
            raise ValueError("Capture-proof image did not decode")
        return decoded.stdout
    actual,observed=pixels(game_frame),pixels(obs_frame)
    error=sum(abs(a-b) for a,b in zip(actual,observed))/(len(actual)*255)
    brightness=sum(actual)/(len(actual)*255)
    matched=error<=threshold and brightness>.05
    return {"matched":matched,"mean_absolute_rgb_error":error,"threshold":threshold,
        "game_frame":str(game_frame),"game_frame_sha256":file_digest(Path(game_frame)),
        "obs_frame":str(obs_frame),"obs_frame_sha256":file_digest(Path(obs_frame)),
        "method":"32x18 area-downsampled RGB comparison of independently captured real frames"}


def verify_mp4(path, *, minimum_seconds=0):
    require_video_tools()
    path=Path(path)
    if not path.is_file() or path.stat().st_size<1024:
        raise ValueError("Recording is missing or empty")
    probe=subprocess.run([str(FFPROBE),"-v","error","-show_entries",
        "format=duration,format_name:stream=index,codec_type,codec_name,width,height,avg_frame_rate,nb_frames",
        "-of","json",str(path)],capture_output=True,text=True,timeout=15)
    if probe.returncode: raise ValueError("Container probe failed: "+probe.stderr[-2000:])
    data=json.loads(probe.stdout)
    streams=[stream for stream in data.get("streams",[]) if stream.get("codec_type")=="video"]
    duration=float(data.get("format",{}).get("duration",0))
    if not streams or not math.isfinite(duration) or duration<max(.1,minimum_seconds):
        raise ValueError("Recording has no valid video stream or is too short")
    if "mp4" not in data.get("format",{}).get("format_name","").split(","):
        raise ValueError("Recording is not an MP4 container")
    decoded=subprocess.run([str(FFMPEG),"-nostdin","-v","error","-xerror","-threads","2",
        "-progress","pipe:1","-nostats","-i",str(path),"-map","0:v:0","-an","-f","null","-"],
        capture_output=True,text=True,timeout=60)
    frames=[int(line.split("=",1)[1]) for line in decoded.stdout.splitlines() if line.startswith("frame=")]
    if decoded.returncode or not frames or frames[-1]<1 or "progress=end" not in decoded.stdout:
        raise ValueError("Full video decode failed: "+decoded.stderr[-2000:])
    return {"playable_verified":True,"full_decode_verified":True,"decoded_frames":frames[-1],
        "duration_seconds":duration,"video_stream":streams[0],"bytes":path.stat().st_size,"sha256":file_digest(path)}


def preserve_milestone(source, destination, *, minimum_seconds=0):
    """Retry finalized-file reads, then remux original packets if necessary.

    No frame synthesis, trimming, action playback or policy execution occurs.
    A missing/corrupt source remains an explicit failed milestone.
    """
    source,destination=Path(source),Path(destination)
    if destination.exists(): raise FileExistsError("Milestone video must be new")
    destination.parent.mkdir(parents=True,exist_ok=True)
    attempts=[]
    for attempt in range(3):
        try:
            report=verify_mp4(source,minimum_seconds=minimum_seconds)
            shutil.copy2(source,destination)
            if file_digest(destination)!=report["sha256"]: raise OSError("Video copy checksum mismatch")
            return report | {"source":str(source),"path":str(destination),"recovery":"none",
                             "verification_attempts":attempts+["verified_original"]}
        except (ValueError,OSError,subprocess.SubprocessError) as error:
            attempts.append(str(error)); time.sleep(.5)
    # Preserve the source and copy encoded packets without altering frames.
    remux=subprocess.run([str(FFMPEG),"-nostdin","-n","-v","error","-i",str(source),
        "-map","0","-c","copy","-movflags","+faststart",str(destination)],
        capture_output=True,text=True,timeout=60)
    if remux.returncode:
        raise ValueError("MP4 unavailable after verification retries and stream-copy remux: "+remux.stderr[-2000:])
    report=verify_mp4(destination,minimum_seconds=minimum_seconds)
    return report | {"source":str(source),"source_sha256":file_digest(source),"path":str(destination),
                     "recovery":"stream_copy_remux","verification_attempts":attempts+["verified_remux"]}


def preview_frame(video, destination):
    metadata=verify_mp4(video)
    result=subprocess.run([str(FFMPEG),"-nostdin","-n","-v","error","-threads","2","-filter_threads","1",
        "-ss",str(metadata["duration_seconds"]*.5),"-i",str(video),"-frames:v","1","-vf","scale=960:-1",
        "-update","1",str(destination)],capture_output=True,text=True,timeout=20)
    if result.returncode: raise ValueError(result.stderr[-2000:])
    return metadata
