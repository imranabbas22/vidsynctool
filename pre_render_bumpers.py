# =============================================================================
# "The Daily Audit" - Pre-render Universal Bumper Scenes
# =============================================================================
import os
import sys
import shutil
from dotenv import load_dotenv

# Load env vars from app_build/.env
load_dotenv(os.path.join("app_build", ".env"))

# Add app_build to system path
sys.path.append(os.path.abspath("app_build"))

from video_engine import VideoEngine, STYLE_PRESETS
from asset_generator import AssetGenerator

try:
    from moviepy.editor import AudioFileClip, VideoFileClip
except ImportError:
    from moviepy import AudioFileClip, VideoFileClip

def find_bg_file(substring):
    blueprint_dir = os.path.join("app_build", "assets", "video_blueprints")
    for f in os.listdir(blueprint_dir):
        if substring.lower() in f.lower():
            return os.path.join(blueprint_dir, f)
    raise ValueError(f"Could not find blueprint video matching '{substring}'")

def main():
    print("=" * 80)
    print("   PRE-RENDERING UNIVERSAL STARTING AND ENDING BUMPERS")
    print("=" * 80)

    # Initialize AssetGenerator to generate the high-quality TTS audio
    asset_gen = AssetGenerator()
    engine = VideoEngine()

    # Create temporary directory for TTS audio
    temp_dir = os.path.join("app_build", "assets", "temp_bumpers_tts")
    os.makedirs(temp_dir, exist_ok=True)
    asset_gen.assets_dir = temp_dir

    # Output paths
    starting_out_dir = os.path.join("assets", "video_blueprints", "starting")
    ending_out_dir = os.path.join("assets", "video_blueprints", "ending")
    os.makedirs(starting_out_dir, exist_ok=True)
    os.makedirs(ending_out_dir, exist_ok=True)

    # Definitions of bumpers to generate
    # (output_filename, text, video_type, bg_substring, folder)
    bumpers = [
        # --- Myth Starting Bumpers ---
        ("MYTH_01.mp4", "Now, with another myth you did not know.", "myth", "question_mark_chalk", starting_out_dir),
        ("MYTH_02.mp4", "Now, with another myth you did not know.", "myth", "Antique_hourglass", starting_out_dir),
        ("MYTH_03.mp4", "Now, with another myth you did not know.", "myth", "Brass_pendulum", starting_out_dir),

        # --- Bizarre Starting Bumpers ---
        ("BIZARRE_01.mp4", "Now, with another bizarre truth you did not know.", "bizarre", "Ancient_book_falling", starting_out_dir),
        ("BIZARRE_02.mp4", "Now, with another bizarre truth you did not know.", "bizarre", "Ancient_parchment_unrolling", starting_out_dir),
        ("BIZARRE_03.mp4", "Now, with another bizarre truth you did not know.", "bizarre", "Crystals_growing", starting_out_dir),

        # --- Universal Ending Bumpers ---
        ("CLASS_DISMISSED_01.mp4", "Like, share, and subscribe for more similar myth and bizarre content. CLASS DISMISSED.", "ending", "Chalk_writing_CLASS_DISMISSED", ending_out_dir),
        ("CLASS_DISMISSED_02.mp4", "Like, share, and subscribe for more similar myth and bizarre content. CLASS DISMISSED.", "ending", "Empty_chair_in_spotlight", ending_out_dir),
    ]

    for filename, text, b_type, bg_sub, out_dir in bumpers:
        print(f"\nProcessing {filename}...")
        
        # 1. Generate TTS
        ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{text}</prosody>"
        tts_name = f"temp_{filename[:-4]}"
        tts_path = asset_gen.generate_tts_audio(ssml_wrapped, tts_name, is_ssml=True)
        print(f"Generated TTS audio: {tts_path}")

        # 2. Get Background Video
        bg_path = find_bg_file(bg_sub)
        print(f"Using background blueprint: {bg_path}")

        # 3. Setup audio clip duration
        audio_clip = AudioFileClip(tts_path)
        duration = audio_clip.duration
        print(f"Audio duration: {duration:.2f}s")

        # 4. Monkey-patch VideoEngine background selectors to return our specific background
        if b_type in ["myth", "bizarre"]:
            engine._select_starting_blueprint = lambda v_type, path=bg_path: path
            # Create bumper clip
            bumper_clip = engine._create_starting_bumper(
                audio_duration=duration,
                video_type=b_type,
                style_dict=STYLE_PRESETS["blueprint"]
            )
        else:
            engine._select_ending_blueprint = lambda path=bg_path: path
            # Create ending clip
            bumper_clip = engine._create_ending_scene(
                audio_duration=duration,
                style_dict=STYLE_PRESETS["blueprint"]
            )

        # Attach audio to the bumper clip
        final_clip = bumper_clip.with_audio(audio_clip)

        # 5. Render & Write the video file
        out_filepath = os.path.join(out_dir, filename)
        print(f"Rendering to final path: {out_filepath}")
        
        # Use nvenc if CUDA detected by VideoEngine
        codec = "h264_nvenc" if engine.has_cuda else "libx264"
        print(f"Using video codec: {codec}")

        final_clip.write_videofile(
            out_filepath,
            codec=codec,
            audio_codec="aac",
            fps=25,
            threads=os.cpu_count() or 4,
            preset="fast"
        )

        # Close resource clips
        final_clip.close()
        audio_clip.close()

    # Clean up temporary TTS files
    try:
        shutil.rmtree(temp_dir)
        print("\nCleaned up temporary TTS directory.")
    except Exception as e:
        print(f"\nWarning: Failed to clean up temporary TTS directory: {e}")

    print("\n" + "=" * 80)
    print("   ALL UNIVERSAL BUMPERS PRE-RENDERED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()
