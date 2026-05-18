###
# Copyright (c) 2012-2013, spline
# Copyright © MMXXIV, Barry Suridge
# All rights reserved.
#
#
###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization

_ = PluginInternationalization("UrbanDictionary")


def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn

    conf.registerPlugin("UrbanDictionary", True)


UrbanDictionary = conf.registerPlugin("UrbanDictionary")

conf.registerChannelValue(
    UrbanDictionary,
    "maxNumberOfDefinitions",
    registry.Integer(
        10, """Number of definition and examples in output. Max 10."""
    ),
)

conf.registerChannelValue(
    UrbanDictionary,
    "disableANSI",
    registry.Boolean(
        False, """Do not display any ANSI formatting codes in output."""
    ),
)

conf.registerChannelValue(
    UrbanDictionary,
    "enabled",
    registry.Boolean(False, _("""Should plugin work in this channel?""")),
)

conf.registerGlobalValue(
    UrbanDictionary,
    "requestTimeout",
    registry.Integer(
        10, _("""HTTP timeout in seconds for UrbanDictionary API requests.""")
    ),
)

conf.registerGlobalValue(
    UrbanDictionary,
    "preferDefinePage",
    registry.Boolean(
        False,
        _(
            """Prefer scraping the define page first instead of using the API endpoint."""
        ),
    ),
)

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=250:
