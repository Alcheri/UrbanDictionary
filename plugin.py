# -*- coding: utf-8 -*-
###
# Copyright (c) 2012-2013, spline
# Copyright © MMXXIV, Barry Suridge
# All rights reserved.
#
# Asynchronous variant of the original UrbanDictionary plugin.
#
###

# Standard library imports
import json
from typing import Any, Dict, List, Optional, Tuple

# Third-party imports
try:
    import aiohttp  # asynchronous HTTP client and server framework
    import asyncio  # asynchronous I/O
except ImportError as ie:
    raise Exception(f"Cannot import module: {ie}")

# Supybot imports
import supybot.log as log
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization

    _ = PluginInternationalization("UrbanDictionary")
except ImportError:
    _ = lambda x: x


class UrbanDictionary(callbacks.Plugin):
    """
    Add the help for "@plugin help UrbanDictionary" here
    This should describe *how* to use this plugin.
    """

    threaded = False

    def __init__(self, irc):
        self.__parent = super(UrbanDictionary, self)
        self.__parent.__init__(irc)

    ######################
    # INTERNAL FUNCTIONS #
    ######################

    def _format_text(
        self,
        string: str,
        color: Optional[str] = None,
        bold: bool = False,
        underline: bool = False,
    ) -> str:
        """Format a string with optional color, bold, and underline."""
        if color:
            string = ircutils.mircColor(string, color)
        if bold:
            string = ircutils.bold(string)
        if underline:
            string = ircutils.underline(string)
        return string

    def _clean_json(self, s: str) -> str:
        """Clean up JSON strings by removing unnecessary whitespace and escape characters."""
        return s.replace("\n", "").replace("\r", "").replace("\t", "").strip()

    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch data from a URL asynchronously using aiohttp."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        log.error(f"Error fetching URL {url}: HTTP {response.status}")
                        return None
        except Exception as e:
            log.error(f"Error fetching URL {url}: {e}")
            return None

    ####################
    # PUBLIC FUNCTIONS #
    ####################

    def urbandictionary(
        self, irc, msg, args, optlist: List[Tuple[str, Any]], optterm: str
    ):
        """[--disableexamples | --showvotes | --num # | --showtags] <term>

        Fetches definition for <term> on UrbanDictionary.com.

        Use --disableexamples to omit examples.
        Use --showvotes to display vote counts (default: off).
        Use --num # to limit the number of definitions (default: 10).
        Use --showtags to display tags (if available).
        """
        args = {
            "showExamples": True,
            "numberOfDefinitions": self.registryValue("maxNumberOfDefinitions"),
            "showVotes": False,
            "showTags": False,
        }

        # Parse options
        for key, value in optlist:
            if key == "disableexamples":
                args["showExamples"] = False
            elif key == "showvotes":
                args["showVotes"] = True
            elif key == "num" and 0 <= value <= self.registryValue(
                "maxNumberOfDefinitions"
            ):
                args["numberOfDefinitions"] = value
            elif key == "showtags":
                args["showTags"] = True

        # Use the dynamic term directly.
        url = f"http://api.urbandictionary.com/v0/define?term={optterm}"

        loop = asyncio.get_event_loop()
        json_data = loop.run_until_complete(self._fetch_url(url))

        if not json_data:
            irc.error(f"Could not retrieve data for '{optterm}'.", prefixNick=False)
            return

        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            log.error(f"Error parsing JSON: {e}")
            irc.error("Failed to parse Urban Dictionary data.", prefixNick=False)
            return

        definitions = data.get("list", [])

        if not definitions:
            irc.error(f"No definition found for '{optterm}'.", prefixNick=False)
            return

        # Apply slicing limit
        limit = args.get("numberOfDefinitions", 10)
        definitions = definitions[:limit]

        MAX_TOTAL_LENGTH = 1000  # Limit total response length in characters
        MAX_ENTRY_LENGTH = 300  # Limit individual entry length
        output = []
        total_length = 0
        include_first = True

        for entry in definitions:
            definition = self._clean_json(entry.get("definition", ""))
            example = self._clean_json(entry.get("example", ""))
            thumbs_up = entry.get("thumbs_up", 0)
            thumbs_down = entry.get("thumbs_down", 0)

            # Truncate individual parts if necessary
            if len(definition) > MAX_ENTRY_LENGTH:
                definition = definition[:MAX_ENTRY_LENGTH] + "..."
            if args["showExamples"] and len(example) > MAX_ENTRY_LENGTH:
                example = example[:MAX_ENTRY_LENGTH] + "..."

            formatted = definition
            if args["showExamples"] and example:
                formatted += f" Example: {example}"
            if args["showVotes"]:
                formatted += f" (+{thumbs_up}/-{thumbs_down})"

            # Ensure at least one definition is included
            if include_first:
                include_first = False
            elif total_length + len(formatted) > MAX_TOTAL_LENGTH:
                break

            output.append(formatted)
            total_length += len(formatted)

        response = " | ".join(output)

        if args["showTags"]:
            tags = data.get("tags", [])
            if tags:
                tag_text = " | ".join(tags)
                response = f"{response} | Tags: {tag_text}"

        # Check if ANSI should be disabled
        if self.registryValue("disableANSI"):
            response = ircutils.stripFormatting(response)
            optterm = ircutils.stripFormatting(optterm)

        irc.reply(
            self._format_text(optterm, color="red") + " :: " + response,
            prefixNick=False,
        )

    urbandictionary = wrap(
        urbandictionary,
        [
            getopts(
                {"disableexamples": "", "showvotes": "", "num": ("int"), "showtags": ""}
            ),
            ("text"),
        ],
    )


Class = UrbanDictionary

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
