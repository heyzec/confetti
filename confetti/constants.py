import re

RAW_OPEN = "\x02"
RAW_CLOSE = "\x03"
SENTINEL_RE = re.compile(
    re.escape(RAW_OPEN) + r"(.*?)" + re.escape(RAW_CLOSE), re.DOTALL
)


# == Confluence ==
AC_NS = "http://atlassian.com/ac"
RI_NS = "http://atlassian.com/ri"
MACRO_NS = {AC_NS, RI_NS}
