###
# Copyright (c) 2012-2013, spline
# Copyright © MMXXIV, Barry Suridge
# All rights reserved.
#
# Asynchronous variant of the original UrbanDictionary plugin.
#
###

# Standard library imports
import html
import json
import urllib.error
import urllib.request
from urllib.parse import quote_plus, urlencode
import re
from typing import Any, Dict, List, Optional, Tuple

# Third-party imports
try:
    import aiohttp  # asynchronous HTTP client and server framework
except ImportError as ie:
    raise ImportError(f"Cannot import module: {ie}")

import asyncio  # asynchronous I/O

# Supybot imports
import supybot.log as log
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

DEFAULT_USER_AGENT = (
    "Limnoria-UrbanDictionary/1.0 (+https://github.com/Alcheri/UrbanDictionary)"
)

try:
    from supybot.i18n import PluginInternationalization

    _ = PluginInternationalization("UrbanDictionary")
except ImportError:
    _ = lambda x: x


class UrbanDictionary(callbacks.Plugin):
    """
    Limnoria / Supybot plugin for UrbanDictionary to display definitions
    on http://www.urbandict.com
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

    async def _fetch_url(self, url: str, timeout: int) -> Optional[str]:
        """Fetch data from a URL asynchronously using aiohttp."""
        try:
            headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"}
            request_timeout = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=request_timeout, headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        body = await response.text()
                        log.error(
                            "Error fetching URL %s: HTTP %s, body=%r",
                            url,
                            response.status,
                            body[:200],
                        )
                        return None
        except Exception as e:
            log.error(f"Error fetching URL {url}: {e}")
            return None

    def _fetch_url_fallback(self, url: str, timeout: int) -> Optional[str]:
        """Fallback fetch path using stdlib urllib when aiohttp fails."""
        headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"}
        req = urllib.request.Request(url, headers=headers)
        retry_timeout = max(timeout + 10, timeout * 2)
        for current_timeout in (timeout, retry_timeout):
            try:
                with urllib.request.urlopen(req, timeout=current_timeout) as response:
                    return response.read().decode("utf-8", errors="replace")
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                log.error(
                    "Fallback fetch failed for %s (timeout=%ss): %s",
                    url,
                    current_timeout,
                    e,
                )
        return None

    def _fetch_define_page_fallback(
        self, term: str, timeout: int
    ) -> Optional[Dict[str, Any]]:
        """Fallback to scraping the Urban Dictionary define page when API fetches fail."""
        url = f"https://www.urbandictionary.com/define.php?term={quote_plus(term)}"
        headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html"}
        req = urllib.request.Request(url, headers=headers)
        retry_timeout = max(timeout + 10, timeout * 2)
        page_html = None
        for current_timeout in (timeout, retry_timeout):
            try:
                with urllib.request.urlopen(req, timeout=current_timeout) as response:
                    page_html = response.read().decode("utf-8", errors="replace")
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                log.error(
                    "Define-page fallback failed for %s (timeout=%ss): %s",
                    term,
                    current_timeout,
                    e,
                )

        if not page_html:
            return None

        # Try the most descriptive metadata first, then title as a last resort.
        description_patterns = (
            r'property="og:description" content="([^"]+)"',
            r'name="description" content="([^"]+)"',
        )
        description = ""
        for pattern in description_patterns:
            match = re.search(pattern, page_html, re.IGNORECASE | re.DOTALL)
            if match:
                description = match.group(1).strip()
                break

        if not description:
            title_match = re.search(
                r"<title[^>]*>(.*?)</title>", page_html, re.IGNORECASE | re.DOTALL
            )
            if title_match:
                description = title_match.group(1).strip()

        if not description:
            return None

        description = html.unescape(description)

        return {
            "list": [
                {
                    "definition": description,
                    "example": "",
                    "thumbs_up": 0,
                    "thumbs_down": 0,
                }
            ],
            "tags": [],
        }

    def _run_coro(self, coro):
        """Run a coroutine in an isolated event loop.

        This avoids collisions with any event loop state in the host process.
        """
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
            loop.close()

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

        query = urlencode({"term": optterm})
        url = f"https://api.urbandictionary.com/v0/define?{query}"
        timeout = self.registryValue("requestTimeout")

        prefer_define_page = self.registryValue("preferDefinePage")
        json_data = None
        data = None

        if prefer_define_page:
            data = self._fetch_define_page_fallback(optterm, timeout)
            if data is None:
                json_data = self._run_coro(self._fetch_url(url, timeout))
                if not json_data:
                    json_data = self._fetch_url_fallback(url, timeout)
        else:
            json_data = self._run_coro(self._fetch_url(url, timeout))
            if not json_data:
                json_data = self._fetch_url_fallback(url, timeout)
            if not json_data:
                data = self._fetch_define_page_fallback(optterm, timeout)

        if not json_data and not data:
            irc.error(f"Could not retrieve data for '{optterm}'.", prefixNick=False)
            return

        if data is None:
            if json_data is None:
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
