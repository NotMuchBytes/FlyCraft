import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.milestone_video import FFMPEG,FFPROBE,preserve_milestone,verify_mp4,compare_capture_frames


@unittest.skipUnless(FFMPEG.is_file() and FFPROBE.is_file(),"Optional local video tools unavailable")
class MilestoneVideoTests(unittest.TestCase):
    def make_test_pattern(self,path):
        # Synthetic codec fixture only. This is never Minecraft footage and
        # lives solely in a temporary test directory.
        subprocess.run([str(FFMPEG),"-nostdin","-n","-v","error","-threads","2","-filter_threads","1",
            "-f","lavfi","-i","testsrc2=s=64x64:r=10","-t","1","-c:v","libx264",str(path)],
            check=True,capture_output=True,timeout=20)

    def decoded_hashes(self,path):
        result=subprocess.run([str(FFMPEG),"-nostdin","-v","error","-threads","2","-i",str(path),
            "-map","0:v:0","-f","framemd5","-"],check=True,capture_output=True,text=True,timeout=20)
        return [line.rsplit(",",1)[-1].strip() for line in result.stdout.splitlines() if line and not line.startswith("#")]

    def test_mp4_is_fully_decoded_and_original_copy_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); source=folder/"synthetic_codec_test.mp4"
            self.make_test_pattern(source)
            result=preserve_milestone(source,folder/"preserved_test.mp4",minimum_seconds=.9)
            self.assertTrue(result["full_decode_verified"])
            self.assertEqual(result["decoded_frames"],10)
            self.assertEqual(source.read_bytes(),(folder/"preserved_test.mp4").read_bytes())

    def test_stream_copy_remux_preserves_every_decoded_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); source=folder/"synthetic_codec_test.mkv"
            self.make_test_pattern(source)
            before=hashlib.sha256(source.read_bytes()).hexdigest()
            result=preserve_milestone(source,folder/"remuxed_test.mp4",minimum_seconds=.9)
            self.assertEqual(result["recovery"],"stream_copy_remux")
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
            self.assertEqual(self.decoded_hashes(source),self.decoded_hashes(folder/"remuxed_test.mp4"))

    def test_invalid_recording_never_passes_as_playable(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"corrupt_test.mp4"
            source.write_bytes(b"invalid codec test"*100)
            with self.assertRaises(ValueError): verify_mp4(source)

    def test_content_preflight_rejects_a_different_picture(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); clip=folder/"synthetic_codec_test.mp4"
            self.make_test_pattern(clip)
            actual=folder/"actual_test.png"; other=folder/"wrong_test.png"
            subprocess.run([str(FFMPEG),"-nostdin","-n","-v","error","-threads","2","-i",str(clip),
                "-frames:v","1",str(actual)],check=True,capture_output=True,timeout=20)
            subprocess.run([str(FFMPEG),"-nostdin","-n","-v","error","-f","lavfi","-i","color=black:s=64x64",
                "-frames:v","1",str(other)],check=True,capture_output=True,timeout=20)
            self.assertTrue(compare_capture_frames(actual,actual)["matched"])
            self.assertFalse(compare_capture_frames(actual,other)["matched"])


if __name__=="__main__":
    unittest.main()
