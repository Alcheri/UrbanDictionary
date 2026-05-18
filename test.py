###
# Copyright (c) 2012-2014, spline
# Copyright © MMXXIV, Barry Suridge
# All rights reserved.
#
#
###

from supybot.test import *
import supybot.conf as conf
from unittest.mock import AsyncMock, patch

MOCK_JSON_WITH_DEFINITION = (
    '{"list": [{"definition": "A greeting", "example": "hello there", '
    '"thumbs_up": 5, "thumbs_down": 1}], "tags": ["greeting"]}'
)

MOCK_JSON_EMPTY_LIST = '{"list": []}'


class UrbanDictionaryTestCase(PluginTestCase):
    plugins = ("UrbanDictionary",)

    def setUp(self):
        super().setUp()
        conf.supybot.plugins.UrbanDictionary.preferDefinePage.setValue(False)

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


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
