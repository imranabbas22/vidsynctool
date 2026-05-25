"""
audio.py — Audio synthesis, normalization, and attachment utilities.

Standalone functions extracted from video_engine.py.
Provides programmatic SFX generation and loudness-normalized audio attachment.
"""

from __future__ import annotations

import math
import os
import random
import struct
import subprocess
import tempfile
import wave
from typing import Any, List, Tuple

try:
    from moviepy.editor import AudioFileClip
except ImportError:
    from moviepy import AudioFileClip


# ── SFX Synthesis ──────────────────────────────────────────────────────


def _ensure_sfx_exist(assets_dir: str) -> None:
    """Ensure SFX files exist under assets_dir/sfx/, synthesizing them programmatically if missing.

    Generates high-quality synthesized sound effects (tick, pop, zap, stamp,
    impact, riser, hum, crackle, heartbeat, ambiences) and converts them to
    MP3 via FFmpeg.  Skips any file that already exists.
    """
    sfx_dir = os.path.join(assets_dir, "sfx")
    os.makedirs(sfx_dir, exist_ok=True)

    try:
        import imageio_ffmpeg as _
        _  # silence pyflakes
    except ImportError:
        pass

    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, Exception):
        ffmpeg_exe = "ffmpeg"

    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]

    sample_rate = 44100

    def _synthesize_and_save(filename_base: str, samples: list[float]) -> None:
        """Write a WAV from *samples*, convert to MP3 via FFmpeg, clean up WAV."""
        wav_path = os.path.join(sfx_dir, f"{filename_base}.wav")
        mp3_path = os.path.join(sfx_dir, f"{filename_base}.mp3")

        if os.path.exists(mp3_path):
            return

        with wave.open(wav_path, "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            for s in samples:
                val = int(s * 32767)
                val = max(-32768, min(32767, val))
                f.writeframes(struct.pack("<h", val))

        cmd = [ffmpeg_exe, "-y", "-i", wav_path, "-acodec", "libmp3lame", "-aq", "4", mp3_path]
        try:
            subprocess.run(
                cmd,
                startupinfo=startupinfo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            if os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception as exc:
            print(
                f"[audio] FFmpeg conversion failed for {filename_base}, "
                f"using WAV data with .mp3 extension as failover: {exc}"
            )
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
            os.rename(wav_path, mp3_path)

    # ── 1. tick.mp3 : Mechanical ticking clock sound ──────────────
    tick_samples: list[float] = []
    for i in range(int(0.08 * sample_rate)):
        t = i / sample_rate
        s = (
            0.8 * math.sin(2 * math.pi * 1000 * t) * math.exp(-150 * t)
            + 0.2 * math.sin(2 * math.pi * 500 * t) * math.exp(-100 * t)
        )
        tick_samples.append(s)
    _synthesize_and_save("tick", tick_samples)

    # ── 2. pop.mp3 : Organic card reveal sound ────────────────────
    pop_samples: list[float] = []
    for i in range(int(0.25 * sample_rate)):
        t = i / sample_rate
        freq = 300 + 400 * (t / 0.25)
        s = math.sin(2 * math.pi * freq * t) * math.exp(-20 * t)
        pop_samples.append(s)
    _synthesize_and_save("pop", pop_samples)

    # Force regeneration of zap.mp3 if it contains the old sharp sound
    zap_mp3_path = os.path.join(sfx_dir, "zap.mp3")
    if os.path.exists(zap_mp3_path):
        try:
            os.remove(zap_mp3_path)
        except Exception:
            pass

    # ── 3. zap.mp3 : CRT Analog glitch sound ──────────────────────
    zap_samples: list[float] = []
    for i in range(int(0.40 * sample_rate)):
        t = i / sample_rate
        freq = 450 - 300 * (t / 0.40) + 50 * math.sin(2 * math.pi * 20 * t)
        noise = random.uniform(-1.0, 1.0)
        s = (0.3 * math.sin(2 * math.pi * freq * t) + 0.05 * noise) * math.exp(-10 * t)
        zap_samples.append(s)
    _synthesize_and_save("zap", zap_samples)

    # ── 4. stamp.mp3 : Forensic watermark stamp slam ──────────────
    stamp_samples: list[float] = []
    for i in range(int(0.50 * sample_rate)):
        t = i / sample_rate
        s = (
            0.6 * math.sin(2 * math.pi * 75 * t) * math.exp(-15 * t)
            + 0.4 * math.sin(2 * math.pi * 1000 * t) * math.exp(-45 * t)
        ) * math.exp(-6 * t)
        stamp_samples.append(s)
    _synthesize_and_save("stamp", stamp_samples)

    # ── 5. impact.mp3 : Deep cinematic impact boom ────────────────
    impact_samples: list[float] = []
    for i in range(int(2.0 * sample_rate)):
        t = i / sample_rate
        freq = 110 - 85 * (t / 2.0)
        noise = random.uniform(-1.0, 1.0)
        s = (math.sin(2 * math.pi * freq * t) + 0.15 * noise) * math.exp(-3.0 * t)
        impact_samples.append(s)
    _synthesize_and_save("impact", impact_samples)

    # ── 6. riser.mp3 : Low sub-bass riser sweep ───────────────────
    riser_samples: list[float] = []
    for i in range(int(10.0 * sample_rate)):
        t = i / sample_rate
        freq = 50 + 200 * (t / 10.0)
        amp = 0.05 + 0.95 * (t / 10.0)
        s = amp * math.sin(2 * math.pi * 200 * t)  # riser frequency sweep
        riser_samples.append(s)
    _synthesize_and_save("riser", riser_samples)

    # ── 7. hum.mp3 : Subtle low-frequency CRT hum (60s) ──────────
    hum_samples: list[float] = []
    for i in range(int(60.0 * sample_rate)):
        t = i / sample_rate
        s = (
            0.7 * math.sin(2 * math.pi * 60 * t)
            + 0.25 * math.sin(2 * math.pi * 120 * t)
            + 0.05 * random.uniform(-0.5, 0.5)
        )
        hum_samples.append(s)
    _synthesize_and_save("hum", hum_samples)

    # ── 8. crackle.mp3 : Procedural fire crackling (2s) ───────────
    crackle_samples: list[float] = []
    for i in range(int(2.0 * sample_rate)):
        t = i / sample_rate
        pop = 0.0
        if random.random() < 0.03:
            pop = random.uniform(0.3, 1.0) * math.exp(-200 * random.uniform(0.01, 0.03))
        rumble = (
            0.3 * math.sin(2 * math.pi * 60 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 4 * t))
        )
        crackle_samples.append(pop + rumble)
    _synthesize_and_save("crackle", crackle_samples)

    # ── 9. heartbeat.mp3 : Sub-bass heartbeat pulse ───────────────
    heartbeat_samples: list[float] = []
    cycle_len = int(0.857 * sample_rate)
    for i in range(int(2.0 * sample_rate)):
        t = i / sample_rate
        idx_in_cycle = i % cycle_len
        t_in_cycle = idx_in_cycle / sample_rate
        val = 0.0
        if 0.0 <= t_in_cycle < 0.15:
            val = 0.7 * math.sin(2 * math.pi * 50 * t_in_cycle) * math.exp(-20 * t_in_cycle)
        elif 0.15 <= t_in_cycle < 0.35:
            t_dub = t_in_cycle - 0.15
            val = 0.5 * math.sin(2 * math.pi * 55 * t_dub) * math.exp(-20 * t_dub)
        heartbeat_samples.append(val)
    _synthesize_and_save("heartbeat", heartbeat_samples)

    # ── 10. ambient_science.mp3 : Science lab hum & bubbling (60s) ─
    sci_samples: list[float] = []
    for i in range(int(60.0 * sample_rate)):
        t = i / sample_rate
        hum = 0.5 * math.sin(2 * math.pi * 100 * t)
        bubble = 0.0
        if random.random() < 0.0005:
            bubble = random.uniform(0.1, 0.4) * math.exp(-80 * random.uniform(0.01, 0.05))
        sci_samples.append(0.8 * hum + 0.2 * bubble)
    _synthesize_and_save("ambient_science", sci_samples)

    # ── 11. ambient_history.mp3 : Wind & distant echo (60s) ───────
    hist_samples: list[float] = []
    for i in range(int(60.0 * sample_rate)):
        t = i / sample_rate
        noise = random.uniform(-1.0, 1.0)
        wind_mod = 0.5 + 0.5 * math.sin(
            2 * math.pi * 0.15 * t + math.sin(2 * math.pi * 0.03 * t)
        )
        hist_samples.append(0.3 * noise * wind_mod)
    _synthesize_and_save("ambient_history", hist_samples)

    # ── 12. ambient_space.mp3 : Detuned deep space drone (60s) ────
    space_samples: list[float] = []
    for i in range(int(60.0 * sample_rate)):
        t = i / sample_rate
        drone = (
            0.5 * math.sin(2 * math.pi * 50 * t)
            + 0.3 * math.sin(2 * math.pi * 75 * t + 0.5)
            + 0.2 * math.sin(2 * math.pi * 110 * t)
        )
        space_samples.append(drone)
    _synthesize_and_save("ambient_space", space_samples)

    # ── 13. ambient_tech.mp3 : Server room ventilation fan & hum ──
    tech_samples: list[float] = []
    for i in range(int(60.0 * sample_rate)):
        t = i / sample_rate
        noise = random.uniform(-0.15, 0.15)
        hum = 0.6 * math.sin(2 * math.pi * 120 * t) + 0.4 * math.sin(2 * math.pi * 60 * t)
        tech_samples.append(0.7 * noise + 0.3 * hum)
    _synthesize_and_save("ambient_tech", tech_samples)


# ── Loudness Normalization & Audio Attachment ─────────────────────────


def _normalize_and_attach_audio(
    video_clip: Any,
    mixed_audio: Any,
    output_name: str,
    temp_dir: str | None = None,
) -> Tuple[Any, List[str]]:
    """Export *mixed_audio* to a temporary WAV, normalise loudness to -14 LUFS
    (with a peak ceiling of -1.0 dBFS) using pydub, and attach the result to
    *video_clip*.

    Parameters
    ----------
    video_clip :
        A MoviePy video clip (will receive the normalised audio).
    mixed_audio :
        A MoviePy audio clip or composite to normalise and attach.
    output_name :
        A unique identifier used for temporary file names.
    temp_dir :
        Directory for temporary files.  If ``None``, uses the system temp dir.

    Returns
    -------
    (video_clip, temp_files)
        The updated video clip and a list of temporary file paths that should
        be cleaned up by the caller.
    """
    if temp_dir is None:
        temp_dir = tempfile.gettempdir()

    temp_wav = os.path.join(temp_dir, f"temp_{output_name}_audio_raw.wav")
    norm_wav = os.path.join(temp_dir, f"temp_{output_name}_audio_norm.wav")
    tmp_files: List[str] = []

    try:
        from pydub import AudioSegment

        # Export raw mix
        mixed_audio.write_audiofile(temp_wav, fps=44100, nbytes=2, codec="pcm_s16le", logger=None)
        tmp_files.append(temp_wav)

        # Load and normalise
        sound = AudioSegment.from_file(temp_wav)
        change_in_dB = -14.0 - sound.dBFS
        normalized = sound.apply_gain(change_in_dB)
        if normalized.max_dBFS > -1.0:
            reduction = normalized.max_dBFS - (-1.0)
            normalized = normalized.apply_gain(-reduction)

        normalized.export(norm_wav, format="wav")
        tmp_files.append(norm_wav)

        # Load normalised audio back into MoviePy
        norm_audio_clip = AudioFileClip(norm_wav)
        video_clip = video_clip.with_audio(norm_audio_clip)
        print(
            f"[audio] Loudness normalised successfully to -14 dBFS target "
            f"(max peak: {normalized.max_dBFS:.2f} dBFS)"
        )
    except Exception as err:
        print(
            f"[audio] WARNING: pydub loudness normalisation failed ({err}). "
            f"Falling back to original mixed audio."
        )
        video_clip = video_clip.with_audio(mixed_audio)

    return video_clip, tmp_files
