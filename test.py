###
# Copyright (c) 2012-2014, spline
# Copyright © MMXXIV, Barry Suridge
# All rights reserved.
#
#
###

import supybot.conf as conf
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from supybot.test import ChannelPluginTestCase as SupybotChannelPluginTestCase
from supybot.test import PluginTestCase as SupybotPluginTestCase

from UrbanDictionary import plugin

SupybotChannelPluginTestCase.__test__ = False
SupybotPluginTestCase.__test__ = False

MOCK_JSON_WITH_DEFINITION = (
    '{"list": [{"definition": "A greeting", "example": "hello there", '
    '"thumbs_up": 5, "thumbs_down": 1}], "tags": ["greeting"]}'
)

MOCK_JSON_EMPTY_LIST = '{"list": []}'


class UrbanDictionaryTestCase(SupybotPluginTestCase):
    __test__ = False
    plugins = ("UrbanDictionary",)

    def setUp(self):
        super().setUp()
        conf.supybot.plugins.UrbanDictionary.preferDefinePage.setValue(False)
        conf.supybot.plugins.UrbanDictionary.disableANSI.setValue(False)
        conf.supybot.plugins.UrbanDictionary.cooldownSeconds.setValue(0)

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    def testUrbanDictionary(self, mock_fetch_url):
        mock_fetch_url.return_value = MOCK_JSON_WITH_DEFINITION
        conf.supybot.plugins.UrbanDictionary.disableANSI.setValue("True")
        self.assertRegexp("urbandictionary hello", ":: A greeting")
        self.assertRegexp("urbandictionary spline", ":: A greeting")

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    def testUrbanDictionaryEncodesQueryAndTimeout(self, mock_fetch_url):
        mock_fetch_url.return_value = MOCK_JSON_WITH_DEFINITION
        conf.supybot.plugins.UrbanDictionary.requestTimeout.setValue(7)
        self.assertRegexp('urbandictionary "hello world"', ":: A greeting")

        called_url, called_timeout = mock_fetch_url.call_args.args
        self.assertIn("term=hello+world", called_url)
        self.assertEqual(called_timeout, 7)

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    def testUrbanDictionaryNoDefinition(self, mock_fetch_url):
        mock_fetch_url.return_value = MOCK_JSON_EMPTY_LIST
        self.assertError("urbandictionary unknownterm")

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    @patch("UrbanDictionary.plugin.UrbanDictionary._fetch_url_fallback")
    def testUrbanDictionaryUsesFallback(self, mock_fallback, mock_fetch_url):
        mock_fetch_url.return_value = None
        mock_fallback.return_value = MOCK_JSON_WITH_DEFINITION
        self.assertRegexp("urbandictionary hello", ":: A greeting")
        mock_fallback.assert_called_once()

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    @patch("UrbanDictionary.plugin.UrbanDictionary._fetch_url_fallback")
    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_define_page_fallback"
    )
    def testUrbanDictionaryUsesDefinePageFallback(
        self, mock_define_fallback, mock_json_fallback, mock_fetch_url
    ):
        mock_fetch_url.return_value = None
        mock_json_fallback.return_value = None
        mock_define_fallback.return_value = {
            "list": [
                {
                    "definition": "Fallback definition text",
                    "example": "",
                    "thumbs_up": 0,
                    "thumbs_down": 0,
                }
            ],
            "tags": [],
        }

        self.assertRegexp("urbandictionary bogan", "Fallback definition text")
        mock_define_fallback.assert_called_once()

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    @patch("UrbanDictionary.plugin.UrbanDictionary._fetch_url_fallback")
    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_define_page_fallback"
    )
    def testUrbanDictionaryPreferDefinePage(
        self, mock_define_fallback, mock_json_fallback, mock_fetch_url
    ):
        conf.supybot.plugins.UrbanDictionary.preferDefinePage.setValue(True)
        mock_define_fallback.return_value = {
            "list": [
                {
                    "definition": "Define page first",
                    "example": "",
                    "thumbs_up": 0,
                    "thumbs_down": 0,
                }
            ],
            "tags": [],
        }

        self.assertRegexp("urbandictionary bogan", "Define page first")
        mock_define_fallback.assert_called_once()
        mock_fetch_url.assert_not_called()
        mock_json_fallback.assert_not_called()

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    def testUrbanDictionaryRejectsLongTermBeforeFetch(self, mock_fetch_url):
        self.assertError(f"urbandictionary {'a' * 121}")
        mock_fetch_url.assert_not_called()


class UrbanDictionaryChannelTestCase(SupybotChannelPluginTestCase):
    __test__ = False
    plugins = ("UrbanDictionary",)

    def setUp(self):
        super().setUp()
        conf.supybot.plugins.UrbanDictionary.preferDefinePage.setValue(False)
        conf.supybot.plugins.UrbanDictionary.disableANSI.setValue(False)
        conf.supybot.plugins.UrbanDictionary.cooldownSeconds.setValue(0)

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    def testUrbanDictionaryChannelDisabledByDefault(self, mock_fetch_url):
        mock_fetch_url.return_value = MOCK_JSON_WITH_DEFINITION
        conf.supybot.plugins.UrbanDictionary.enabled.setValue(False)

        self.assertNoResponse("urbandictionary hello")
        mock_fetch_url.assert_not_called()

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    def testUrbanDictionaryPrivateMessageRemainsPublic(self, mock_fetch_url):
        mock_fetch_url.return_value = MOCK_JSON_WITH_DEFINITION
        conf.supybot.plugins.UrbanDictionary.enabled.setValue(False)

        self.assertRegexp(
            "urbandictionary hello", ":: A greeting", private=True
        )

    @patch(
        "UrbanDictionary.plugin.UrbanDictionary._fetch_url",
        new_callable=AsyncMock,
    )
    def testUrbanDictionaryCooldown(self, mock_fetch_url):
        mock_fetch_url.return_value = MOCK_JSON_WITH_DEFINITION
        conf.supybot.plugins.UrbanDictionary.enabled.setValue(True)
        conf.supybot.plugins.UrbanDictionary.cooldownSeconds.setValue(5)

        self.assertRegexp("urbandictionary hello", ":: A greeting")
        self.assertError("urbandictionary hello")
        self.assertEqual(mock_fetch_url.call_count, 1)


class UrbanDictionarySecurityTestCase(unittest.TestCase):
    def setUp(self):
        self.plugin = plugin.UrbanDictionary.__new__(plugin.UrbanDictionary)
        self.plugin.registryValue = MagicMock(return_value=262144)

    def test_clean_text_strips_unsafe_controls_and_preserves_irc_formatting(
        self,
    ):
        result = self.plugin._clean_text("\x0304red\x03\x00 text")

        self.assertIn("\x03", result)
        self.assertNotIn("\x00", result)

    @patch("UrbanDictionary.plugin.urllib.request.urlopen")
    def test_fetch_url_fallback_rejects_large_response(self, mock_urlopen):
        response = MagicMock()
        response.headers = {"Content-Length": str(262145)}
        mock_urlopen.return_value.__enter__.return_value = response

        result = self.plugin._fetch_url_fallback(
            "https://api.urbandictionary.com/v0/define?term=test",
            1,
        )

        self.assertIsNone(result)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
