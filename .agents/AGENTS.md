# HTML Parsing & Cleaning Heuristics

When writing or modifying logic that removes HTML elements based on CSS classes or IDs (e.g., stripping ads, banners, popups), **never use blind substring matching** (e.g., `if "ad" in class_string`).

This approach can inadvertently match and delete critical content (e.g., "ad" is a substring of "exitload", causing mutual fund exit load data to be dropped).

Instead, always use exact matches or explicitly handle delimiter-separated prefixes/suffixes:
- Split the class list properly (`class_string.split()`).
- Check for exact equality (`class_name == bad_word`).
- Check for explicitly delimited prefixes (`class_name.startswith(bad_word + "-")`).
