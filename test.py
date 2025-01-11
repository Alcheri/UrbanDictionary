###
# Copyright (c) 2012-2014, spline
# Copyright © MMXXIV, Barry Suridge
# All rights reserved.
#
#
###

from supybot.test import *
import supybot.conf as conf


class UrbanDictionaryTestCase(PluginTestCase):
    plugins = ("UrbanDictionary",)

    def testUrbanDictionary(self):
        conf.supybot.plugins.UrbanDictionary.disableANSI.setValue("True")
        self.assertRegexp("urbandictionary hello", "hello ::")
        self.assertRegexp("urbandictionary spline", "spline ::")


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
