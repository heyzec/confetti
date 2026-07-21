import re

AC_RI_OPEN = re.compile(r"<(ac|ri):")
TAG_NAME = re.compile(r"<([a-zA-Z][a-zA-Z0-9:._-]*)")

ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*)")
SETEXT_EQ = re.compile(r"^=+\s*$")
SETEXT_DASH = re.compile(r"^-{2,}\s*$")
