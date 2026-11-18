"""Build the two local HyperFrames projects from the same licensed W3C source."""

import hashlib
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
SOURCE_URL = "https://media.w3.org/2010/05/sintel/trailer.mp4"
SOURCE_SHA256 = "b670602fa00934ca27c4351bb0efe7ea7a07fae57284e44226025eeed7c51254"
FPS = 24
# [first included frame, first excluded frame), horizontal crop centre.
SHOTS = [(279, 334, 445), (334, 369, 353), (435, 507, 421)]


def build_project(name, height, picture_height, picture_top):
    project = ROOT / name
    project.mkdir(exist_ok=True)
    crop_width = 2 * round((364 * 720 / picture_height) / 2)
    filters = []
    for index, (start, stop, center) in enumerate(SHOTS):
        x = 2 * round((center - crop_width / 2) / 2)
        filters.append(
            f"[0:v]trim=start_frame={start}:end_frame={stop},setpts=PTS-STARTPTS,"
            f"crop={crop_width}:364:{x}:58,scale=720:{picture_height},setsar=1[v{index}]"
        )
    filters.append("[v0][v1][v2]concat=n=3:v=1:a=0[video]")
    # Preserve the source audio continuously across its first, in-scene camera cut.
    for index, (start, stop) in enumerate([(279, 369), (435, 507)]):
        length = (stop - start) / FPS
        filters.append(
            f"[0:a]atrim=start={start/FPS}:end={stop/FPS},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d=0.018,afade=t=out:st={length-0.018}:d=0.018[a{index}]"
        )
    filters.append("[a0][a1]concat=n=2:v=0:a=1[audio]")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(ROOT / "source.mp4"),
         "-filter_complex", ";".join(filters), "-map", "[video]", "-map", "[audio]",
         "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(project / "picture.mp4")],
        check=True,
    )
    portrait = name == "portrait"
    caption_bottom = 139 if portrait else 72
    title = '<div class="title">Sintel</div>' if portrait else ""
    shade = "" if portrait else '<div class="shade"></div>'
    content = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Sintel · dialogue excerpt</title>
<meta name="viewport" content="width=720,height={height}">
<style>
* {{ box-sizing: border-box; }}
html,body {{ margin:0; background:#17120f; }}
#film {{ width:720px; height:{height}px; position:relative; overflow:hidden;
        background:#17120f; color:#fff7ec; font-family:Arial,sans-serif; }}
video {{ position:absolute; left:0; top:{picture_top}px; width:720px; height:{picture_height}px; }}
.title {{ position:absolute; top:22px; left:42px; font:italic 50px Georgia,serif; color:#e4ccac; }}
.shade {{ position:absolute; bottom:0; width:100%; height:235px;
         background:linear-gradient(transparent,rgba(13,9,6,.92)); }}
.caption {{ position:absolute; left:42px; right:42px; bottom:{caption_bottom}px;
           font-size:{45 if portrait else 40}px; line-height:1.16; font-weight:700;
           text-align:center; text-shadow:0 2px 6px #100c09; }}
.credit {{ position:absolute; bottom:25px; left:0; width:100%; margin:0;
          font-size:20px; color:#eadccd; text-align:center; }}
</style></head><body>
<main id="film" data-no-timeline data-composition-id="sintel-{name}" data-width="720" data-height="{height}"
      data-start="0" data-duration="6.75" data-fps="24">
  <video class="clip" id="picture" src="picture.mp4" data-start="0" data-duration="6.75"
         data-track-index="0" muted playsinline></video>
  <audio id="dialogue" src="picture.mp4" data-start="0" data-duration="6.75" data-track-index="1"></audio>
  {title}{shade}
  <div class="clip caption" id="question" data-start="0.2083" data-duration="2.60" data-track-index="2">What brings you to the land<br>of the gatekeepers?</div>
  <div class="clip caption" id="answer" data-start="3.95" data-duration="1.87" data-track-index="2">I’m searching for someone.</div>
  <p class="credit">© copyright Blender Foundation | durian.blender.org</p>
</main></body></html>"""
    (project / "index.html").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    source = ROOT / "source.mp4"
    if not source.exists():
        with urlopen(SOURCE_URL, timeout=30) as response, source.open("wb") as target:
            shutil.copyfileobj(response, target)
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise SystemExit("The source differs from the trailer used to time this cut.")
    build_project("portrait", 1280, 870, 101)
    build_project("square", 720, 720, 0)
