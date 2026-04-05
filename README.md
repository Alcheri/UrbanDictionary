<!-- An asynchronous variant of the original UrbanDictionary plugin. -->

<h1 align="center">Limnoria plugin for UrbanDictionary</h1>

<!-- README_HEADER:start -->
<p align="center">
  <a href="https://github.com/Alcheri/UrbanDictionary/actions/workflows/tests.yml">
    <img src="https://github.com/Alcheri/UrbanDictionary/actions/workflows/tests.yml/badge.svg" alt="Tests">
  </a>
  <a href="https://github.com/Alcheri/UrbanDictionary/actions/workflows/lint.yml">
    <img src="https://github.com/Alcheri/UrbanDictionary/actions/workflows/lint.yml/badge.svg" alt="Lint">
  </a>
  <a href="https://github.com/Alcheri/UrbanDictionary/security/code-scanning">
    <img src="https://github.com/Alcheri/UrbanDictionary/actions/workflows/codeql.yml/badge.svg" alt="CodeQL">
  </a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
  <img src="https://img.shields.io/badge/limnoria-compatible-brightgreen.svg" alt="Limnoria">
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="Licence">
  </a>
</p>
<!-- README_HEADER:end -->

## Introduction

Limnoria plugin for querying [UrbanDictionary](http://www.urbandictionary.com)

_An asynchronous variant of the original UrbanDictionary plugin._

## Install

You will need a working Limnoria bot on Python 3.10 or above for this to work.

Go into your Limnoria plugin dir, usually ~/runbot/plugins and run:

```plaintext
git clone https://github.com/Alcheri/UrbanDictionary.git
```

To install additional requirements, run:

```plaintext
pip install --upgrade -r requirements.txt 
```

Next, load the plugin:

```plaintext
/msg bot load UrbanDictionary
```

## Configuring

* **_config supybot.plugins.UrbanDictionary.maxNumberOfDefinitions_**

    Number of definition and examples in output. Max 10.

* **_config supybot.plugins.UrbanDictionary.disableANSI_**

    Do not display any ANSI formatting codes in output. Default is _False_

* **_config supybot.plugins.UrbanDictionary.enabled_**

    Should plugin work in this channel?

* **_config supybot.plugins.UrbanDictionary.requestTimeout_**

    HTTP timeout in seconds for API requests. Default is _10_.
  
* **_config supybot.plugins.UrbanDictionary.preferDefinePage_**

    Prefer scraping the define page first instead of using the API endpoint.
  
* **_aka add ud urbandictionary $*_**

    Add an alias to your bot for ease of use.

Notes:

* API requests are sent over HTTPS.
* Search terms are URL-encoded automatically.

## Example Usage

```plaintext
<spline> @ud spline
<myybot> spline :: The [object] which [Maxis] likes to [reticulate]. Example: 1:  "What [are you] reticulating, dude?"
 2: "[My favorite] dish-- [Splines]!" | A combination organ between [the spine] and the [spleen].
One which doesn't exist, but you should ask [the stoner] people how it's doing anyways.
Example: Hey [Maya], how's your spline doing? What? Not to well? Oh, [I'm sorry] to [hear] that.
```

## Licensing

This project contains code originally published under the MIT Licence by the
upstream author. The original licence text is preserved verbatim in
`LICENSE.txt` as required by the MIT Licence.

All modifications, additions, and ongoing maintenance performed by Barry
Suridge are licensed under the terms described in `LICENCE.md`.

In summary:

- `LICENSE.txt` — original upstream MIT Licence (unchanged)
- `LICENCE.md` — licence applying to Barry Suridge’s contributions
