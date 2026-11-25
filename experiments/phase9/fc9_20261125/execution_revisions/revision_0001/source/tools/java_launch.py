"""Launch prepared Minecraft JVMs without retaining Gradle processes."""

import json
import locale
import os
from pathlib import Path


def command_from_export(path: Path, argument_file: Path, *, expected_java: Path | None = None):
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema") != 1:
        raise ValueError("Unsupported Java launch export")
    executable = Path(config["executable"]).resolve(strict=True)
    if expected_java is not None and executable != expected_java.resolve(strict=True):
        raise ValueError("Launch export selected a different Java runtime")
    arguments = config["arguments"]
    if not isinstance(arguments, list) or not arguments or any(not isinstance(arg, str) or any(c in arg for c in "\x00\r\n") for arg in arguments):
        raise ValueError("Invalid Java launch arguments")
    # Java argument files recognize quoted backslashes/quotes; this is a file
    # parser, never shell interpolation. An argument per line avoids Windows'
    # process command-length limit for the dependency classpath.
    payload = "\n".join(json.dumps(arg, ensure_ascii=False) for arg in arguments) + "\n"
    # The Windows launcher decodes @files before the JVM's file.encoding setting
    # applies. Refuse unrepresentable characters instead of corrupting a path.
    encoding=locale.getencoding() if os.name=="nt" else "utf-8"
    try:
        payload.encode(encoding)
    except UnicodeEncodeError as error:
        raise ValueError("Java launch arguments are not representable in the native code page") from error
    with argument_file.open("x", encoding=encoding, newline="\n") as handle:
        handle.write(payload)
    return [str(executable), "@" + str(argument_file.resolve())]
