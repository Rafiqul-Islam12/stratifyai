"""Single source for the app version string.

The version lives here rather than in two files so a release cannot end up
stamping one place and missing the other. Bump before the T18 tag.
"""

__version__ = "0.1.0"
