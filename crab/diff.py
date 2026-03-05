import base64
import difflib


def unified_diff(a: str, b: str, fromfile: str = "a", tofile: str = "b") -> str:
    return "".join(
        difflib.unified_diff(
            (a + "\n").splitlines(keepends=True),
            (b + "\n").splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )


def unified_diff_b64(a: str, b: str, fromfile: str = "a", tofile: str = "b") -> bytes:
    return base64.b64encode(unified_diff(a, b, fromfile, tofile).encode())
