test:
    python3 -m confetti to-md td.xml -o td.md
    python3 -m confetti to-xhtml td.md -o td.rt.xml
    diff td.xml td.rt.xml

unit:
    python3 -m unittest discover -s . -p "test_*.py" -v
