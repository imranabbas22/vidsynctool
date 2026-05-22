import subprocess
import imageio_ffmpeg

def check_cuda():
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        print(f"Error getting FFmpeg executable: {e}")
        ffmpeg_exe = "ffmpeg"
    
    print(f"FFmpeg path: {ffmpeg_exe}")
    
    # Run ffmpeg -encoders and search for h264_nvenc
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    except AttributeError:
        startupinfo = None
        
    try:
        res = subprocess.run(
            [ffmpeg_exe, "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo,
            check=True
        )
        encoders = res.stdout
        has_nvenc = "h264_nvenc" in encoders
        print(f"h264_nvenc present in encoders: {has_nvenc}")
        if has_nvenc:
            print("CUDA/NVENC is supported by FFmpeg!")
        else:
            print("h264_nvenc was NOT found in the encoders list.")
            
        # Also run a quick test encoding 1 frame to see if it actually initializes
        # (sometimes the encoder is listed but fails to initialize if drivers are missing)
        if has_nvenc:
            print("Testing dummy NVENC encoding...")
            test_cmd = [
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "color=c=black:s=128x128:d=0.1",
                "-c:v", "h264_nvenc",
                "-f", "null", "-"
            ]
            test_res = subprocess.run(
                test_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            if test_res.returncode == 0:
                print("Dummy NVENC encoding test PASSED!")
            else:
                print("Dummy NVENC encoding test FAILED:")
                print(test_res.stderr)
    except Exception as e:
        print(f"Failed to check encoders or test encode: {e}")

if __name__ == "__main__":
    check_cuda()
