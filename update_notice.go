package main

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/portapps/portapps/v3/pkg/log"
	"github.com/portapps/portapps/v3/pkg/win"
)

// The launcher version comes from the executable itself. portapp.json stays
// behind when a user replaces only the executable.
//
//go:embed build.properties
var buildProperties string

// notifyLauncherUpdate tells the user once per version when a release with a
// newer launcher exists and returns the page to open, if any. Waterfox updates
// itself, so a release that only raises app.release is ignored. Starts with
// arguments (links, headless, screenshots) are never interrupted, and GitHub is
// asked at most once a day.
func notifyLauncherUpdate() []string {
	if len(os.Args) > 1 || os.Getenv("MOZ_HEADLESS") != "" {
		return nil
	}
	seenFile := filepath.Join(app.DataPath, "launcher-update-seen.txt")
	if info, err := os.Stat(seenFile); err == nil && time.Since(info.ModTime()) < 24*time.Hour {
		return nil
	}
	seen, _ := os.ReadFile(seenFile)
	if err := os.WriteFile(seenFile, seen, 0644); err != nil {
		log.Error().Err(err).Msg("Cannot remember launcher update check")
		return nil
	}

	client := http.Client{Timeout: 2 * time.Second}
	// Not app.Info.URL: portapp.json can come from another package.
	resp, err := client.Get("https://api.github.com/repos/HyperCriSiS/waterfox-portable/releases/latest")
	if err != nil {
		log.Debug().Err(err).Msg("Cannot check for launcher updates")
		return nil
	}
	defer resp.Body.Close()
	var release struct {
		TagName string `json:"tag_name"`
		HTMLURL string `json:"html_url"`
	}
	if resp.StatusCode != http.StatusOK || json.NewDecoder(resp.Body).Decode(&release) != nil {
		return nil
	}

	latest, _, _ := strings.Cut(release.TagName, "-")
	current := launcherVersion()
	if !newerVersion(latest, current) || strings.TrimSpace(string(seen)) == latest {
		return nil
	}
	if err := os.WriteFile(seenFile, []byte(latest), 0644); err != nil {
		log.Error().Err(err).Msg("Cannot remember launcher update notice")
		return nil
	}

	answer, err := win.MsgBox(
		fmt.Sprintf("%s portable", app.Name),
		fmt.Sprintf("A new portable launcher is available (%s, you have %s). Waterfox itself keeps updating on its own; this update is for the portable launcher.\n\nReplace only the launcher executable. Keep your app and data folders.\n\nOpen the release page?", latest, current),
		win.MsgBoxBtnYesNo|win.MsgBoxIconInformation|win.MsgBoxTopMost)
	if err != nil {
		log.Error().Err(err).Msg("Cannot create dialog box")
		return nil
	}
	if answer == win.MsgBoxSelectYes && strings.HasPrefix(release.HTMLURL, "https://github.com/") {
		return []string{release.HTMLURL}
	}
	return nil
}

// launcherVersion returns app.version of the build this executable came from.
func launcherVersion() string {
	for _, line := range strings.Split(buildProperties, "\n") {
		key, value, _ := strings.Cut(line, "=")
		if strings.TrimSpace(key) == "app.version" {
			return strings.TrimSpace(value)
		}
	}
	return app.Info.Version
}

// newerVersion reports whether dotted version a is greater than b.
func newerVersion(a, b string) bool {
	as, bs := strings.Split(a, "."), strings.Split(b, ".")
	for i := 0; i < len(as) || i < len(bs); i++ {
		var x, y int
		if i < len(as) {
			x, _ = strconv.Atoi(as[i])
		}
		if i < len(bs) {
			y, _ = strconv.Atoi(bs[i])
		}
		if x != y {
			return x > y
		}
	}
	return false
}
