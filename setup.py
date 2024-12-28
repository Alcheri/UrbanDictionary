###
# Copyright © MMXXIV, Barry Suridge
# All rights reserved.
#
#
###

from supybot.setup import plugin_setup

plugin_setup(
    'UrbanDictionary',
    install_requires=[
        'aiohttp',
        'asyncio',
    ],
)
