import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.java_launch import command_from_export

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/".runtime/jdk-25/bin/java.exe"
JAVAC=JAVA.with_name("javac.exe")


@unittest.skipUnless(JAVA.is_file() and JAVAC.is_file(),"Local JDK unavailable")
class JavaLaunchTests(unittest.TestCase):
    def test_actual_java_argument_file_preserves_paths_native_encoding_quotes_and_empty_arguments(self):
        with tempfile.TemporaryDirectory(prefix="flycraft launch ") as directory:
            folder=Path(directory)
            source=folder/"EchoArgs.java"
            source.write_text('''import java.util.Base64;
import java.nio.charset.StandardCharsets;
public class EchoArgs {
    public static void main(String[] args) {
        for(String arg:args) System.out.println(Base64.getEncoder().encodeToString(arg.getBytes(StandardCharsets.UTF_8)));
    }
}''')
            subprocess.run([str(JAVAC),str(source)],check=True,capture_output=True,timeout=30)
            for index,unicode_arg in enumerate(["ASCII", "Minecraft "+chr(0xe9)]):
                with self.subTest(argument=unicode_arg):
                    values=['C:\\path with spaces\\', 'quote" and #', '$(Get-Secret)`&', unicode_arg, '']
                    export=folder/(str(index)+".json")
                    export.write_text(json.dumps({"schema":1,"executable":str(JAVA),"arguments":["-cp",str(folder),"EchoArgs",*values]}))
                    command=command_from_export(export,folder/(str(index)+".args"),expected_java=JAVA)
                    result=subprocess.run(command,check=True,capture_output=True,text=True,timeout=30)
                    decoded=[base64.b64decode(line).decode("utf-8") for line in result.stdout.splitlines()]
                    self.assertEqual(decoded,values)


if __name__=="__main__":
    unittest.main()
