"""Audio quality / integrity checks. Catches the two big lies you get on
Soulseek: corrupted/truncated files, and lossy-source transcodes wearing a
.flac extension.

  - integrity: `flac --test` for FLAC files (decoder verifies sample data)
  - spectral cutoff: FFT the first ~30s, find the highest frequency that
    still carries real energy. Real lossless goes to ~22 kHz; MP3 sources
    typically cut off at 16-20 kHz."""

import logging
import os
import shutil
import subprocess

import numpy as np

log = logging.getLogger("refinery.quality")

# Frequency-cutoff classification thresholds.
# Most lossy encoders apply a lowpass below the Nyquist limit:
#  - MP3 v0/320: usually 19-20 kHz
#  - MP3 v2:     ~17 kHz
#  - AAC 256:    ~19-20 kHz
# Genuine lossless from CD = 22.05 kHz Nyquist; hi-res higher.
CUTOFF_VERIFIED_HZ  = 20500   # >= this -> looks lossless
CUTOFF_SUSPECT_HZ   = 17000   # < this  -> very likely transcoded


def _have(cmd):
    return shutil.which(cmd) is not None


def flac_test(path):
    """Run `flac -t`. Returns (ok, error_message)."""
    if not _have("flac"):
        return (True, "flac CLI not installed - skipping integrity check")
    try:
        r = subprocess.run(
            ["flac", "-t", "-s", path],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            return (True, None)
        return (False, (r.stderr or r.stdout).strip()[:300])
    except subprocess.TimeoutExpired:
        return (False, "flac --test timeout")
    except Exception as e:
        return (False, str(e)[:300])


def _decode_pcm(path, seconds=30, sample_rate=44100):
    """Decode the first `seconds` of `path` to mono s16le PCM via ffmpeg."""
    if not _have("ffmpeg"):
        return None
    try:
        r = subprocess.run([
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-t", str(seconds), "-i", path,
            "-ac", "1", "-ar", str(sample_rate),
            "-f", "s16le", "-",
        ], capture_output=True, timeout=60)
        if r.returncode != 0:
            return None
        return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception as e:
        log.warning("ffmpeg decode failed %s: %s", path, e)
        return None


def freq_cutoff(path, sample_rate=44100):
    """Estimate the highest frequency carrying real energy. Returns Hz or 0
    if analysis failed."""
    samples = _decode_pcm(path, seconds=30, sample_rate=sample_rate)
    if samples is None or len(samples) < sample_rate:
        return 0
    # Window slightly to reduce spectral leakage.
    window = np.hanning(len(samples))
    fft  = np.abs(np.fft.rfft(samples * window))
    freqs = np.fft.rfftfreq(len(samples), d=1.0 / sample_rate)
    if not fft.size:
        return 0
    # Pick threshold relative to overall peak: -60 dB.
    peak = float(fft.max())
    if peak <= 0:
        return 0
    threshold = peak * 10 ** (-60 / 20)
    sig = freqs[fft > threshold]
    return int(sig.max()) if sig.size else 0


def classify_cutoff(hz):
    if hz <= 0:
        return "unknown"
    if hz >= CUTOFF_VERIFIED_HZ:
        return "verified"
    if hz < CUTOFF_SUSPECT_HZ:
        return "suspect"
    return "borderline"


def generate_spectrogram(audio_path, output_path,
                         width=1500, height=800):
    """Render a frequency-vs-time spectrogram PNG via sox. This is the same
    type of image people post on Soulseek to prove a file is real lossless.
    Returns True on success.

    Trims to the first 5 minutes so high-res FLAC (24/96, long tracks) doesn't
    blow past the subprocess timeout - the cutoff pattern is stable across a
    track, so a 5-minute window shows the same thing as the whole file."""
    if not _have("sox"):
        return False
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        r = subprocess.run([
            "sox", audio_path, "-n",
            "trim", "0", "300",
            "spectrogram",
            "-o", output_path,
            "-x", str(width),
            "-y", str(height),
            "-c", os.path.basename(audio_path)[:60],
        ], capture_output=True, timeout=300)
        if r.returncode != 0:
            log.warning("sox spectrogram failed %s: %s",
                        audio_path, (r.stderr or b"")[-400:])
            return False
        return os.path.exists(output_path)
    except Exception as e:
        log.warning("spectrogram failed %s: %s", audio_path, e)
        return False


def analyze(path):
    """Run both checks. Returns dict with verified bool, cutoff Hz, verdict,
    and an error string if integrity failed."""
    ext = os.path.splitext(path)[1].lower()
    error = None

    if ext == ".flac":
        ok, err = flac_test(path)
    else:
        ok, err = True, None
    if not ok:
        error = err

    cutoff = freq_cutoff(path)
    return {
        "verified": ok,
        "freq_cutoff_hz": cutoff,
        "verdict": classify_cutoff(cutoff),
        "error": error,
    }
