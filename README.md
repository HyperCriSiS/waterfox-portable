# Waterfox Portable (self-updating, unofficial)

**Waterfox for Windows that runs from any folder or USB drive and keeps itself up to date with the built-in Waterfox updater.**

<p>
  <a href="https://github.com/HyperCriSiS/waterfox-portable/releases/latest"><img src="https://img.shields.io/github/release/HyperCriSiS/waterfox-portable.svg?style=flat-square" alt="GitHub release"></a>
  <a href="https://github.com/HyperCriSiS/waterfox-portable/releases"><img src="https://img.shields.io/github/downloads/HyperCriSiS/waterfox-portable/total.svg?style=flat-square" alt="Total downloads"></a>
  <a href="https://github.com/HyperCriSiS/waterfox-portable/actions/workflows/build.yml"><img src="https://img.shields.io/github/actions/workflow/status/HyperCriSiS/waterfox-portable/build.yml?branch=master&label=build&logo=github&style=flat-square" alt="Build Status"></a>
  <img src="https://img.shields.io/badge/platform-Windows%20x64-0078d4.svg?style=flat-square" alt="Windows x64">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="MIT license"></a>
</p>

This build is based on [Portapps Waterfox portable](https://github.com/portapps/waterfox-portable). Portapps disables the Waterfox updater, so every browser update needs a new portable package. This build keeps the portable layout and lets Waterfox update itself.

## Why this build

| | Portapps | This build |
| --- | --- | --- |
| Browser updates | New portable package per Waterfox release | Built-in Waterfox updater |
| Administrator rights | Not needed | Not needed |
| Profile location | `data` next to the launcher | `data` next to the launcher |
| Mozilla Maintenance Service | Disabled | Disabled |
| New package checks | Manual | Daily, signature verified and smoke tested |

## Download and installation

1. Download the latest release from the [releases page](https://github.com/HyperCriSiS/waterfox-portable/releases/latest): the `.7z` archive, or the `-setup.exe` installer that extracts it for you.
2. Extract it to a folder your user can write to, for example `D:\Apps\Waterfox` or a USB drive. Avoid protected folders such as `C:\Program Files`, because the updater must write there.
3. Start `waterfox-portable.exe`.

Existing Portapps users can copy their `data` folder into the new folder to keep their profile.

## Updates

Waterfox checks for updates itself and updates the files in the `app` folder. The profile in `data` stays untouched. A new portable package is only needed for launcher changes or a fresh installation.

The launcher has its own version (`app.version`), independent of the Waterfox version bundled into a new package (`waterfox.version`). Daily checks build and verify a new package for every stable Waterfox release; see [daily update and publication instructions](.github/DAILY-UPDATES.md).

## Disclaimer

This is an unofficial build. It is not affiliated with, authorized or endorsed by Waterfox™ or Portapps. The official Waterfox website is https://www.waterfox.net/. Waterfox™ and related names, marks, emblems and images are registered trademarks of their respective owners.

## Support

Report problems with this build in the [issues](https://github.com/HyperCriSiS/waterfox-portable/issues). Browser bugs that also occur in the regular Waterfox installation belong to [Waterfox](https://github.com/BrowserWorks/Waterfox/issues).

## Credits

Based on [Portapps](https://portapps.io) by [CrazyMax](https://github.com/crazy-max). You can support the original project by [becoming a sponsor on GitHub](https://github.com/sponsors/crazy-max).

## License

MIT. See [LICENSE](LICENSE). Rocket icon credit to [Squid Ink](http://thesquid.ink).
