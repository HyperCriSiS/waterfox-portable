<p align="center"><a href="https://portapps.io/app/waterfox-portable/" target="_blank"><img width="100" src="https://github.com/portapps/waterfox-portable/blob/master/res/papp.png"></a></p>

<p align="center">
  <a href="https://github.com/HyperCriSiS/waterfox-portable/releases/latest"><img src="https://img.shields.io/github/release/HyperCriSiS/waterfox-portable.svg?style=flat-square" alt="GitHub release"></a>
  <a href="https://github.com/HyperCriSiS/waterfox-portable/releases"><img src="https://img.shields.io/github/downloads/HyperCriSiS/waterfox-portable/total.svg?style=flat-square" alt="Total downloads"></a>
  <a href="https://github.com/HyperCriSiS/waterfox-portable/actions/workflows/build.yml"><img src="https://img.shields.io/github/actions/workflow/status/HyperCriSiS/waterfox-portable/build.yml?branch=master&label=build&logo=github&style=flat-square" alt="Build Status"></a>
  <br /><a href="https://github.com/sponsors/crazy-max"><img src="https://img.shields.io/badge/sponsor-crazy--max-181717.svg?logo=github&style=flat-square" alt="Become a sponsor"></a>
  <a href="https://www.paypal.me/crazyws"><img src="https://img.shields.io/badge/donate-paypal-00457c.svg?logo=paypal&style=flat-square" alt="Donate Paypal"></a>
</p>

## Self-updating portable build

This fork keeps the portable profile/data layout while allowing Waterfox to use its built-in updater. Waterfox updates the files inside the portable `app` directory; the portable profile remains under `data`.

The Mozilla Maintenance Service remains disabled. No administrator rights are required as long as the portable directory is writable by the current user. Avoid placing the portable installation in a protected directory such as `C:\Program Files`.

The portable launcher has its own version (`app.version`), independent of the bundled bootstrap Waterfox version (`waterfox.version`). After the initial package is installed, Waterfox can update itself without requiring a new portable package release for every Waterfox release.

Daily Waterfox updates are built and verified automatically. Only after the required tests pass does the workflow create and merge its own update PR and publish the verified release files. See [daily update and publication instructions](.github/DAILY-UPDATES.md) for the gates and failure handling.

## Notice of Non-Affiliation and Disclaimer

Portapps is not affiliated, associated, authorized, endorsed by, or in any way officially connected with Waterfox™, or any of its subsidiaries or its affiliates.

The official Waterfox™ website can be found at https://www.waterfox.net/.

The name Waterfox™ as well as related names, marks, emblems and images are registered trademarks of their respective owners.

## About

Waterfox™ portable app made with 🚀 [Portapps](https://portapps.io).<br />
Documentation and downloads of the upstream can be found on https://portapps.io/app/waterfox-portable/

## Contributing

Want to contribute? Awesome! The most basic way to show your support is to star the project, or to raise issues. If
you want to open a pull request, please read the [contributing guidelines](https://portapps.io/doc/contribute/).

You can also support this project by [**becoming a sponsor on GitHub**](https://github.com/sponsors/crazy-max) or by
making a [Paypal donation](https://www.paypal.me/crazyws) to ensure this journey continues indefinitely!

Thanks again for your support, it is much appreciated! :pray:

## License

MIT. See `LICENSE` for more details.<br />
Rocket icon credit to [Squid Ink](http://thesquid.ink).
