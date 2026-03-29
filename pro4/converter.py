from opencc import OpenCC

cc = OpenCC('t2s')


def convert_to_simplified(text: str) -> str:
    """Convert Traditional Chinese to Simplified Chinese."""
    return cc.convert(text)
