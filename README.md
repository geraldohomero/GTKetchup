# GTKetchup

Stay focused and increase your productivity with GTKetchup, a native GNOME application built with GTK4 and Libadwaita. It features a beautiful, custom-drawn circular interface that dynamically changes colors the longer you focus. Use the scroll wheel to change the time. Feel the tactile feedback of the timer!

<p align="center">
  <img src="assets/img/screenshot.png" width="49%" />
  <img src="assets/img/screenshot2.png" width="49%" />
</p>


## Recommended Installation

Go to https://github.com/geraldohomero/GTKetchup/releases and download the latest .flatpak file.

Then install it using flatpak:

```bash
flatpak install --user GTKetchup.flatpak
```

## Installation

```bash
git clone https://github.com/geraldohomero/GTKetchup.git
cd GTKetchup
flatpak-builder --user --install-deps-from=flathub --repo=repo --force-clean build-dir com.github.geraldohomero.GTKetchup.json && flatpak build-bundle repo GTKetchup.flatpak com.github.geraldohomero.GTKetchup
flatpak install --user GTKetchup.flatpak
```

## Usage

```bash
flatpak run com.github.geraldohomero.GTKetchup
```


## Uninstall

```bash
flatpak uninstall --user com.github.geraldohomero.GTKetchup
```

