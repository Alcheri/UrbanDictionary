###
# Copyright (c) 2012-2013, spline
# Copyright © MMXXIV, Barry Suridge
# All rights reserved.
#
#
###

"""
Limnoria plugin for UrbanDictionary to display definitions on https://www.urbandictionary.com/
"""

import sys

if sys.version_info < (3, 10):
    raise RuntimeError(
        "This plugin requires Python 3.10 or newer. Please upgrade your Python installation."
    )

import supybot
import supybot.world as world

# Use this for the version of this plugin.  You may wish to put a CVS keyword
# in here if you're keeping the plugin in CVS or some similar system.
__version__ = "1.0.0"

__author__ = supybot.Author("reticulatingspline", "spline", "")
__maintainer__ = getattr(
    supybot.authors,
    "Alcheri",
    supybot.Author("Barry Suridge", "Alcheri", "barry.suridge@gmail.com"),
)

# This is a dictionary mapping supybot.Author instances to lists of
# contributions.
__contributors__ = {
    supybot.Author("Barry Suridge", "Alcheri", "barry.suridge@gmail.com"): [
        "Maintenance"
    ],
}

# This is a url where the most recent plugin package can be downloaded.
__url__ = "https://github.com/Alcheri/UrbanDictionary"

from . import config
from . import plugin
from importlib import reload

# In case we're being reloaded.
reload(config)
reload(plugin)
# Add more reloads here if you add third-party modules and want them to be
# reloaded when this plugin is reloaded.  Don't forget to import them as well!

if world.testing:
    from . import test

Class = plugin.Class
configure = config.configure

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
